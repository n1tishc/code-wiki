# CodeWiki

AI-powered codebase wiki generator inspired by [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## Quick Start

```bash
pip install codewiki

# Initialize in your project
codewiki init

# Configure your LLM provider
codewiki config llm.provider --set anthropic
codewiki config llm.model --set claude-sonnet-4-5-20250929

# Ingest a codebase
codewiki ingest /path/to/repo

# Ask questions
codewiki query "How does authentication work?"

# Update after code changes
codewiki evolve

# Check wiki health
codewiki lint

# Auto-evolve on git changes
codewiki watch
```

## Supported LLM Providers

- **Anthropic** (Claude) — `anthropic/claude-sonnet-4-5-20250929`
- **OpenAI** — `openai/gpt-4o`
- **Ollama** (local) — `ollama/llama3`
- Any provider supported by [litellm](https://docs.litellm.ai/)
