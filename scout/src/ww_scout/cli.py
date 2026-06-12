"""ww-scout CLI — lead-pipeline visibility.

The source-ingester framework (CMS Nursing Home Compare, etc.) was retired with
the Pivot-2 acquisition scope (`pivot-disposition.md`). Scout is now built
incrementally as real co-pilot scouting sessions need capabilities (operator
decision 2026-06-12, knowledge/product.md) — recover the old ingesters from git
history if a structured source ever returns to scope.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from . import db

app = typer.Typer(
    help="Winston Wolf Scout — lead-pipeline visibility."
)
console = Console()


@app.command("status")
def cmd_status(
    campaign: str = typer.Option(..., help="Campaign id."),
) -> None:
    """Show lead counts per niche and per source for a campaign."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT niche_id, source_channel_id, company_region,
                   COUNT(*) AS n,
                   SUM(CASE WHEN person_email IS NOT NULL THEN 1 ELSE 0 END) AS enriched
              FROM leads
             WHERE campaign_id = ?
             GROUP BY niche_id, source_channel_id, company_region
             ORDER BY niche_id, source_channel_id, company_region
            """,
            (campaign,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        console.print(f"[yellow]No leads for campaign {campaign}.[/yellow]")
        return

    table = Table(title=f"Leads for {campaign}")
    table.add_column("Niche")
    table.add_column("Source")
    table.add_column("Region")
    table.add_column("Count", justify="right")
    table.add_column("With email", justify="right")
    total = 0
    total_enriched = 0
    for r in rows:
        table.add_row(
            r["niche_id"],
            r["source_channel_id"],
            r["company_region"] or "—",
            str(r["n"]),
            str(r["enriched"]),
        )
        total += r["n"]
        total_enriched += r["enriched"] or 0
    console.print(table)
    console.print(
        f"Total: [bold]{total}[/bold] leads, [bold]{total_enriched}[/bold] with email."
    )


if __name__ == "__main__":
    app()
