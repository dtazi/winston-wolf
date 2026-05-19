"""ww-engine CLI. See specs/002-outreach-campaign-engine/contracts/cli.md."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import db, logging, rotation

app = typer.Typer(help="Winston Wolf outreach campaign engine.")
console = Console()

_DB = typer.Option(db.DEFAULT_DB_PATH, "--db", help="Path to leads.db")


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


if __name__ == "__main__":
    app()
