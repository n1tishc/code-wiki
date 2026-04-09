"""Tests for the query system."""

from pathlib import Path

from codewiki.config import CodeWikiConfig, init_codewiki
from codewiki.core.query import _score_page, _tokenize


def test_tokenize():
    tokens = _tokenize("How does the authentication module work?")
    assert "authentication" in tokens
    assert "module" in tokens
    assert "work" in tokens
    assert "how" not in tokens  # stop word
    assert "does" not in tokens  # stop word
    assert "the" not in tokens  # stop word


def test_score_page():
    query_tokens = _tokenize("authentication module")
    score = _score_page(
        query_tokens,
        title="Authentication Module",
        content="# Authentication Module\n\nThis module handles user auth.\n\nSome body text about login.",
    )
    # Title match (3) + heading match (2) for both tokens
    assert score > 0


def test_score_page_no_match():
    query_tokens = _tokenize("database migrations")
    score = _score_page(
        query_tokens,
        title="Authentication Module",
        content="# Auth\n\nHandles login.",
    )
    assert score == 0.0
