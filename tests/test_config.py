"""Tests for configuration management."""

from pathlib import Path

from codewiki.config import (
    CodeWikiConfig,
    LLMConfig,
    init_codewiki,
    load_config,
    save_config,
)


def test_default_config():
    cfg = CodeWikiConfig()
    assert cfg.schema_version == 1
    assert cfg.llm.provider == "anthropic"
    assert cfg.llm.temperature == 0.2
    assert len(cfg.scanner.include) > 0
    assert len(cfg.scanner.exclude) > 0


def test_save_and_load(tmp_path: Path):
    cfg = CodeWikiConfig()
    cfg.llm.provider = "openai"
    cfg.llm.model = "gpt-4o"
    save_config(cfg, tmp_path)

    loaded = load_config(tmp_path)
    assert loaded.llm.provider == "openai"
    assert loaded.llm.model == "gpt-4o"
    assert loaded.scanner.respect_gitignore is True


def test_roundtrip_preserves_all_fields(tmp_path: Path):
    cfg = CodeWikiConfig()
    cfg.state.target_path = "/some/path"
    cfg.prompts = {"file_summary": "custom prompt"}
    save_config(cfg, tmp_path)

    loaded = load_config(tmp_path)
    assert loaded.state.target_path == "/some/path"
    assert loaded.prompts["file_summary"] == "custom prompt"


def test_from_dict_ignores_unknown_fields():
    data = {"llm": {"provider": "openai", "unknown_field": "value"}}
    cfg = CodeWikiConfig.from_dict(data)
    assert cfg.llm.provider == "openai"


def test_init_creates_structure(tmp_path: Path):
    cw_dir = init_codewiki(tmp_path)
    assert cw_dir.exists()
    assert (cw_dir / "config.yaml").exists()
    assert (cw_dir / "wiki").is_dir()
    assert (cw_dir / "wiki" / "modules").is_dir()
    assert (cw_dir / "wiki" / "patterns").is_dir()
    assert (cw_dir / "wiki" / "decisions").is_dir()
    assert (cw_dir / "wiki" / "index.md").exists()
    assert (cw_dir / "wiki" / "log.md").exists()
