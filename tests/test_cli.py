"""Tests for CLI commands."""

from pathlib import Path

from typer.testing import CliRunner

from codewiki.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "codewiki v" in result.stdout


def test_init(tmp_path: Path):
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".codewiki").exists()
    assert (tmp_path / ".codewiki" / "config.yaml").exists()
    assert (tmp_path / ".codewiki" / "wiki" / "index.md").exists()
    assert (tmp_path / ".codewiki" / "wiki" / "log.md").exists()


def test_init_already_exists(tmp_path: Path):
    runner.invoke(app, ["init", str(tmp_path)])
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "already initialized" in result.stdout


def test_config_show(tmp_path: Path):
    runner.invoke(app, ["init", str(tmp_path)])
    result = runner.invoke(app, ["config", "--base", str(tmp_path)])
    assert result.exit_code == 0
    assert "llm" in result.stdout
    assert "scanner" in result.stdout


def test_config_get(tmp_path: Path):
    runner.invoke(app, ["init", str(tmp_path)])
    result = runner.invoke(app, ["config", "llm.provider", "--base", str(tmp_path)])
    assert result.exit_code == 0
    assert "anthropic" in result.stdout


def test_config_set(tmp_path: Path):
    runner.invoke(app, ["init", str(tmp_path)])
    result = runner.invoke(app, ["config", "llm.provider", "--set", "openai", "--base", str(tmp_path)])
    assert result.exit_code == 0
    assert "openai" in result.stdout

    # Verify it persisted
    result = runner.invoke(app, ["config", "llm.provider", "--base", str(tmp_path)])
    assert "openai" in result.stdout


def test_ingest_no_init(tmp_path: Path):
    result = runner.invoke(app, ["ingest", str(tmp_path)])
    assert result.exit_code == 1


def test_query_no_init(tmp_path: Path):
    result = runner.invoke(app, ["query", "test", "--base", str(tmp_path)])
    assert result.exit_code == 1
