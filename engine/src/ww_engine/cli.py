"""ww-engine CLI. See specs/002-outreach-campaign-engine/contracts/cli.md."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

import dataclasses
import json as _json

from . import (
    cost, db, feedback, intake, knowledge, logging, modes, research, rotation,
    runs, selection, sender,
)
from .drafting import personalization
from .drafting.base import DraftError, DraftRequest, Drafter
from .drafting.claude_code import ClaudeCodeDrafter
from .drafting.grounded import GroundedClaudeDrafter
from .research import Researcher

app = typer.Typer(help="Winston Wolf outreach campaign engine.")
console = Console()

_DB = typer.Option(db.DEFAULT_DB_PATH, "--db", help="Path to leads.db")


def _campaign_ctx(conn, campaign: str) -> tuple[str, str]:
    row = conn.execute(
        "SELECT customer_id, mode FROM campaigns WHERE id=?", (campaign,)
    ).fetchone()
    if not row:
        console.print(f"[red]No such campaign:[/red] {campaign}")
        raise typer.Exit(1)
    return row["customer_id"], row["mode"]


def run_draft(conn, campaign: str, batch: int, drafter: Drafter) -> dict:
    """Draft pass core (FR-001/005/006/010/011). Testable without Typer."""
    customer_id, mode = _campaign_ctx(conn, campaign)
    with runs.run(conn, campaign, "draft") as counts:
        counts.update(drafted=0, skipped=0)
        for lead in selection.eligible_leads(conn, campaign, limit=batch):
            next_touch = (lead["current_touch"] or 0) + 1
            live = conn.execute(
                "SELECT 1 FROM send_drafts WHERE lead_id=? AND touch_number=? "
                "AND review_state!='rejected'",
                (lead["id"], next_touch),
            ).fetchone()
            if live:  # idempotency (FR-005)
                continue
            angle = rotation.angle_for(lead["rotation_group"], next_touch)
            pers = personalization.gather(dict(lead))
            req = DraftRequest(lead=dict(lead), pitch={}, brief_excerpt={},
                               value_angle=angle, touch_number=next_touch,
                               personalization=pers)
            try:
                res = drafter.draft(req)
            except DraftError as exc:
                counts["skipped"] += 1
                logging.log("draft_skip", campaign_id=campaign,
                            lead_id=lead["id"], reason=type(exc).__name__)
                continue
            draft_id = __import__("uuid").uuid4().hex
            state = "approved" if mode == "autonomous" else "pending"
            conn.execute(
                """INSERT INTO send_drafts (id, customer_id, campaign_id,
                       lead_id, touch_number, value_angle, subject, body_text,
                       body_text_original, message_recipe, personalization_level,
                       review_state, scheduled_send_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (draft_id, customer_id, campaign, lead["id"], next_touch, angle,
                 res.subject, res.body_text, res.body_text,
                 __import__("json").dumps(res.message_recipe),
                 pers["level"], state, sender.next_window_slot()),
            )
            for u in res.token_usage:
                cost.record(conn, customer_id=customer_id, campaign_id=campaign,
                            stage=u.get("stage", "drafting"),
                            model=u.get("model", "unknown"),
                            input_tokens=int(u.get("input_tokens", 0)),
                            output_tokens=int(u.get("output_tokens", 0)),
                            lead_id=lead["id"], send_draft_id=draft_id)
            conn.commit()
            counts["drafted"] += 1
            logging.log("draft", campaign_id=campaign, lead_id=lead["id"],
                        send_id=draft_id, touch=next_touch, angle=angle,
                        personalization_level=pers["level"])
    return counts


