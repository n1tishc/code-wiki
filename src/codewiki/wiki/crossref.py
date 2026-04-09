"""Cross-reference link insertion and validation for wiki pages."""

from __future__ import annotations

import os
import re
from pathlib import Path

from codewiki.config import CodeWikiConfig, get_wiki_dir
from codewiki.wiki.manager import WikiManager


def strip_broken_links(base_path: Path | None = None, config: CodeWikiConfig | None = None) -> int:
    """Remove markdown links that point to non-existent files, keeping just the link text.
    Returns count of links removed."""
    wiki_dir = get_wiki_dir(base_path, config)
    links_removed = 0

    for md_file in wiki_dir.rglob("*.md"):
        content = md_file.read_text()
        modified = False

        def _replace_if_broken(m: re.Match) -> str:
            link_text, link_target = m.group(1), m.group(2)
            # Skip external URLs and anchors
            if link_target.startswith(("http://", "https://", "#", "mailto:")):
                return m.group(0)
            target_path = (md_file.parent / link_target).resolve()
            if not target_path.exists():
                return link_text  # Strip link, keep text
            return m.group(0)

        new_content = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _replace_if_broken, content)
        removed = content.count("[") - new_content.count("[")
        if new_content != content:
            md_file.write_text(new_content)
            links_removed += removed
            modified = True

    return links_removed


def validate_links(base_path: Path | None = None, config: CodeWikiConfig | None = None) -> list[str]:
    """Validate all markdown links in wiki pages. Returns list of issues."""
    wiki_dir = get_wiki_dir(base_path, config)
    issues: list[str] = []

    for md_file in wiki_dir.rglob("*.md"):
        content = md_file.read_text()
        relative = str(md_file.relative_to(wiki_dir))

        # Find all markdown links: [text](path)
        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content):
            link_text, link_target = match.group(1), match.group(2)
            # Skip external URLs and anchors
            if link_target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            # Resolve relative to the page's directory
            target_path = (md_file.parent / link_target).resolve()
            if not target_path.exists():
                issues.append(f"{relative}: broken link [{link_text}]({link_target})")

    return issues


def insert_crossrefs(base_path: Path | None = None, config: CodeWikiConfig | None = None) -> int:
    """Scan wiki pages and insert cross-reference links where module/pattern names
    are mentioned but not linked. Returns count of links inserted."""
    wiki_dir = get_wiki_dir(base_path, config)
    manager = WikiManager(base_path, config)
    pages = manager.list_pages()

    # Build a map of page titles to their relative paths
    title_to_path: dict[str, str] = {}
    for page in pages:
        if page.relative_path in ("index.md", "log.md"):
            continue
        if page.title and page.title != "Untitled":
            title_to_path[page.title] = page.relative_path

    links_inserted = 0

    for md_file in wiki_dir.rglob("*.md"):
        relative = str(md_file.relative_to(wiki_dir))
        if relative in ("index.md", "log.md"):
            continue

        content = md_file.read_text()
        modified = False

        for title, target_path in title_to_path.items():
            if target_path == relative:
                continue  # Don't self-link

            # Calculate relative link from current page to target
            from_dir = str(Path(relative).parent)
            rel_link = os.path.relpath(target_path, from_dir)

            # Skip if already linked to this target
            if rel_link in content or target_path in content:
                continue

            # Find unlinked mentions of the title (not inside existing links)
            # Only match whole words, case-insensitive
            pattern = rf"(?<!\[)(?<!\()\b({re.escape(title)})\b(?!\])(?!\))"
            replacement = f"[{title}]({rel_link})"

            new_content, count = re.subn(pattern, replacement, content, count=1)
            if count > 0:
                content = new_content
                links_inserted += count
                modified = True

        if modified:
            md_file.write_text(content)

    return links_inserted
