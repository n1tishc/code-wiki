"""File watcher for auto-evolve mode."""

from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from codewiki.config import CodeWikiConfig, load_config
from codewiki.core.evolve import run_evolve

console = Console()


class _GitRefHandler(FileSystemEventHandler):
    """Watches for git ref changes (commits, branch switches)."""

    def __init__(self, config: CodeWikiConfig, base_path: Path | None, debounce: int):
        self.config = config
        self.base_path = base_path
        self.debounce = debounce
        self._last_trigger = 0.0

    def on_modified(self, event):
        if event.is_directory:
            return
        now = time.time()
        if now - self._last_trigger < self.debounce:
            return
        self._last_trigger = now
        console.print(f"\n[bold]Change detected:[/bold] {event.src_path}")
        console.print("[bold]Running evolve...[/bold]\n")
        try:
            # Reload config in case it changed
            self.config = load_config(self.base_path)
            run_evolve(self.config, self.base_path)
        except Exception as e:
            console.print(f"[red]Evolve failed:[/red] {e}")


def run_watch(
    config: CodeWikiConfig,
    base_path: Path | None = None,
) -> None:
    """Watch for git changes and auto-evolve the wiki."""
    target_path = config.state.target_path
    if not target_path:
        console.print("[red]Error:[/red] No target path found. Run `codewiki ingest` first.")
        return

    target = Path(target_path).resolve()
    git_refs_dir = target / ".git" / "refs" / "heads"

    if not git_refs_dir.exists():
        console.print("[red]Error:[/red] Not a git repository or .git/refs/heads not found.")
        return

    debounce = config.evolve.debounce_seconds
    handler = _GitRefHandler(config, base_path, debounce)
    observer = Observer()
    observer.schedule(handler, str(git_refs_dir), recursive=True)

    console.print(f"[bold]Watching[/bold] {target} for git changes...")
    console.print(f"  Debounce: {debounce}s")
    console.print("  Press Ctrl+C to stop.\n")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold]Stopping watcher...[/bold]")
        observer.stop()
    observer.join()
