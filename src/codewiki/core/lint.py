"""Wiki health checks and gap analysis."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from codewiki.config import CodeWikiConfig
from codewiki.core.scanner import scan_codebase
from codewiki.wiki.crossref import validate_links
from codewiki.wiki.manager import WikiManager

console = Console()


def run_lint(
    config: CodeWikiConfig,
    base_path: Path | None = None,
) -> None:
    """Run health checks on the wiki."""
    manager = WikiManager(base_path, config)
    pages = manager.list_pages()
    issues: list[tuple[str, str, str]] = []  # (severity, category, message)

    target_path = config.state.target_path
    target = Path(target_path).resolve() if target_path else None

    console.print("\n[bold]Running wiki health checks...[/bold]\n")

    # 1. Stale pages — source files changed since wiki was generated
    if target and target.exists():
        for page in pages:
            if page.relative_path.startswith("_"):
                continue
            if not page.source_files:
                continue
            if manager.is_stale(page.relative_path, target):
                issues.append((
                    "warning",
                    "Stale",
                    f"{page.relative_path} — source files have changed since generation",
                ))

    # 2. Orphan pages — wiki pages whose source files no longer exist
    if target and target.exists():
        for page in pages:
            if page.relative_path.startswith("_"):
                continue
            for src in page.source_files:
                if not (target / src).exists():
                    issues.append((
                        "error",
                        "Orphan",
                        f"{page.relative_path} references deleted file: {src}",
                    ))

    # 3. Broken links
    broken = validate_links(base_path, config)
    for issue in broken:
        issues.append(("error", "Broken Link", issue))

    # 4. Missing modules — codebase directories with no wiki page
    if target and target.exists():
        scanned = scan_codebase(target, config.scanner)
        documented_sources: set[str] = set()
        for page in pages:
            documented_sources.update(page.source_files)

        undocumented = [f for f in scanned if f.relative_path not in documented_sources]
        if undocumented:
            # Group by module
            modules: dict[str, int] = {}
            for f in undocumented:
                parts = f.relative_path.split("/")
                module = parts[0] if len(parts) > 1 else "_root"
                modules[module] = modules.get(module, 0) + 1

            for module, count in sorted(modules.items()):
                issues.append((
                    "info",
                    "Coverage Gap",
                    f"Module '{module}' has {count} undocumented file(s)",
                ))

    # 5. Empty or very short pages
    for page in pages:
        if page.relative_path.startswith("_"):
            continue
        if page.relative_path in ("index.md", "log.md"):
            continue
        result = manager.read_page(page.relative_path)
        if result:
            _, content = result
            if len(content.strip()) < 50:
                issues.append((
                    "warning",
                    "Thin Content",
                    f"{page.relative_path} has very little content ({len(content.strip())} chars)",
                ))

    # Display results
    if not issues:
        console.print("[green bold]All checks passed![/green bold] Wiki is healthy.\n")
        return

    table = Table(title="Wiki Health Report")
    table.add_column("Severity", style="bold", width=10)
    table.add_column("Category", width=15)
    table.add_column("Details")

    severity_styles = {"error": "red", "warning": "yellow", "info": "blue"}
    for severity, category, message in sorted(issues, key=lambda x: {"error": 0, "warning": 1, "info": 2}[x[0]]):
        table.add_row(
            f"[{severity_styles[severity]}]{severity}[/{severity_styles[severity]}]",
            category,
            message,
        )

    console.print(table)

    errors = sum(1 for s, _, _ in issues if s == "error")
    warnings = sum(1 for s, _, _ in issues if s == "warning")
    infos = sum(1 for s, _, _ in issues if s == "info")
    console.print(f"\n  {errors} error(s), {warnings} warning(s), {infos} info(s)\n")
