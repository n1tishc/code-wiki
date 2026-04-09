"""Tests for the evolve pipeline."""

from pathlib import Path

import git

from codewiki.config import CodeWikiConfig, init_codewiki, save_config
from codewiki.git.analyzer import GitAnalyzer


def _make_git_repo(path: Path) -> git.Repo:
    """Initialize a git repo with an initial commit."""
    repo = git.Repo.init(path)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    # Create a file and commit
    (path / "hello.py").write_text("print('hello')\n")
    repo.index.add(["hello.py"])
    repo.index.commit("initial commit")
    return repo


def test_git_analyzer_current_ref(tmp_path: Path):
    repo = _make_git_repo(tmp_path)
    analyzer = GitAnalyzer(tmp_path)
    ref = analyzer.get_current_ref()
    assert len(ref) == 40  # SHA hex


def test_git_analyzer_changes_since(tmp_path: Path):
    repo = _make_git_repo(tmp_path)
    initial_ref = repo.head.commit.hexsha

    # Make a change
    (tmp_path / "hello.py").write_text("print('world')\n")
    repo.index.add(["hello.py"])
    repo.index.commit("update hello")

    analyzer = GitAnalyzer(tmp_path)
    changes = analyzer.get_changes_since(initial_ref)
    assert len(changes) == 1
    assert changes[0].path == "hello.py"
    assert changes[0].change_type == "modified"


def test_git_analyzer_added_file(tmp_path: Path):
    repo = _make_git_repo(tmp_path)
    initial_ref = repo.head.commit.hexsha

    (tmp_path / "new.py").write_text("x = 1\n")
    repo.index.add(["new.py"])
    repo.index.commit("add new file")

    analyzer = GitAnalyzer(tmp_path)
    changes = analyzer.get_changes_since(initial_ref)
    added = [c for c in changes if c.change_type == "added"]
    assert len(added) == 1
    assert added[0].path == "new.py"


def test_git_analyzer_deleted_file(tmp_path: Path):
    repo = _make_git_repo(tmp_path)
    initial_ref = repo.head.commit.hexsha

    (tmp_path / "hello.py").unlink()
    repo.index.remove(["hello.py"])
    repo.index.commit("delete hello")

    analyzer = GitAnalyzer(tmp_path)
    changes = analyzer.get_changes_since(initial_ref)
    deleted = [c for c in changes if c.change_type == "deleted"]
    assert len(deleted) == 1
    assert deleted[0].path == "hello.py"


def test_git_analyzer_commit_messages(tmp_path: Path):
    repo = _make_git_repo(tmp_path)
    initial_ref = repo.head.commit.hexsha

    (tmp_path / "hello.py").write_text("print('world')\n")
    repo.index.add(["hello.py"])
    repo.index.commit("update hello message")

    analyzer = GitAnalyzer(tmp_path)
    messages = analyzer.get_commit_messages_since(initial_ref)
    assert len(messages) == 1
    assert "update hello message" in messages[0]
