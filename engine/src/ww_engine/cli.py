"""ww-engine CLI. See specs/002-outreach-campaign-engine/contracts/cli.md."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import cost, db, logging, modes, rotation, runs, selection, sender
from .drafting import personalization
from .drafting.base import DraftError, DraftRequest, Drafter
from .drafting.claude_code import ClaudeCodeDrafter

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
    """Draft pass: select eligible leads and draft their next touch."""
    conn = db.get_connection(db_path)
    try:
        counts = run_draft(conn, campaign, batch, ClaudeCodeDrafter())
    finally:
        conn.close()
    console.print(f"[green]Draft pass[/green]: {counts}")


@app.command()
def review(campaign: str = typer.Option(..., "--campaign"),
           db_path: Path = _DB) -> None:
    """List pending drafts with full bodies and thin-personalization flags."""
    conn = db.get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM send_drafts WHERE campaign_id=? AND "
            "review_state='pending' ORDER BY created_at",
            (campaign,),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        console.print("[yellow]No pending drafts.[/yellow]")
        return
    for r in rows:
        flag = " [red](THIN PERSONALIZATION)[/red]" if \
            r["personalization_level"] == "thin" else ""
        console.print(
            f"\n[bold]{r['id']}[/bold] · lead {r['lead_id']} · touch "
            f"{r['touch_number']} · angle {r['value_angle']}{flag}")
        console.print(f"[dim]Subject:[/dim] {r['subject']}")
        console.print(r["body_text"])


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
    """Deliver approved drafts — inside the send window only."""
    conn = db.get_connection(db_path)
    try:
        counts = run_deliver(conn, campaign, sender.GraphTransport())
    finally:
        conn.close()
    console.print(f"[green]Deliver pass[/green]: {counts}")


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
