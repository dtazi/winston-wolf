"""ww-eval CLI.

Subcommands:
  run             fire a customer's query set through chosen backends
  score           pattern-aware recall scoring against a customer's ground truth
  list-backends   show registered adapters
  list-customers  show registered customers
  list-patterns   show the Pattern taxonomy
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .backends.base import SearchBackend
from .backends.brave import BraveBackend
from .backends.exa import ExaBackend
from .backends.perplexity import PerplexityBackend
from .backends.serper import SerperBackend
from .backends.tavily import TavilyBackend
from .email_backends.apollo import ApolloBackend
from .email_backends.base import EmailBackend
from .email_backends.hunter import HunterBackend
from .llm.base import ICPExtractor
from .llm.claude import ClaudeICPExtractor
from .queries.base import Pattern, Query
from .queries.richbond import RICHBOND_QUERIES
from .runner import run as run_eval
from .scorer import load_ground_truth, score_run

app = typer.Typer(help="Winston Wolf vendor evaluation CLI.")
console = Console()


BACKEND_REGISTRY: dict[str, type[SearchBackend]] = {
    "exa": ExaBackend,
    "tavily": TavilyBackend,
    "brave": BraveBackend,
    "perplexity": PerplexityBackend,
    "serper": SerperBackend,
}

EMAIL_BACKEND_REGISTRY: dict[str, type[EmailBackend]] = {
    "hunter": HunterBackend,
    "apollo": ApolloBackend,
}


def _package_root() -> Path:
    return Path(__file__).resolve().parent


CUSTOMER_REGISTRY: dict[str, dict[str, object]] = {
    "richbond": {
        "queries": RICHBOND_QUERIES,
        "ground_truth": _package_root() / "ground_truth" / "richbond.yaml",
    },
}


def _filter_by_pattern(queries: list[Query], pattern: Optional[str]) -> list[Query]:
    if not pattern:
        return queries
    try:
        target = Pattern(pattern.upper())
    except ValueError:
        typer.echo(
            f"Unknown pattern: {pattern}. Known: {[p.value for p in Pattern]}"
        )
        raise typer.Exit(code=1)
    return [q for q in queries if q.pattern is target]


@app.command("run")
def cmd_run(
    customer: str = typer.Option(..., help="Customer name, e.g. 'richbond'."),
    backends: str = typer.Option("", help="Comma-separated search backend names, e.g. 'exa,tavily'."),
    email_backends: str = typer.Option("", help="Comma-separated email-finder backend names, e.g. 'hunter,apollo'."),
    pattern: Optional[str] = typer.Option(
        None,
        help="Optional pattern filter (A, B, C, D, or E). Default: all patterns.",
    ),
) -> None:
    """Fire the customer's query set through chosen backends; save raw responses."""
    load_dotenv()
    config = CUSTOMER_REGISTRY.get(customer)
    if not config:
        typer.echo(f"Unknown customer: {customer}. Known: {list(CUSTOMER_REGISTRY)}")
        raise typer.Exit(code=1)

    selected: list[SearchBackend] = []
    for name in (b.strip() for b in backends.split(",") if b.strip()):
        cls = BACKEND_REGISTRY.get(name)
        if not cls:
            typer.echo(f"Unknown backend: {name}. Known: {list(BACKEND_REGISTRY)}")
            raise typer.Exit(code=1)
        selected.append(cls())

    selected_email: list[EmailBackend] = []
    for name in (b.strip() for b in email_backends.split(",") if b.strip()):
        cls = EMAIL_BACKEND_REGISTRY.get(name)
        if not cls:
            typer.echo(f"Unknown email backend: {name}. Known: {list(EMAIL_BACKEND_REGISTRY)}")
            raise typer.Exit(code=1)
        selected_email.append(cls())

    queries = _filter_by_pattern(list(config["queries"]), pattern)  # type: ignore[arg-type]
    if not queries:
        typer.echo("No queries match the given filter.")
        raise typer.Exit(code=1)

    # Pattern D needs an ICP extractor. We shell out to `claude -p` and
    # let the user's Max subscription (CLAUDE_CODE_OAUTH_TOKEN) cover the
    # billing. The subprocess error surfaces at call time if the token is
    # missing or invalid.
    extractor: ICPExtractor | None = None
    if any(q.pattern is Pattern.ICP_FROM_URL for q in queries):
        extractor = ClaudeICPExtractor()

    output_dir = Path.cwd() / "results" / "raw" / customer
    run_dir = run_eval(
        selected,
        queries,
        output_dir,
        extractor=extractor,
        email_backends=selected_email or None,
    )
    console.print(f"[green]Run complete[/green] → {run_dir}")
    console.print(
        f"To score: [bold]uv run ww-eval score --customer {customer} "
        f"--run-id {run_dir.name}[/bold]"
    )


