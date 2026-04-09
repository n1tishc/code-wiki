"""Tests for wiki lint/health checks."""

from pathlib import Path

import frontmatter

from codewiki.config import CodeWikiConfig, init_codewiki
from codewiki.wiki.crossref import validate_links


def test_validate_links_no_issues(tmp_path: Path):
    init_codewiki(tmp_path)
    wiki_dir = tmp_path / ".codewiki" / "wiki"
    (wiki_dir / "test.md").write_text("# Test\n\nSome content with no links.")
    issues = validate_links(tmp_path)
    assert len(issues) == 0


def test_validate_links_broken(tmp_path: Path):
    init_codewiki(tmp_path)
    wiki_dir = tmp_path / ".codewiki" / "wiki"
    (wiki_dir / "test.md").write_text("# Test\n\nSee [missing](nonexistent.md) page.")
    issues = validate_links(tmp_path)
    assert len(issues) == 1
    assert "broken link" in issues[0]


def test_validate_links_ignores_external(tmp_path: Path):
    init_codewiki(tmp_path)
    wiki_dir = tmp_path / ".codewiki" / "wiki"
    (wiki_dir / "test.md").write_text("# Test\n\nSee [example](https://example.com).")
    issues = validate_links(tmp_path)
    assert len(issues) == 0


def test_validate_links_valid_internal(tmp_path: Path):
    init_codewiki(tmp_path)
    wiki_dir = tmp_path / ".codewiki" / "wiki"
    (wiki_dir / "a.md").write_text("# Page A\n\nSee [Page B](b.md).")
    (wiki_dir / "b.md").write_text("# Page B\n\nHello.")
    issues = validate_links(tmp_path)
    assert len(issues) == 0
