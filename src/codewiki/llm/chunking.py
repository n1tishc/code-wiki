"""Token-aware text chunking for LLM context windows."""

from __future__ import annotations

import tiktoken

from codewiki.constants import DEFAULT_CHUNK_TOKEN_LIMIT

# Use cl100k_base as a reasonable approximation across providers
_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Estimate the token count for a piece of text."""
    return len(_ENCODING.encode(text))


def chunk_text(
    text: str,
    max_tokens: int = DEFAULT_CHUNK_TOKEN_LIMIT,
    overlap_lines: int = 5,
) -> list[str]:
    """Split text into chunks that fit within a token limit.

    Tries to split on blank lines (logical boundaries) first,
    then falls back to line-count splitting.
    """
    if count_tokens(text) <= max_tokens:
        return [text]

    lines = text.split("\n")
    chunks: list[str] = []
    current_lines: list[str] = []
    current_tokens = 0

    for line in lines:
        line_tokens = count_tokens(line)
        if current_tokens + line_tokens > max_tokens and current_lines:
            chunks.append("\n".join(current_lines))
            # Keep overlap for context continuity
            overlap = current_lines[-overlap_lines:] if overlap_lines else []
            current_lines = list(overlap)
            current_tokens = count_tokens("\n".join(current_lines))
        current_lines.append(line)
        current_tokens += line_tokens

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks
