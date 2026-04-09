"""Index page generation for the wiki."""

from __future__ import annotations

from pathlib import Path

import re

from codewiki.config import CodeWikiConfig, get_wiki_dir
from codewiki.constants import INDEX_FILE
from codewiki.wiki.manager import WikiManager


def _safe_title(title: str) -> str:
    """Escape brackets in titles so they don't break markdown link syntax."""
    return re.sub(r"[\[\]]", "", title).strip() or "Untitled"


def generate_index(base_path: Path | None = None, config: CodeWikiConfig | None = None) -> None:
    """Generate index.md from all wiki pages."""
    wiki_dir = get_wiki_dir(base_path, config)
    manager = WikiManager(base_path, config)
    pages = manager.list_pages()

    # Group pages by section, skipping internal (_) pages
    sections: dict[str, list[tuple[str, str]]] = {}
    standalone: list[tuple[str, str]] = []

    for page in pages:
        if page.relative_path in ("index.md", "log.md"):
            continue
        # Skip internal pages (prefixed with _)
        parts = page.relative_path.split("/")
        if parts[0].startswith("_"):
            continue
        title = _safe_title(page.title)
        if len(parts) > 1:
            section = parts[0]
            sections.setdefault(section, []).append((page.relative_path, title))
        else:
            standalone.append((page.relative_path, title))

    lines = ["# CodeWiki Index\n"]

    if standalone:
        lines.append("## Overview\n")
        for rel_path, title in sorted(standalone):
            lines.append(f"- [{title}]({rel_path})")
        lines.append("")

    for section_name in sorted(sections.keys()):
        lines.append(f"## {section_name.title()}\n")
        for rel_path, title in sorted(sections[section_name]):
            lines.append(f"- [{title}]({rel_path})")
        lines.append("")

    index_path = wiki_dir / INDEX_FILE
    index_path.write_text("\n".join(lines))
