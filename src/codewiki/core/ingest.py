"""Full ingest pipeline — scan a codebase and generate the wiki."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from codewiki.config import CodeWikiConfig, save_config
from codewiki.core.scanner import FileInfo, scan_codebase
from codewiki.llm.chunking import chunk_text, count_tokens
from codewiki.llm.client import LLMClient
from codewiki.llm.prompts import PromptRegistry
from codewiki.wiki.crossref import insert_crossrefs, strip_broken_links
from codewiki.wiki.index import generate_index
from codewiki.wiki.log import append_log
from codewiki.wiki.manager import WikiManager

console = Console()

SYSTEM_PROMPT = (
    "You are a technical documentation expert. You produce clear, accurate, "
    "well-structured markdown documentation for codebases. Use relative markdown "
    "links to reference other wiki pages. Be concise but thorough."
)


def _summarize_file(
    file_info: FileInfo,
    client: LLMClient,
    prompts: PromptRegistry,
    source_root: Path,
) -> str:
    """Generate a summary for a single source file."""
    content = file_info.path.read_text(errors="replace")

    chunks = chunk_text(content)
    if len(chunks) == 1:
        prompt = prompts.render(
            "file_summary",
            file_path=file_info.relative_path,
            language=file_info.language,
            content=content,
        )
        return client.complete(SYSTEM_PROMPT, prompt)

    # Multi-chunk: summarize each chunk, then combine
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        prompt = prompts.render(
            "file_summary",
            file_path=f"{file_info.relative_path} (part {i+1}/{len(chunks)})",
            language=file_info.language,
            content=chunk,
        )
        chunk_summaries.append(client.complete(SYSTEM_PROMPT, prompt))

    # Combine chunk summaries
    combined_prompt = (
        f"Combine these partial summaries of `{file_info.relative_path}` into one "
        f"coherent summary using the same structure:\n\n"
        + "\n\n---\n\n".join(chunk_summaries)
    )
    return client.complete(SYSTEM_PROMPT, combined_prompt)


def _group_by_module(files: list[FileInfo]) -> dict[str, list[FileInfo]]:
    """Group files by their top-level directory (module)."""
    modules: dict[str, list[FileInfo]] = {}
    for f in files:
        parts = f.relative_path.split("/")
        module = parts[0] if len(parts) > 1 else "_root"
        modules.setdefault(module, []).append(f)
    return modules


def _find_manifests(target: Path) -> str:
    """Read dependency manifest files if they exist."""
    manifest_names = [
        "requirements.txt", "setup.py", "pyproject.toml",
        "package.json", "Cargo.toml", "go.mod", "Gemfile",
        "pom.xml", "build.gradle",
    ]
    parts = []
    for name in manifest_names:
        p = target / name
        if p.exists():
            try:
                content = p.read_text(errors="replace")
                parts.append(f"--- {name} ---\n{content}")
            except OSError:
                continue
    return "\n\n".join(parts)


def run_ingest(
    target: Path,
    config: CodeWikiConfig,
    base_path: Path | None = None,
) -> None:
    """Run the full ingest pipeline."""
    target = target.resolve()
    client = LLMClient(config.llm)
    prompts = PromptRegistry(config.prompts or None)
    manager = WikiManager(base_path, config)

    # Step 1: Scan
    console.print(f"\n[bold]Scanning[/bold] {target}...")
    files = scan_codebase(target, config.scanner)

    if not files:
        console.print("[yellow]No files found matching scanner config.[/yellow]")
        return

    console.print(f"  Found [bold]{len(files)}[/bold] files to process.\n")

    # Step 2: Per-file summaries
    summaries: dict[str, str] = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Summarizing files...", total=len(files))

        for file_info in files:
            progress.update(task, description=f"Summarizing {file_info.relative_path}...")
            # Strip any existing .md extension to avoid double .md.md
            summary_key = re.sub(r"\.md$", "", file_info.relative_path)
            summary_page = f"_summaries/{summary_key}.md"

            if not manager.is_stale(summary_page, target):
                # Read cached summary
                result = manager.read_page(summary_page)
                if result:
                    summaries[file_info.relative_path] = result[1]
                    progress.advance(task)
                    continue

            summary = _summarize_file(file_info, client, prompts, target)
            summaries[file_info.relative_path] = summary

            # Cache the summary
            manager.write_page(
                summary_page,
                summary,
                source_files=[file_info.relative_path],
                source_root=target,
            )
            progress.advance(task)

    all_summaries_text = "\n\n---\n\n".join(
        f"### `{path}`\n{summary}" for path, summary in summaries.items()
    )

    # Step 3: Architecture page
    console.print("[bold]Generating[/bold] architecture overview...")
    arch_prompt = prompts.render("architecture", file_summaries=all_summaries_text)
    architecture = client.complete(SYSTEM_PROMPT, arch_prompt)
    manager.write_page(
        "architecture.md",
        architecture,
        source_files=list(summaries.keys()),
        source_root=target,
    )

    # Step 4: Module pages
    modules = _group_by_module(files)
    for module_name, module_files in modules.items():
        console.print(f"[bold]Generating[/bold] module page: {module_name}...")
        module_summaries = "\n\n".join(
            f"### `{f.relative_path}`\n{summaries.get(f.relative_path, 'No summary available.')}"
            for f in module_files
        )
        page_prompt = prompts.render(
            "module_page",
            module_name=module_name,
            architecture_summary=architecture[:2000],  # Truncate for context
            file_summaries=module_summaries,
        )
        page_content = client.complete(SYSTEM_PROMPT, page_prompt)
        safe_name = module_name.replace("/", "_").replace(".", "_")
        manager.write_page(
            f"modules/{safe_name}.md",
            page_content,
            source_files=[f.relative_path for f in module_files],
            source_root=target,
        )

    # Step 5: Patterns page
    console.print("[bold]Identifying[/bold] patterns...")
    patterns_prompt = prompts.render("patterns", file_summaries=all_summaries_text)
    patterns_content = client.complete(SYSTEM_PROMPT, patterns_prompt)
    manager.write_page(
        "patterns/overview.md",
        patterns_content,
        source_files=list(summaries.keys()),
        source_root=target,
    )

    # Step 6: Decisions page
    console.print("[bold]Inferring[/bold] architectural decisions...")
    decisions_prompt = prompts.render("decisions", file_summaries=all_summaries_text)
    decisions_content = client.complete(SYSTEM_PROMPT, decisions_prompt)
    manager.write_page(
        "decisions/initial.md",
        decisions_content,
        source_files=list(summaries.keys()),
        source_root=target,
    )

    # Step 7: Dependencies page
    console.print("[bold]Mapping[/bold] dependencies...")
    manifest_content = _find_manifests(target)
    deps_prompt = prompts.render(
        "dependencies",
        file_summaries=all_summaries_text,
        manifest_content=manifest_content,
    )
    deps_content = client.complete(SYSTEM_PROMPT, deps_prompt)
    manager.write_page(
        "dependencies.md",
        deps_content,
        source_files=list(summaries.keys()),
        source_root=target,
    )

    # Step 8: Onboarding page
    console.print("[bold]Writing[/bold] onboarding guide...")
    module_summaries_text = "\n\n".join(
        f"### {name}\n{summaries.get(files[0].relative_path, '')[:500]}"
        for name, files in modules.items()
    )
    onboard_prompt = prompts.render(
        "onboarding",
        architecture=architecture,
        module_summaries=module_summaries_text,
    )
    onboarding_content = client.complete(SYSTEM_PROMPT, onboard_prompt)
    manager.write_page("onboarding.md", onboarding_content)

    # Step 9: Strip broken links left by LLM hallucinations
    console.print("[bold]Cleaning[/bold] broken links...")
    removed = strip_broken_links(base_path, config)
    if removed:
        console.print(f"  Removed {removed} broken link(s).")

    # Step 10: Cross-references
    console.print("[bold]Inserting[/bold] cross-references...")
    links = insert_crossrefs(base_path, config)
    console.print(f"  Inserted {links} cross-reference links.")

    # Step 11: Index
    console.print("[bold]Generating[/bold] index...")
    generate_index(base_path, config)

    # Step 12: Log
    append_log("ingest", f"Ingested {len(files)} files from {target}", base_path, config)

    # Update state
    from datetime import datetime, timezone
    config.state.target_path = str(target)
    config.state.last_ingest_at = datetime.now(timezone.utc).isoformat()
    save_config(config, base_path)

    wiki_dir = manager.wiki_dir
    console.print(f"\n[green bold]Done![/green bold] Wiki generated with {len(files)} source files.")
    console.print(f"  View at: {wiki_dir}/index.md\n")
