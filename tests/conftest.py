"""Shared test fixtures."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from codewiki.config import CodeWikiConfig, init_codewiki


@pytest.fixture
def tmp_codewiki(tmp_path: Path) -> Path:
    """Create a temporary directory with .codewiki initialized."""
    init_codewiki(tmp_path)
    return tmp_path


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a small sample repo with a few Python files."""
    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()

    # README
    (repo_dir / "README.md").write_text("# My Repo\nA sample project for testing.\n")

    # Main entry point
    (repo_dir / "main.py").write_text(
        'from myrepo.core import process\n\ndef main():\n    result = process("hello")\n    print(result)\n\nif __name__ == "__main__":\n    main()\n'
    )

    # Package
    pkg = repo_dir / "myrepo"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text(
        'from myrepo.utils import clean\n\ndef process(data: str) -> str:\n    """Process input data."""\n    return clean(data).upper()\n'
    )
    (pkg / "utils.py").write_text(
        'def clean(text: str) -> str:\n    """Clean input text."""\n    return text.strip().lower()\n'
    )

    # requirements.txt
    (repo_dir / "requirements.txt").write_text("click>=8.0\nrich>=13.0\n")

    # .gitignore
    (repo_dir / ".gitignore").write_text("__pycache__/\n*.pyc\n")

    return repo_dir


@pytest.fixture
def mock_llm(monkeypatch):
    """Mock the LLMClient.complete method to return deterministic responses."""
    responses = {
        "file_summary": "- **Purpose**: Test file\n- **Key Exports**: test_func\n- **Dependencies**: None\n- **Patterns**: Simple function\n- **Complexity**: Low",
        "architecture": "# Architecture Overview\n\n## System Overview\nA simple test project.\n\n## Components\n- core: Main logic\n- utils: Helpers",
        "module_page": "# Module: test\n\n## Purpose\nTest module.\n\n## Key Components\n- test_func: does testing",
        "patterns": "# Patterns Overview\n\n## Simple Functions\nMost code uses simple standalone functions.",
        "decisions": "# Architectural Decisions\n\n## Decision 1: Keep it Simple\nThe codebase uses simple functions.",
        "dependencies": "# Dependencies\n\n## External\n- click\n- rich",
        "onboarding": "# Onboarding Guide\n\n## Getting Started\nRun main.py to start.",
        "query_answer": "Based on the wiki, the answer is: this is a test project.",
        "evolve_update": "# Updated Page\n\nThis page has been updated.",
    }

    def mock_complete(self, system_prompt, user_prompt, **kwargs):
        # Return response based on which prompt template keywords are found
        for key, response in responses.items():
            if key in user_prompt.lower() or key.replace("_", " ") in user_prompt.lower():
                return response
        return "# Generated Content\n\nGeneric LLM response."

    def mock_complete_streaming(self, system_prompt, user_prompt, callback=None):
        result = mock_complete(self, system_prompt, user_prompt)
        if callback:
            callback(result)
        return result

    from codewiki.llm.client import LLMClient
    monkeypatch.setattr(LLMClient, "complete", mock_complete)
    monkeypatch.setattr(LLMClient, "complete_streaming", mock_complete_streaming)
