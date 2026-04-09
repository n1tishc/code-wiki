"""CodeWiki CLI — AI-powered codebase wiki generator."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from codewiki import __version__
from codewiki.config import (
    CodeWikiConfig,
    get_codewiki_dir,
    init_codewiki,
    load_config,
    save_config,
)

app = typer.Typer(
    name="codewiki",
    help="AI-powered codebase wiki generator.",
    no_args_is_help=True,
)
console = Console()


def _require_init(base_path: Path | None = None) -> CodeWikiConfig:
    """Ensure codewiki is initialized, return config."""
    cw_dir = get_codewiki_dir(base_path)
    if not cw_dir.exists():
        console.print("[red]Error:[/red] CodeWiki not initialized. Run `codewiki init` first.")
        raise typer.Exit(1)
    return load_config(base_path)


@app.command()
def init(
    path: Optional[Path] = typer.Argument(None, help="Directory to initialize (default: current)"),
    vault: Optional[Path] = typer.Option(None, "--vault", "-V", help="Obsidian vault path to store wiki pages"),
) -> None:
    """Initialize a CodeWiki in the target directory."""
    base = path or Path.cwd()
    cw_dir = get_codewiki_dir(base)

    if cw_dir.exists():
        console.print(f"[yellow]CodeWiki already initialized at {cw_dir}[/yellow]")
        raise typer.Exit(0)

    init_codewiki(base, obsidian_vault=str(vault.resolve()) if vault else None)

    if vault:
        console.print(Panel(
            f"[green]CodeWiki initialized at {cw_dir}[/green]\n\n"
            f"Wiki pages will be stored in Obsidian vault: [bold]{vault.resolve()}[/bold]\n\n"
            "Next steps:\n"
            "  1. Edit [bold].codewiki/config.yaml[/bold] to set your LLM provider\n"
            "  2. Run [bold]codewiki ingest <path>[/bold] to generate your wiki",
            title="CodeWiki",
        ))
    else:
        console.print(Panel(
            f"[green]CodeWiki initialized at {cw_dir}[/green]\n\n"
            "Next steps:\n"
            "  1. Edit [bold].codewiki/config.yaml[/bold] to set your LLM provider\n"
            "  2. Run [bold]codewiki ingest <path>[/bold] to generate your wiki",
            title="CodeWiki",
        ))


@app.command()
def ingest(
    target: Path = typer.Argument(..., help="Path to the codebase to ingest"),
    base: Optional[Path] = typer.Option(None, "--base", "-b", help="CodeWiki base directory"),
) -> None:
    """Ingest a codebase and generate wiki pages."""
    config = _require_init(base)
    target = target.resolve()

    if not target.is_dir():
        console.print(f"[red]Error:[/red] {target} is not a directory.")
        raise typer.Exit(1)

    from codewiki.core.ingest import run_ingest
    run_ingest(target, config, base_path=base)


@app.command()
def query(
    question: str = typer.Argument(..., help="Question to ask about the codebase"),
    base: Optional[Path] = typer.Option(None, "--base", "-b", help="CodeWiki base directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show which pages were consulted"),
) -> None:
    """Ask a question about the codebase using the wiki."""
    config = _require_init(base)

    from codewiki.core.query import run_query
    run_query(question, config, base_path=base, verbose=verbose)


@app.command()
def evolve(
    base: Optional[Path] = typer.Option(None, "--base", "-b", help="CodeWiki base directory"),
) -> None:
    """Update wiki pages based on recent git changes."""
    config = _require_init(base)

    from codewiki.core.evolve import run_evolve
    run_evolve(config, base_path=base)


@app.command()
def lint(
    base: Optional[Path] = typer.Option(None, "--base", "-b", help="CodeWiki base directory"),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix broken links and regenerate index"),
) -> None:
    """Run health checks on the wiki."""
    config = _require_init(base)

    if fix:
        from codewiki.wiki.crossref import strip_broken_links
        from codewiki.wiki.index import generate_index
        removed = strip_broken_links(base_path=base, config=config)
        generate_index(base_path=base, config=config)
        console.print(f"[green]Fixed:[/green] removed {removed} broken link(s), regenerated index.")

    from codewiki.core.lint import run_lint
    run_lint(config, base_path=base)


@app.command()
def watch(
    base: Optional[Path] = typer.Option(None, "--base", "-b", help="CodeWiki base directory"),
) -> None:
    """Watch for git changes and auto-evolve the wiki."""
    config = _require_init(base)

    from codewiki.core.watch import run_watch
    run_watch(config, base_path=base)


@app.command(name="config")
def config_cmd(
    key: Optional[str] = typer.Argument(None, help="Config key (dot-notation, e.g. llm.provider)"),
    value: Optional[str] = typer.Option(None, "--set", "-s", help="Set config value"),
    base: Optional[Path] = typer.Option(None, "--base", "-b", help="CodeWiki base directory"),
) -> None:
    """View or update CodeWiki configuration."""
    config = _require_init(base)

    if key is None:
        # Show full config
        import yaml
        console.print(yaml.dump(config.to_dict(), default_flow_style=False, sort_keys=False))
        return

    if value is None:
        # Get a specific key
        obj = config.to_dict()
        for part in key.split("."):
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                console.print(f"[red]Unknown config key:[/red] {key}")
                raise typer.Exit(1)
        console.print(obj)
        return

    # Set a specific key
    obj = config.to_dict()
    parts = key.split(".")
    target = obj
    for part in parts[:-1]:
        if isinstance(target, dict) and part in target:
            target = target[part]
        else:
            console.print(f"[red]Unknown config key:[/red] {key}")
            raise typer.Exit(1)

    if parts[-1] not in target:
        console.print(f"[red]Unknown config key:[/red] {key}")
        raise typer.Exit(1)

    # Auto-convert types
    old_val = target[parts[-1]]
    if isinstance(old_val, bool):
        target[parts[-1]] = value.lower() in ("true", "1", "yes")
    elif isinstance(old_val, int):
        target[parts[-1]] = int(value)
    elif isinstance(old_val, float):
        target[parts[-1]] = float(value)
    else:
        target[parts[-1]] = value if value != "null" else None

    new_config = CodeWikiConfig.from_dict(obj)
    save_config(new_config, base)
    console.print(f"[green]Set {key} = {value}[/green]")


@app.command()
def version() -> None:
    """Show CodeWiki version."""
    console.print(f"codewiki v{__version__}")
