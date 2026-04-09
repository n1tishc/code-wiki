"""Git diff analysis, changed file detection, and commit history."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import git


@dataclass
class ChangedFile:
    path: str
    change_type: str  # "added", "modified", "deleted", "renamed"
    diff_text: str


class GitAnalyzer:
    """Analyzes git repository for changes."""

    def __init__(self, repo_path: Path):
        self.repo = git.Repo(repo_path)
        self.repo_path = repo_path

    def get_current_ref(self) -> str:
        """Get the current HEAD SHA."""
        return self.repo.head.commit.hexsha

    def get_changes_since(self, ref: str) -> list[ChangedFile]:
        """Get all files changed between a ref and HEAD."""
        try:
            old_commit = self.repo.commit(ref)
        except (git.BadName, ValueError):
            return []

        head_commit = self.repo.head.commit
        diffs = old_commit.diff(head_commit)
        changes: list[ChangedFile] = []

        for diff in diffs:
            if diff.new_file:
                change_type = "added"
                path = diff.b_path
            elif diff.deleted_file:
                change_type = "deleted"
                path = diff.a_path
            elif diff.renamed_file:
                change_type = "renamed"
                path = diff.b_path
            else:
                change_type = "modified"
                path = diff.b_path or diff.a_path

            try:
                diff_text = diff.diff.decode("utf-8", errors="replace") if diff.diff else ""
            except Exception:
                diff_text = ""

            changes.append(ChangedFile(
                path=path,
                change_type=change_type,
                diff_text=diff_text,
            ))

        return changes

    def get_commit_messages_since(self, ref: str) -> list[str]:
        """Get commit messages between a ref and HEAD."""
        try:
            commits = list(self.repo.iter_commits(f"{ref}..HEAD"))
        except git.GitCommandError:
            return []
        return [c.message.strip() for c in commits]

    def is_git_repo(self) -> bool:
        """Check if the path is a valid git repository."""
        try:
            _ = self.repo.head.commit
            return True
        except (ValueError, git.InvalidGitRepositoryError):
            return False
