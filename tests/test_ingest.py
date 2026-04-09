"""Tests for the ingest pipeline."""

from pathlib import Path

from codewiki.config import CodeWikiConfig, init_codewiki
from codewiki.core.ingest import run_ingest


def test_ingest_creates_wiki_pages(tmp_path: Path, sample_repo: Path, mock_llm):
    init_codewiki(tmp_path)
    config = CodeWikiConfig()

    run_ingest(sample_repo, config, base_path=tmp_path)

    wiki_dir = tmp_path / ".codewiki" / "wiki"
    assert (wiki_dir / "architecture.md").exists()
    assert (wiki_dir / "dependencies.md").exists()
    assert (wiki_dir / "onboarding.md").exists()
    assert (wiki_dir / "patterns" / "overview.md").exists()
    assert (wiki_dir / "decisions" / "initial.md").exists()
    assert (wiki_dir / "index.md").exists()

    # Check modules were created
    module_files = list((wiki_dir / "modules").glob("*.md"))
    assert len(module_files) > 0

    # Check log was updated
    log_content = (wiki_dir / "log.md").read_text()
    assert "ingest" in log_content


def test_ingest_updates_config_state(tmp_path: Path, sample_repo: Path, mock_llm):
    init_codewiki(tmp_path)
    config = CodeWikiConfig()

    run_ingest(sample_repo, config, base_path=tmp_path)

    from codewiki.config import load_config
    loaded = load_config(tmp_path)
    assert loaded.state.target_path == str(sample_repo.resolve())
    assert loaded.state.last_ingest_at is not None
