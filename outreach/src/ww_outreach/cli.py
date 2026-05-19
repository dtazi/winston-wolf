"""ww-outreach CLI — send emails from a Microsoft 365 mailbox via Microsoft Graph."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console

from . import auth, send

app = typer.Typer(
    help="Winston Wolf Outreach — send emails from your Richbond mailbox via Microsoft Graph."
)
console = Console()


def _load_credentials() -> tuple[str, str]:
    load_dotenv()
    client_id = os.environ.get("AZURE_CLIENT_ID")
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    if not client_id or not tenant_id:
        console.print(
            "[red]AZURE_CLIENT_ID or AZURE_TENANT_ID missing — set them in .env[/red]"
        )
        raise typer.Exit(code=1)
    return client_id, tenant_id


@app.command("auth")
def cmd_auth() -> None:
    """Run the Microsoft device code flow and store the refresh token locally."""
    client_id, tenant_id = _load_credentials()
    console.print(
        "[bold]Starting device code flow.[/bold] Follow the instructions below.\n"
    )
    auth.acquire_token_interactive(client_id, tenant_id)
    console.print(
        f"\n[green]Auth complete.[/green] Token saved to {auth.TOKEN_FILE}"
    )


@app.command("send")
def cmd_send(
    to: str = typer.Option(..., help="Recipient email address."),
    subject: str = typer.Option(..., help="Subject line."),
    body_file: Path = typer.Option(
        ..., help="Path to a UTF-8 text file containing the message body."
    ),
) -> None:
    """Send one email through your Richbond mailbox."""
    client_id, tenant_id = _load_credentials()
    if not body_file.exists():
        console.print(f"[red]Body file not found: {body_file}[/red]")
        raise typer.Exit(code=1)
    body = body_file.read_text(encoding="utf-8")

    access_token = auth.acquire_token_silent(client_id, tenant_id)
    if not access_token:
        console.print(
            "[yellow]No valid session — running auth flow first.[/yellow]\n"
        )
        access_token = auth.acquire_token_interactive(client_id, tenant_id)

    send.send_email(access_token, to, subject, body)
    console.print(f"[green]Sent[/green] to {to} (subject: {subject!r})")


@app.command("revoke")
def cmd_revoke() -> None:
    """Delete the local token and print the Microsoft revocation URL."""
    deleted = auth.revoke_local()
    if deleted:
        console.print("[green]Local token deleted.[/green]")
    else:
        console.print("[yellow]No local token found.[/yellow]")
    console.print(
        "\nTo also revoke from Microsoft's side, go to:\n"
        "  [bold]https://myaccount.microsoft.com/[/bold]\n"
        "  → Settings & Privacy → Privacy → Apps and services you've authorized\n"
        "  → Find 'Assistant Mail Djaafar (Winston Wolf Outreach)' → Remove."
    )


if __name__ == "__main__":
    app()
