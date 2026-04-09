"""Configuration management for CodeWiki."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from codewiki.constants import (
    CODEWIKI_DIR,
    CONFIG_FILE,
    DEFAULT_EXCLUDE_GLOBS,
    DEFAULT_INCLUDE_GLOBS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    MAX_FILE_SIZE_KB,
    WIKI_DIR,
    WIKI_SECTIONS,
)


@dataclass
class LLMConfig:
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"
    api_key: str | None = None
    api_base: str | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE


@dataclass
class ScannerConfig:
    include: list[str] = field(default_factory=lambda: list(DEFAULT_INCLUDE_GLOBS))
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE_GLOBS))
    max_file_size_kb: int = MAX_FILE_SIZE_KB
    respect_gitignore: bool = True


@dataclass
class WikiConfig:
    path: str = WIKI_DIR
    sections: list[str] = field(default_factory=lambda: list(WIKI_SECTIONS))
    obsidian_vault: str | None = None


@dataclass
class EvolveConfig:
    debounce_seconds: int = 5
    auto_update_architecture: bool = True


@dataclass
class StateConfig:
    last_evolve_ref: str | None = None
    last_ingest_at: str | None = None
    target_path: str | None = None


@dataclass
class CodeWikiConfig:
    schema_version: int = 1
    llm: LLMConfig = field(default_factory=LLMConfig)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    wiki: WikiConfig = field(default_factory=WikiConfig)
    evolve: EvolveConfig = field(default_factory=EvolveConfig)
    prompts: dict[str, str] = field(default_factory=dict)
    state: StateConfig = field(default_factory=StateConfig)

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to a dict suitable for YAML output."""
        def _asdict(obj: Any) -> Any:
            if hasattr(obj, "__dataclass_fields__"):
                return {k: _asdict(v) for k, v in obj.__dict__.items()}
            if isinstance(obj, list):
                return [_asdict(i) for i in obj]
            return obj
        return _asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeWikiConfig:
        """Deserialize config from a dict (loaded from YAML)."""
        cfg = cls()
        if "schema_version" in data:
            cfg.schema_version = data["schema_version"]
        if "llm" in data:
            cfg.llm = LLMConfig(**{k: v for k, v in data["llm"].items()
                                   if k in LLMConfig.__dataclass_fields__})
        if "scanner" in data:
            cfg.scanner = ScannerConfig(**{k: v for k, v in data["scanner"].items()
                                           if k in ScannerConfig.__dataclass_fields__})
        if "wiki" in data:
            cfg.wiki = WikiConfig(**{k: v for k, v in data["wiki"].items()
                                     if k in WikiConfig.__dataclass_fields__})
        if "evolve" in data:
            cfg.evolve = EvolveConfig(**{k: v for k, v in data["evolve"].items()
                                         if k in EvolveConfig.__dataclass_fields__})
        if "prompts" in data and isinstance(data["prompts"], dict):
            cfg.prompts = data["prompts"]
        if "state" in data:
            cfg.state = StateConfig(**{k: v for k, v in data["state"].items()
                                       if k in StateConfig.__dataclass_fields__})
        return cfg


def get_codewiki_dir(base_path: Path | None = None) -> Path:
    """Get the .codewiki directory path."""
    base = base_path or Path.cwd()
    return base / CODEWIKI_DIR


def get_config_path(base_path: Path | None = None) -> Path:
    """Get the config.yaml file path."""
    return get_codewiki_dir(base_path) / CONFIG_FILE


def get_wiki_dir(base_path: Path | None = None, config: "CodeWikiConfig | None" = None) -> Path:
    """Get the wiki output directory path."""
    if config and config.wiki.obsidian_vault:
        return Path(config.wiki.obsidian_vault).expanduser().resolve()
    cw_dir = get_codewiki_dir(base_path)
    return cw_dir / WIKI_DIR


def load_config(base_path: Path | None = None) -> CodeWikiConfig:
    """Load config from disk, or return defaults if not found."""
    config_path = get_config_path(base_path)
    if not config_path.exists():
        return CodeWikiConfig()
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    return CodeWikiConfig.from_dict(data)


def save_config(config: CodeWikiConfig, base_path: Path | None = None) -> None:
    """Save config to disk."""
    config_path = get_config_path(base_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)


def init_codewiki(base_path: Path | None = None, obsidian_vault: str | None = None) -> Path:
    """Initialize a .codewiki directory with default config and wiki structure."""
    base = base_path or Path.cwd()
    cw_dir = get_codewiki_dir(base)

    if cw_dir.exists():
        return cw_dir

    cw_dir.mkdir(parents=True, exist_ok=True)

    config = CodeWikiConfig()
    if obsidian_vault:
        config.wiki.obsidian_vault = obsidian_vault
        wiki_dir = Path(obsidian_vault).expanduser().resolve()
    else:
        wiki_dir = cw_dir / WIKI_DIR

    wiki_dir.mkdir(parents=True, exist_ok=True)
    for section in WIKI_SECTIONS:
        (wiki_dir / section).mkdir(exist_ok=True)

    save_config(config, base)

    # Create empty index and log
    (wiki_dir / "index.md").write_text("# CodeWiki Index\n\n_No pages yet. Run `codewiki ingest` to populate._\n")
    (wiki_dir / "log.md").write_text("# CodeWiki Activity Log\n\n")

    return cw_dir
