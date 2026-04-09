"""Prompt template registry with Jinja2 rendering."""

from __future__ import annotations

from typing import Any

from jinja2 import Template

from codewiki.constants import PROMPTS


class PromptRegistry:
    """Manages prompt templates for each workflow."""

    def __init__(self, overrides: dict[str, str] | None = None):
        self.templates: dict[str, str] = {**PROMPTS}
        if overrides:
            self.templates.update(overrides)

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Render a named template with the given variables."""
        if template_name not in self.templates:
            raise KeyError(f"Unknown prompt template: {template_name}")
        return Template(self.templates[template_name]).render(**kwargs)

    def list_templates(self) -> list[str]:
        """Return all available template names."""
        return sorted(self.templates.keys())
