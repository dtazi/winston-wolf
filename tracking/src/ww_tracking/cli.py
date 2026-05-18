"""ww-tracking CLI — run the tracking server."""

from __future__ import annotations

import typer
import uvicorn
from rich.console import Console

app = typer.Typer(help="Winston Wolf tracking server.")
console = Console()


@app.callback()
def _main() -> None:
    """Winston Wolf tracking server."""


@app.command("serve")
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
    reload: bool = typer.Option(False, help="Auto-reload (dev only)."),
) -> None:
    """Start the open-pixel + click-redirector server."""
    console.print(
        f"[bold]Winston Wolf tracking[/bold] starting on http://{host}:{port}"
    )
    console.print("Endpoints: /healthz  /p/{pixel_token}.gif  /c/{click_token}")
    uvicorn.run("ww_tracking.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
