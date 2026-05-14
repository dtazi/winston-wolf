"""ww-core CLI — manage the lead database and inspect brief/pitch artifacts."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import briefs, db, pitches

app = typer.Typer(
    help="Winston Wolf core — lead database + brief/pitch loaders."
)
console = Console()


@app.command("init")
def cmd_init(
    db_path: Path = typer.Option(db.DEFAULT_DB_PATH, help="Path to the SQLite file."),
) -> None:
    """Create the lead database and seed source channels."""
    actual_path, new_channels = db.init_database(db_path)
    console.print(f"[green]Database initialised[/green] at {actual_path}")
    console.print(f"Seeded {new_channels} new source-channel rows.")


@app.command("status")
def cmd_status(
    db_path: Path = typer.Option(db.DEFAULT_DB_PATH, help="Path to the SQLite file."),
) -> None:
    """Show row counts per table."""
    conn = db.get_connection(db_path)
    try:
        tables = ["customers", "campaigns", "source_channels", "leads", "sends", "events"]
        table = Table(title=f"Database: {db_path}")
        table.add_column("Table")
        table.add_column("Rows", justify="right")
        for t in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            table.add_row(t, str(count))
        console.print(table)
    finally:
        conn.close()


@app.command("show-brief")
def cmd_show_brief(
    path: Path = typer.Argument(..., help="Path to a brief YAML."),
) -> None:
    """Load and summarise a brief YAML."""
    brief = briefs.load_brief(path)
    console.print(f"[bold]{brief['name']}[/bold] ({brief['id']})")
    console.print(f"Customer: {brief['customer']}")
    console.print(f"Status: {brief.get('status', 'draft')}")
    included = briefs.included_sub_niches(brief)
    console.print(f"Included sub-niches: {len(included)}")
    for n in included:
        console.print(f"  - {n['id']}: {n['label']}")


@app.command("show-pitch")
def cmd_show_pitch(
    path: Path = typer.Argument(..., help="Path to a pitch YAML."),
) -> None:
    """Load and summarise a pitch YAML."""
    pitch = pitches.load_pitch(path)
    console.print(f"[bold]Pitch — customer: {pitch['customer']}[/bold]")
    console.print(f"One-liner: {pitch['one_liner'].strip()}")
    console.print(f"Pains solved: {len(pitch.get('pains_solved', []))}")
    console.print(f"Differentiation knobs: {len(pitch.get('differentiation', []))}")
    primary = pitch.get("cta", {}).get("primary", {})
    label = primary.get("label") if isinstance(primary, dict) else primary
    console.print(f"Primary CTA: {label or '?'}")


if __name__ == "__main__":
    app()
