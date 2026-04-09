"""Wiki search and LLM-powered Q&A."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

from codewiki.config import CodeWikiConfig
from codewiki.llm.client import LLMClient
from codewiki.llm.prompts import PromptRegistry
from codewiki.wiki.manager import WikiManager

console = Console()

# Common English stop words to ignore in keyword matching
STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "of", "to", "and", "or",
    "for", "with", "this", "that", "are", "was", "be", "has", "have",
    "do", "does", "how", "what", "where", "when", "why", "who", "which",
}


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase keywords, excluding stop words."""
    words = re.findall(r"\b\w+\b", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def _score_page(query_tokens: list[str], title: str, content: str) -> float:
    """Score a page's relevance to a query. Higher = more relevant."""
    title_tokens = set(_tokenize(title))
    heading_tokens: set[str] = set()
    body_tokens: set[str] = set()

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            heading_tokens.update(_tokenize(stripped))
        else:
            body_tokens.update(_tokenize(stripped))

    score = 0.0
    for token in query_tokens:
        if token in title_tokens:
            score += 3.0
        if token in heading_tokens:
            score += 2.0
        if token in body_tokens:
            score += 1.0

    return score


def run_query(
    question: str,
    config: CodeWikiConfig,
    base_path: Path | None = None,
    verbose: bool = False,
) -> None:
    """Search the wiki and answer a question using LLM."""
    manager = WikiManager(base_path, config)
    pages = manager.list_pages()

    if not pages:
        console.print("[yellow]Wiki is empty.[/yellow] Run `codewiki ingest` first.")
        return

    # Filter out internal pages
    query_pages = [p for p in pages if not p.relative_path.startswith("_")]

    # Rank pages by relevance
    query_tokens = _tokenize(question)
    scored: list[tuple[float, str, str, str]] = []

    for page in query_pages:
        result = manager.read_page(page.relative_path)
        if result is None:
            continue
        _, content = result
        score = _score_page(query_tokens, page.title, content)
        if score > 0:
            scored.append((score, page.relative_path, page.title, content))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top 5
    top_pages = scored[:5]

    if not top_pages:
        console.print("[yellow]No relevant wiki pages found for your question.[/yellow]")
        console.print("Try rephrasing or run `codewiki ingest` to update the wiki.")
        return

    if verbose:
        console.print("[dim]Consulting pages:[/dim]")
        for score, path, title, _ in top_pages:
            console.print(f"  [dim]{path}[/dim] (score: {score:.1f})")
        console.print()

    # Build context for LLM
    pages_text = "\n\n---\n\n".join(
        f"## [{title}]({path})\n\n{content}"
        for _, path, title, content in top_pages
    )

    client = LLMClient(config.llm)
    prompts = PromptRegistry(config.prompts or None)

    prompt = prompts.render("query_answer", question=question, pages=pages_text)
    system = (
        "You are a helpful assistant answering questions about a codebase "
        "using its wiki documentation. Be precise and cite your sources."
    )

    # Collect answer and render as Markdown
    answer = client.complete_streaming(system, prompt)
    console.print()
    console.print(Markdown(answer))
    console.print()