def run_deliver(conn, campaign: str, transport: sender.Transport,
                now=None) -> dict:
    """Deliver pass core (FR-009/016/017). Window-gated; re-checks eligibility;
    refuses blind follow-ups (freshness guard applies to touch>=2 only)."""
    _campaign_ctx(conn, campaign)
    with runs.run(conn, campaign, "deliver") as counts:
        counts.update(delivered=0, skipped=0)
        if not sender.in_send_window(now):
            logging.log("deliver_skip", campaign_id=campaign,
                        reason="outside_window")
            return counts
        fresh = runs.detect_is_fresh(conn, campaign)
        rows = conn.execute(
            "SELECT d.* FROM send_drafts d WHERE d.campaign_id=? "
            "AND d.review_state IN ('approved','edited') "
            "AND (d.scheduled_send_at IS NULL OR d.scheduled_send_at<=?)",
            (campaign, __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).replace(
                tzinfo=None).isoformat(sep=" ", timespec="seconds")),
        ).fetchall()
        for d in rows:
            if d["touch_number"] >= 2 and not fresh:  # never follow up blind
                counts["skipped"] += 1
                logging.log("deliver_skip", campaign_id=campaign,
                            lead_id=d["lead_id"], reason="detect_stale")
                continue
            if not selection.is_still_eligible(conn, d["lead_id"]):  # FR-009
                counts["skipped"] += 1
                logging.log("deliver_skip", campaign_id=campaign,
                            lead_id=d["lead_id"], reason="ineligible")
                continue
            sender.deliver_draft(conn, d, transport)
            counts["delivered"] += 1
    return counts


def run_experiment_draft(conn, campaign: str, batch: int,
                         researcher: Researcher, drafter: Drafter,
                         tenant: str = "richbond") -> dict:
    """004 nightly pass (D6/D7): research each eligible lead, draft grounded in
    the KB + strategy library + research + conclusions + feedback, write a
    reasoning note + a review file. Testable without Typer."""
    customer_id, mode = _campaign_ctx(conn, campaign)
    kb = knowledge.load_kb(tenant)
    strategies = knowledge.load_strategies()
    conclusions = knowledge.load_conclusions(tenant)
    comments = knowledge.recent_comments(conn, campaign)
    with runs.run(conn, campaign, "draft") as counts:
        counts.update(drafted=0, researched=0, skipped=0)
        for lead in selection.eligible_leads(conn, campaign, limit=batch):
            next_touch = (lead["current_touch"] or 0) + 1
            live = conn.execute(
                "SELECT 1 FROM send_drafts WHERE lead_id=? AND touch_number=? "
                "AND review_state!='rejected'", (lead["id"], next_touch),
            ).fetchone()
            if live:  # idempotency (FR-005)
                continue
            ld = dict(lead)
            ld["person_name"] = " ".join(
                x for x in [ld.get("person_first_name"),
                            ld.get("person_last_name")] if x).strip()

            try:
                res_obj = researcher.research(ld)
                research.store_research(conn, lead["id"], res_obj)
                counts["researched"] += 1
            except research.ResearchError as exc:
                res_obj = research.ResearchResult()  # thin, never invented
                logging.log("research_skip", campaign_id=campaign,
                            lead_id=lead["id"], reason=type(exc).__name__)

            tier = selection.engagement_tier(conn, lead["id"]) \
                if next_touch > 1 else ""
            pers = personalization.gather(ld)
            req = DraftRequest(
                lead=ld, pitch={}, brief_excerpt={}, value_angle="grounded",
                touch_number=next_touch, personalization=pers,
                knowledge_base=kb, strategies=strategies,
                research=dataclasses.asdict(res_obj), conclusions=conclusions,
                feedback=comments, engagement_tier=tier)
            try:
                drafted = drafter.draft(req)
            except DraftError as exc:
                counts["skipped"] += 1
                logging.log("draft_skip", campaign_id=campaign,
                            lead_id=lead["id"], reason=type(exc).__name__)
                continue

            draft_id = __import__("uuid").uuid4().hex
            state = "approved" if mode == "autonomous" else "pending"
            slot = sender.next_window_slot(tz=lead["send_timezone"])
            conn.execute(
                """INSERT INTO send_drafts (id, customer_id, campaign_id,
                       lead_id, touch_number, value_angle, subject, body_text,
                       body_text_original, message_recipe, personalization_level,
                       review_state, scheduled_send_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (draft_id, customer_id, campaign, lead["id"], next_touch,
                 "grounded", drafted.subject, drafted.body_text,
                 drafted.body_text, _json.dumps(drafted.message_recipe),
                 pers["level"], state, slot))
            for u in drafted.token_usage:
                cost.record(conn, customer_id=customer_id, campaign_id=campaign,
                            stage=u.get("stage", "drafting"),
                            model=u.get("model", "unknown"),
                            input_tokens=int(u.get("input_tokens", 0)),
                            output_tokens=int(u.get("output_tokens", 0)),
                            lead_id=lead["id"], send_draft_id=draft_id)
            conn.commit()
            feedback.write_review_file(
                {"id": draft_id, "touch_number": next_touch,
                 "lead_id": lead["id"], "subject": drafted.subject,
                 "body_text": drafted.body_text,
                 "message_recipe": _json.dumps(drafted.message_recipe)}, res_obj)
            counts["drafted"] += 1
            logging.log("draft", campaign_id=campaign, lead_id=lead["id"],
                        send_id=draft_id, touch=next_touch,
                        personalization_level=pers["level"])
    return counts


def run_experiment_deliver(conn, campaign: str, transport: sender.Transport,
                           now=None) -> dict:
    """004 deliver pass: per-recipient-local window; manual-flag suppression via
    is_still_eligible (no detector/freshness guard — D4)."""
    _campaign_ctx(conn, campaign)
    now_str = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).replace(
        tzinfo=None).isoformat(sep=" ", timespec="seconds")
    with runs.run(conn, campaign, "deliver") as counts:
        counts.update(delivered=0, skipped=0)
        rows = conn.execute(
            "SELECT d.*, l.send_timezone AS lead_tz FROM send_drafts d "
            "JOIN leads l ON l.id=d.lead_id WHERE d.campaign_id=? "
            "AND d.review_state IN ('approved','edited') "
            "AND (d.scheduled_send_at IS NULL OR d.scheduled_send_at<=?)",
            (campaign, now_str)).fetchall()
        for d in rows:
            if not sender.in_send_window(now, tz=d["lead_tz"]):
                counts["skipped"] += 1
                logging.log("deliver_skip", campaign_id=campaign,
                            lead_id=d["lead_id"], reason="outside_window")
                continue
            if not selection.is_still_eligible(conn, d["lead_id"]):  # FR-016/017
                counts["skipped"] += 1
                logging.log("deliver_skip", campaign_id=campaign,
                            lead_id=d["lead_id"], reason="ineligible")
                continue
            sender.deliver_draft(conn, d, transport)
            counts["delivered"] += 1
    return counts


@app.command("import-prospects")
def import_prospects(file: Path = typer.Argument(...),
                     campaign: str = typer.Option(..., "--campaign"),
                     db_path: Path = _DB) -> None:
    """Import a hand-built prospect list (YAML) into the campaign (D8)."""
    conn = db.get_connection(db_path)
    try:
        if not file.exists():
            console.print(f"[red]No such file:[/red] {file}")
            raise typer.Exit(1)
        res = intake.import_prospects(conn, file, campaign)
    finally:
        conn.close()
    console.print(f"[green]Imported[/green] {res['imported']} "
                  f"(skipped {res['skipped']}).")


@app.command()
def configure(campaign: str = typer.Option(..., "--campaign"),
              max_touches: int = typer.Option(2, "--max-touches"),
              gap_days: int = typer.Option(7, "--gap-days"),
              db_path: Path = _DB) -> None:
    """Set the experiment campaign's sequencing config (D3): 2 touches, 7-day gap."""
    conn = db.get_connection(db_path)
    try:
        conn.execute(
            "UPDATE campaigns SET max_touches=?, touch_gap_days=? WHERE id=?",
            (max_touches, gap_days, campaign))
        conn.commit()
        logging.log("configure", campaign_id=campaign,
                    max_touches=max_touches, touch_gap_days=gap_days)
    finally:
        conn.close()
    console.print(f"[green]Configured[/green] {campaign}: "
                  f"{max_touches} touches, {gap_days}-day gap.")


@app.command()
def init(db_path: Path = _DB) -> None:
    """Apply idempotent engine migrations."""
    conn = db.get_connection(db_path)
    try:
        added = db.apply_migrations(conn)
    finally:
        conn.close()
    if added:
        console.print(f"[green]Migrations applied[/green]: {', '.join(added)}")
    else:
        console.print("[green]Schema already current[/green] (no-op).")


@app.command()
def enroll(
    campaign: str = typer.Option(..., "--campaign"),
    db_path: Path = _DB,
) -> None:
    """Assign rotation groups + activate this campaign's un-enrolled leads."""
    conn = db.get_connection(db_path)
    try:
        cust = conn.execute(
            "SELECT customer_id FROM campaigns WHERE id=?", (campaign,)
        ).fetchone()
        if not cust:
            console.print(f"[red]No such campaign:[/red] {campaign}")
            raise typer.Exit(1)
        leads = conn.execute(
            "SELECT id FROM leads WHERE campaign_id=? AND rotation_group IS NULL",
            (campaign,),
        ).fetchall()
        for row in leads:
            g = rotation.group_for_lead(row["id"])
            conn.execute(
                "UPDATE leads SET rotation_group=?, sequence_state='active' "
                "WHERE id=?",
                (g, row["id"]),
            )
        conn.commit()
        logging.log("enroll", customer_id=cust["customer_id"],
                    campaign_id=campaign, enrolled=len(leads))
        dist = conn.execute(
            "SELECT rotation_group AS g, COUNT(*) AS n FROM leads "
            "WHERE campaign_id=? AND rotation_group IS NOT NULL GROUP BY g",
            (campaign,),
        ).fetchall()
    finally:
        conn.close()

    t = Table(title=f"Enrolled {len(leads)} new lead(s) — rotation balance")
    t.add_column("Group")
    t.add_column("Leads", justify="right")
    for r in dist:
        t.add_row(str(r["g"]), str(r["n"]))
    console.print(t)


@app.command()
def draft(campaign: str = typer.Option(..., "--campaign"),
          batch: int = typer.Option(15, "--batch"),
          db_path: Path = _DB) -> None:
    """Nightly pass: research each eligible lead and draft a grounded next touch."""
    conn = db.get_connection(db_path)
    try:
        counts = run_experiment_draft(
            conn, campaign, batch,
            research.ClaudeCodeResearcher(), GroundedClaudeDrafter())
    finally:
        conn.close()
    console.print(f"[green]Draft pass[/green]: {counts}")


@app.command()
def review(campaign: str = typer.Option(..., "--campaign"),
           draft_id: str = typer.Option(None, "--draft"),
           verdict: str = typer.Option(None, "--verdict",
                                       help="approve | edit | reject"),
           comment: str = typer.Option(None, "--comment"),
           body_file: Path = typer.Option(None, "--body"),
           db_path: Path = _DB) -> None:
    """Morning review (D1). No --draft → list pending + review-file paths.
    With --draft + --verdict → record the decision and an optional comment."""
    conn = db.get_connection(db_path)
    try:
        if draft_id and verdict:
            state = {"approve": "approved", "edit": "edited",
                     "reject": "rejected"}.get(verdict)
            if not state:
                console.print(f"[red]Bad verdict:[/red] {verdict}")
                raise typer.Exit(1)
            body = None
            if state == "edited":
                if not body_file or not body_file.exists():
                    console.print("[red]edit needs --body <file>[/red]")
                    raise typer.Exit(1)
                body = body_file.read_text(encoding="utf-8")
            ok = modes.set_review_state(conn, draft_id, state, body, comment)
            if ok:
                logging.log("review_decision", send_id=draft_id,
                            decision=state, has_comment=bool(comment))
            if not ok:
                console.print("[red]Draft missing or already finalized.[/red]")
                raise typer.Exit(1)
            console.print(f"[green]{state}[/green] {draft_id}")
            return

        rows = conn.execute(
            "SELECT * FROM send_drafts WHERE campaign_id=? AND "
            "review_state='pending' ORDER BY created_at", (campaign,),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        console.print("[yellow]No pending drafts.[/yellow]")
        return
    rdir = feedback.reviews_dir()
    for r in rows:
        flag = " [red](THIN)[/red]" if \
            r["personalization_level"] == "thin" else ""
        console.print(
            f"\n[bold]{r['id']}[/bold] · lead {r['lead_id']} · touch "
            f"{r['touch_number']}{flag}")
        console.print(f"[dim]Subject:[/dim] {r['subject']}")
        console.print(f"[dim]Review file:[/dim] {rdir / (r['id'] + '.md')}")


@app.command()
def approve(draft_id: str, db_path: Path = _DB) -> None:
    """Approve one draft."""
    _decide(db_path, draft_id, "approved")


@app.command()
def reject(draft_id: str, db_path: Path = _DB) -> None:
    """Reject one draft (never sent)."""
    _decide(db_path, draft_id, "rejected")


@app.command()
def edit(draft_id: str,
         body_file: Path = typer.Option(..., "--body-file"),
         db_path: Path = _DB) -> None:
    """Replace a draft's body with operator text and approve it (edited)."""
    if not body_file.exists():
        console.print(f"[red]No such file:[/red] {body_file}")
        raise typer.Exit(1)
    _decide(db_path, draft_id, "edited", body_file.read_text(encoding="utf-8"))


@app.command("approve-all")
def approve_all(campaign: str = typer.Option(..., "--campaign"),
                db_path: Path = _DB) -> None:
    """Approve every remaining pending draft."""
    conn = db.get_connection(db_path)
    try:
        cur = conn.execute(
            "UPDATE send_drafts SET review_state='approved', "
            "updated_at=CURRENT_TIMESTAMP WHERE campaign_id=? AND "
            "review_state='pending'",
            (campaign,),
        )
        conn.commit()
        logging.log("approve_all", campaign_id=campaign, count=cur.rowcount)
    finally:
        conn.close()
    console.print(f"[green]Approved[/green] {cur.rowcount} draft(s).")


def _decide(db_path: Path, draft_id: str, state: str,
            body: str | None = None) -> None:
    conn = db.get_connection(db_path)
    try:
        ok = modes.set_review_state(conn, draft_id, state, body)
        if ok:
            logging.log("review_decision", send_id=draft_id, decision=state)
    finally:
        conn.close()
    if not ok:
        console.print("[red]Draft missing or already finalized.[/red]")
        raise typer.Exit(1)
    console.print(f"[green]{state}[/green] {draft_id}")


@app.command()
def deliver(campaign: str = typer.Option(..., "--campaign"),
            db_path: Path = _DB) -> None:
    """Deliver approved drafts — each in the recipient's local window."""
    conn = db.get_connection(db_path)
    try:
        counts = run_experiment_deliver(conn, campaign, sender.GraphTransport())
    finally:
        conn.close()
    console.print(f"[green]Deliver pass[/green]: {counts}")


@app.command()
def detect(campaign: str = typer.Option(..., "--campaign"),
           db_path: Path = _DB) -> None:
    """Detect pass: poll the mailbox, log replies/bounces, halt sequences."""
    from .detector import GraphMailReader, run_detect
    conn = db.get_connection(db_path)
    try:
        counts = run_detect(conn, campaign, GraphMailReader())
    finally:
        conn.close()
    console.print(f"[green]Detect pass[/green]: {counts}")


@app.command("flag-replied")
def flag_replied(lead: str = typer.Option(..., "--lead"),
                 category: str = typer.Option(
                     "other", "--category",
                     help="interested|not-interested|wrong-person|ooo|other"),
                 db_path: Path = _DB) -> None:
    """Manually mark a prospect as replied (D4, Article 15): record the reply,
    halt outreach, void pending drafts. NEVER reads the reply content."""
    conn = db.get_connection(db_path)
    try:
        row = conn.execute("SELECT id FROM leads WHERE id=?", (lead,)).fetchone()
        if not row:
            console.print(f"[red]No such lead:[/red] {lead}")
            raise typer.Exit(1)
        conn.execute(
            "INSERT INTO events (lead_id, event_type, timestamp, payload) "
            "VALUES (?, 'replied', CURRENT_TIMESTAMP, ?)",
            (lead, _json.dumps({"category": category, "source": "manual_flag"})))
        conn.execute(
            "UPDATE leads SET sequence_state='halted_reply', "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?", (lead,))
        conn.execute(
            "UPDATE send_drafts SET review_state='rejected', "
            "updated_at=CURRENT_TIMESTAMP WHERE lead_id=? AND "
            "review_state IN ('pending','approved','edited')", (lead,))
        conn.commit()
        logging.log("flag_replied", lead_id=lead, category=category)
    finally:
        conn.close()
    console.print(f"[green]Flagged replied[/green] {lead} ({category}) — "
                  "outreach halted.")


@app.command("go-autonomous")
def go_autonomous(campaign: str = typer.Option(..., "--campaign"),
                  db_path: Path = _DB) -> None:
    """Switch the campaign to autonomous mode (explicit, reversible)."""
    _set_mode(db_path, campaign, "autonomous")


@app.command("go-review")
def go_review(campaign: str = typer.Option(..., "--campaign"),
              db_path: Path = _DB) -> None:
    """Pull the campaign back to review mode."""
    _set_mode(db_path, campaign, "review")


def _set_mode(db_path: Path, campaign: str, mode: str) -> None:
    conn = db.get_connection(db_path)
    try:
        modes.set_mode(conn, campaign, mode)
        logging.log("mode_change", campaign_id=campaign, mode=mode)
    finally:
        conn.close()
    console.print(f"[green]Campaign mode → {mode}[/green]")


@app.command()
def status(campaign: str = typer.Option(..., "--campaign"),
           db_path: Path = _DB) -> None:
    """Funnel, sequence states, last run per pass, detect freshness."""
    conn = db.get_connection(db_path)
    try:
        seq = conn.execute(
            "SELECT sequence_state s, COUNT(*) n FROM leads WHERE campaign_id=? "
            "AND rotation_group IS NOT NULL GROUP BY s", (campaign,)).fetchall()
        drafts = conn.execute(
            "SELECT review_state s, COUNT(*) n FROM send_drafts WHERE "
            "campaign_id=? GROUP BY s", (campaign,)).fetchall()
        fresh = runs.detect_is_fresh(conn, campaign)
        # Manual LinkedIn task paired to touch 2 (FR-008/022): due while the
        # lead is active, cancelled the moment the sequence is halted.
        li = conn.execute(
            "SELECT l.sequence_state s, COUNT(*) n FROM leads l "
            "WHERE l.campaign_id=? AND EXISTS (SELECT 1 FROM sends s2 "
            "WHERE s2.lead_id=l.id AND s2.touch_number=2) GROUP BY l.sequence_state",
            (campaign,)).fetchall()
        last = conn.execute(
            "SELECT pass, outcome, MAX(started_at) t FROM engine_runs WHERE "
            "campaign_id=? GROUP BY pass", (campaign,)).fetchall()
    finally:
        conn.close()
    t = Table(title=f"Campaign {campaign}")
    t.add_column("Metric"); t.add_column("Value")
    t.add_row("sequence", ", ".join(f"{r['s']}={r['n']}" for r in seq) or "—")
    t.add_row("drafts", ", ".join(f"{r['s']}={r['n']}" for r in drafts) or "—")
    t.add_row("detect fresh", "[green]yes[/green]" if fresh else "[red]NO[/red]")
    li_due = sum(r["n"] for r in li if r["s"] == "active")
    li_cancelled = sum(r["n"] for r in li if r["s"] != "active")
    t.add_row("linkedin tasks (touch 2)",
              f"due={li_due}, cancelled={li_cancelled}")
    for r in last:
        t.add_row(f"last {r['pass']}", f"{r['outcome']} @ {r['t']}")
    console.print(t)


@app.command()
def costs(campaign: str = typer.Option(..., "--campaign"),
          db_path: Path = _DB) -> None:
    """Cost-per-email + per-stage rollup (SC-011)."""
    conn = db.get_connection(db_path)
    try:
        stages = cost.per_stage(conn, campaign)
        pe = cost.per_email(conn, campaign)
    finally:
        conn.close()
    t = Table(title=f"Cost — {campaign}")
    t.add_column("Stage"); t.add_column("Calls", justify="right")
    t.add_column("In tok", justify="right"); t.add_column("Out tok", justify="right")
    t.add_column("USD", justify="right")
    for r in stages:
        t.add_row(r["stage"], str(r["calls"]), str(r["in_tok"]),
                  str(r["out_tok"]), str(r["cost_usd"]))
    console.print(t)
    console.print(f"[bold]Per email[/bold]: {pe}")


if __name__ == "__main__":
    app()
