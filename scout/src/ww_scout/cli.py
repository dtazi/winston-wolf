"""ww-scout CLI — ingest leads from public sources into the shared database."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import db
from .sources.cms_nursing_home import CMSNursingHomeIngester

app = typer.Typer(
    help="Winston Wolf Scout — discover leads from public sources."
)
console = Console()


_KNOWN_SOURCES = {"cms_nursing_home_compare"}


@app.command("ingest")
def cmd_ingest(
    source: str = typer.Option(..., help="Source channel id (e.g. cms_nursing_home_compare)."),
    customer: str = typer.Option(..., help="Customer id (e.g. richbond)."),
    campaign: str = typer.Option(..., help="Campaign id (must already exist)."),
    niche: str = typer.Option(..., help="Niche id (must match a sub-niche in the brief)."),
    file: Path = typer.Option(..., help="Path to the source's input CSV."),
    region_filter: Optional[str] = typer.Option(
        None,
        help="Comma-separated US state codes to keep (e.g. MT,WY,SD). Omit = all.",
    ),
) -> None:
    """Run a source ingester and write leads into the database."""
    if not file.exists():
        console.print(f"[red]Input file not found: {file}[/red]")
        raise typer.Exit(code=1)
    if source not in _KNOWN_SOURCES:
        console.print(
            f"[red]Unknown source: {source}.[/red] Known: {sorted(_KNOWN_SOURCES)}"
        )
        raise typer.Exit(code=1)

    regions = (
        {s.strip().upper() for s in region_filter.split(",") if s.strip()}
        if region_filter else None
    )
    ingester = CMSNursingHomeIngester(file, region_filter=regions)

    conn = db.get_connection()
    try:
        inserted, skipped = db.write_leads(
            conn,
            customer_id=customer,
            campaign_id=campaign,
            niche_id=niche,
            source_channel_id=source,
            leads_iter=ingester.ingest(),
        )
    finally:
        conn.close()

    console.print(
        f"[green]Ingested[/green] from [bold]{source}[/bold]: "
        f"{inserted} new leads, {skipped} duplicates skipped."
    )


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


@app.command("list-sources")
def cmd_list_sources() -> None:
    """List the source-channel ids this Scout knows how to ingest."""
    for s in sorted(_KNOWN_SOURCES):
        console.print(f"  - {s}")


if __name__ == "__main__":
    app()
