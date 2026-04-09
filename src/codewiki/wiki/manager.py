"""Wiki page CRUD with YAML frontmatter support."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter

from codewiki.config import CodeWikiConfig, get_wiki_dir


@dataclass
class PageInfo:
    path: Path
    relative_path: str
    title: str
    source_files: list[str]
    generated_at: str


def _compute_checksum(file_path: Path) -> str:
    """Compute SHA256 checksum of a file."""
    sha = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()[:16]
    except OSError:
        return ""


def _extract_title(content: str) -> str:
    """Extract the first markdown heading as the page title."""
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Untitled"


class WikiManager:
    """Manages wiki page operations."""

    def __init__(self, base_path: Path | None = None, config: CodeWikiConfig | None = None):
        self.wiki_dir = get_wiki_dir(base_path, config)

    def read_page(self, page_path: str) -> tuple[dict[str, Any], str] | None:
        """Read a wiki page, returning (metadata, content) or None."""
        full_path = self.wiki_dir / page_path
        if not full_path.exists():
            return None
        post = frontmatter.load(str(full_path))
        return dict(post.metadata), post.content

    def write_page(
        self,
        page_path: str,
        content: str,
        source_files: list[str] | None = None,
        source_root: Path | None = None,
    ) -> None:
        """Write a wiki page with YAML frontmatter."""
        full_path = self.wiki_dir / page_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        metadata: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if source_files:
            metadata["source_files"] = source_files
            if source_root:
                metadata["source_checksums"] = {
                    f: _compute_checksum(source_root / f) for f in source_files
                }

        post = frontmatter.Post(content, **metadata)
        full_path.write_text(frontmatter.dumps(post))

    def page_exists(self, page_path: str) -> bool:
        """Check if a wiki page exists."""
        return (self.wiki_dir / page_path).exists()

    def list_pages(self) -> list[PageInfo]:
        """List all wiki pages with metadata."""
        pages: list[PageInfo] = []
        for md_file in self.wiki_dir.rglob("*.md"):
            relative = str(md_file.relative_to(self.wiki_dir))
            try:
                post = frontmatter.load(str(md_file))
                pages.append(PageInfo(
                    path=md_file,
                    relative_path=relative,
                    title=_extract_title(post.content),
                    source_files=post.metadata.get("source_files", []),
                    generated_at=post.metadata.get("generated_at", ""),
                ))
            except Exception:
                pages.append(PageInfo(
                    path=md_file,
                    relative_path=relative,
                    title=_extract_title(md_file.read_text()),
                    source_files=[],
                    generated_at="",
                ))
        return pages

    def is_stale(self, page_path: str, source_root: Path) -> bool:
        """Check if a page's source files have changed since generation."""
        result = self.read_page(page_path)
        if result is None:
            return True
        metadata, _ = result
        stored_checksums = metadata.get("source_checksums", {})
        if not stored_checksums:
            return True
        for filepath, stored_hash in stored_checksums.items():
            current_hash = _compute_checksum(source_root / filepath)
            if current_hash != stored_hash:
                return True
        return False

    def find_pages_for_source(self, source_file: str) -> list[str]:
        """Find wiki pages that reference a given source file."""
        matching: list[str] = []
        for page in self.list_pages():
            if source_file in page.source_files:
                matching.append(page.relative_path)
        return matching
