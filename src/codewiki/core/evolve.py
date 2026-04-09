"""Incremental wiki update pipeline based on git diffs."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from codewiki.config import CodeWikiConfig, save_config
from codewiki.core.scanner import detect_language, scan_codebase
from codewiki.git.analyzer import GitAnalyzer
from codewiki.llm.client import LLMClient
from codewiki.llm.prompts import PromptRegistry
from codewiki.wiki.crossref import insert_crossrefs, strip_broken_links
from codewiki.wiki.index import generate_index
from codewiki.wiki.log import append_log
from codewiki.wiki.manager import WikiManager

console = Console()

SYSTEM_PROMPT = (
    "You are a technical documentation expert. Update wiki pages to reflect "
    "code changes accurately. Preserve existing structure, only modify affected sections."
)


def run_evolve(
    config: CodeWikiConfig,
    base_path: Path | None = None,
) -> None:
    """Run the incremental evolve pipeline."""
    target_path = config.state.target_path
    if not target_path:
        console.print("[red]Error:[/red] No target path found. Run `codewiki ingest` first.")
        return

    target = Path(target_path).resolve()
    if not target.exists():
        console.print(f"[red]Error:[/red] Target path {target} no longer exists.")
        return

    last_ref = config.state.last_evolve_ref
    if not last_ref:
        console.print("[yellow]No previous evolve reference found. Using last ingest state.[/yellow]")
        console.print("Consider running `codewiki ingest` for a full rebuild instead.")
        return

    # Analyze git changes
    analyzer = GitAnalyzer(target)
    if not analyzer.is_git_repo():
        console.print("[red]Error:[/red] Target is not a git repository.")
        return

    current_ref = analyzer.get_current_ref()
    if current_ref == last_ref:
        console.print("[green]Wiki is up to date.[/green] No changes since last evolve.")
        return

    changes = analyzer.get_changes_since(last_ref)
    if not changes:
        console.print("[green]No file changes detected.[/green]")
        config.state.last_evolve_ref = current_ref
        save_config(config, base_path)
        return

    commit_messages = analyzer.get_commit_messages_since(last_ref)
    console.print(f"\n[bold]Found {len(changes)} changed files[/bold] across {len(commit_messages)} commits.\n")

    client = LLMClient(config.llm)
    prompts = PromptRegistry(config.prompts or None)
    manager = WikiManager(base_path, config)

    # Categorize changes
    added = [c for c in changes if c.change_type == "added"]
    modified = [c for c in changes if c.change_type in ("modified", "renamed")]
    deleted = [c for c in changes if c.change_type == "deleted"]

    pages_updated = 0

    # Handle modified files
    for change in modified:
        affected_pages = manager.find_pages_for_source(change.path)
        if not affected_pages:
            continue

        # Re-summarize the changed file
        file_path = target / change.path
        if not file_path.exists():
            continue

        content = file_path.read_text(errors="replace")
        file_summary_prompt = prompts.render(
            "file_summary",
            file_path=change.path,
            language=detect_language(file_path),
            content=content[:8000],  # Truncate very large files
        )
        new_summary = client.complete(SYSTEM_PROMPT, file_summary_prompt)

        # Update each affected wiki page
        for page_path in affected_pages:
            result = manager.read_page(page_path)
            if result is None:
                continue
            _, current_content = result

            console.print(f"  Updating [bold]{page_path}[/bold]...")
            update_prompt = prompts.render(
                "evolve_update",
                current_page=current_content,
                diff=change.diff_text[:3000],  # Truncate large diffs
                file_summaries=new_summary,
                commit_messages="\n".join(commit_messages[:10]),
            )
            updated_content = client.complete(SYSTEM_PROMPT, update_prompt)

            result_meta = manager.read_page(page_path)
            source_files = result_meta[0].get("source_files", []) if result_meta else []
            manager.write_page(page_path, updated_content, source_files=source_files, source_root=target)
            pages_updated += 1

    # Handle added files — summarize and add to appropriate module page
    for change in added:
        file_path = target / change.path
        if not file_path.exists():
            continue

        console.print(f"  Processing new file: [bold]{change.path}[/bold]...")
        content = file_path.read_text(errors="replace")
        summary_prompt = prompts.render(
            "file_summary",
            file_path=change.path,
            language=detect_language(file_path),
            content=content[:8000],
        )
        summary = client.complete(SYSTEM_PROMPT, summary_prompt)

        # Cache the summary
        manager.write_page(
            f"_summaries/{change.path}.md",
            summary,
            source_files=[change.path],
            source_root=target,
        )

        # Find the module this file belongs to
        parts = change.path.split("/")
        module_name = parts[0] if len(parts) > 1 else "_root"
        safe_name = module_name.replace("/", "_").replace(".", "_")
        module_page = f"modules/{safe_name}.md"

        if manager.page_exists(module_page):
            result = manager.read_page(module_page)
            if result:
                _, current_content = result
                update_prompt = (
                    f"Add documentation for a new file `{change.path}` to this module page.\n\n"
                    f"**Current page:**\n{current_content}\n\n"
                    f"**New file summary:**\n{summary}\n\n"
                    "Integrate naturally into the existing structure."
                )
                updated = client.complete(SYSTEM_PROMPT, update_prompt)
                source_files = result[0].get("source_files", []) if result else []
                source_files.append(change.path)
                manager.write_page(module_page, updated, source_files=source_files, source_root=target)
                pages_updated += 1

    # Handle deleted files — update references
    for change in deleted:
        affected_pages = manager.find_pages_for_source(change.path)
        for page_path in affected_pages:
            result = manager.read_page(page_path)
            if result is None:
                continue
            _, current_content = result

            console.print(f"  Removing references to deleted file: [bold]{change.path}[/bold]...")
            update_prompt = (
                f"The file `{change.path}` has been deleted from the codebase. "
                f"Update this wiki page to remove references to it.\n\n"
                f"**Current page:**\n{current_content}"
            )
            updated = client.complete(SYSTEM_PROMPT, update_prompt)
            source_files = [f for f in (result[0].get("source_files", []) if result else [])
                           if f != change.path]
            manager.write_page(page_path, updated, source_files=source_files, source_root=target)
            pages_updated += 1

    # Update cross-references and index
    strip_broken_links(base_path, config)
    insert_crossrefs(base_path, config)
    generate_index(base_path, config)

    # Log and update state
    append_log(
        "evolve",
        f"Updated {pages_updated} pages. Changes: +{len(added)} ~{len(modified)} -{len(deleted)} files.",
        base_path,
        config,
    )
    config.state.last_evolve_ref = current_ref
    save_config(config, base_path)

    console.print(f"\n[green bold]Done![/green bold] Updated {pages_updated} wiki pages.\n")