@app.command("score")
def cmd_score(
    customer: str = typer.Option(..., help="Customer name."),
    run_id: str = typer.Option(..., help="Run directory name (UTC timestamp)."),
    pattern: Optional[str] = typer.Option(
        None,
        help="Optional pattern filter for the score table. Default: all patterns.",
    ),
) -> None:
    """Score a previous run with pattern-aware recall."""
    config = CUSTOMER_REGISTRY.get(customer)
    if not config:
        typer.echo(f"Unknown customer: {customer}")
        raise typer.Exit(code=1)

    run_dir = Path.cwd() / "results" / "raw" / customer / run_id
    if not run_dir.exists():
        typer.echo(f"Run not found: {run_dir}")
        raise typer.Exit(code=1)

    ground_truth = load_ground_truth(config["ground_truth"])  # type: ignore[arg-type]
    queries = list(config["queries"])  # type: ignore[arg-type]

    if not ground_truth.contacts and not ground_truth.companies:
        console.print(
            "[yellow]Ground truth is empty — populate "
            f"{config['ground_truth']} before scoring is meaningful.[/yellow]"
        )
        return

    scores = score_run(run_dir, ground_truth, queries)
    if pattern:
        try:
            target = Pattern(pattern.upper())
        except ValueError:
            typer.echo(f"Unknown pattern: {pattern}")
            raise typer.Exit(code=1)
        scores = [s for s in scores if s.pattern is target]

    table = Table(title=f"Recall — {customer} run {run_id}")
    table.add_column("Pattern")
    table.add_column("Backend")
    table.add_column("Queries", justify="right")
    table.add_column("With results", justify="right")
    table.add_column("Skipped", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("Targets found / total", justify="right")
    table.add_column("Recall", justify="right")
    for s in scores:
        table.add_row(
            s.pattern.value,
            s.backend,
            str(s.queries_run),
            str(s.queries_with_results),
            str(s.queries_skipped),
            str(s.queries_errored),
            f"{len(s.targets_found)} / {s.targets_total}",
            f"{s.recall:.1%}",
        )
    console.print(table)


@app.command("list-backends")
def cmd_list_backends() -> None:
    """List registered backend adapters."""
    console.print("[bold]Search backends:[/bold]")
    for name in BACKEND_REGISTRY:
        console.print(f"  - {name}")
    console.print("[bold]Email backends:[/bold]")
    for name in EMAIL_BACKEND_REGISTRY:
        console.print(f"  - {name}")


@app.command("list-customers")
def cmd_list_customers() -> None:
    """List registered customers."""
    for name in CUSTOMER_REGISTRY:
        console.print(f"- {name}")


@app.command("list-patterns")
def cmd_list_patterns() -> None:
    """List the Pattern taxonomy."""
    descriptions = {
        Pattern.PEOPLE_AT_TARGET: "people at a known target company (scored vs contacts)",
        Pattern.COMPANY_DISCOVERY: "discover target companies matching an ICP (scored vs companies)",
        Pattern.FIND_SIMILAR: "find companies similar to a reference URL (Exa only; scored vs companies)",
        Pattern.ICP_FROM_URL: "LLM derives a brand-agnostic ICP from a URL; query fired through all backends (scored vs companies)",
        Pattern.EMAIL_FROM_NAME_COMPANY: "find email given (first name, last name, domain) — uses email_backends, scored against contacts' known emails",
    }
    for p in Pattern:
        console.print(f"- [bold]{p.value}[/bold]: {descriptions[p]}")


if __name__ == "__main__":
    app()
