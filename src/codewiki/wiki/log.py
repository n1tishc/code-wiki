"""Append-only activity log for the wiki."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from codewiki.config import CodeWikiConfig, get_wiki_dir
from codewiki.constants import LOG_FILE


def append_log(
    action: str,
    details: str,
    base_path: Path | None = None,
    config: CodeWikiConfig | None = None,
) -> None:
    """Append an entry to the wiki activity log."""
    log_path = get_wiki_dir(base_path, config) / LOG_FILE
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"- **[{timestamp}]** `{action}` — {details}\n"

    if not log_path.exists():
        log_path.write_text(f"# CodeWiki Activity Log\n\n{entry}")
    else:
        with open(log_path, "a") as f:
            f.write(entry)
