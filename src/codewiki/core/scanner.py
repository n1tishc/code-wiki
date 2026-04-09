"""Codebase file walking, filtering, and prioritization."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

import pathspec

from codewiki.config import ScannerConfig
from codewiki.constants import PRIORITY_FILENAMES


@dataclass
class FileInfo:
    path: Path
    relative_path: str
    language: str
    size_bytes: int
    priority: int  # Lower = higher priority


def detect_language(path: Path) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".tsx": "TypeScript (React)", ".jsx": "JavaScript (React)",
        ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
        ".c": "C", ".cpp": "C++", ".h": "C/C++ Header", ".hpp": "C++ Header",
        ".rb": "Ruby", ".php": "PHP", ".swift": "Swift", ".scala": "Scala",
        ".sh": "Shell", ".bash": "Bash",
        ".md": "Markdown", ".txt": "Text",
        ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".json": "JSON",
        ".sql": "SQL", ".html": "HTML", ".css": "CSS",
    }
    return ext_map.get(path.suffix.lower(), path.suffix.lstrip(".").upper() or "Unknown")


def _is_binary(path: Path) -> bool:
    """Check if a file is binary by reading its first 8KB."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except (OSError, PermissionError):
        return True


def _load_gitignore_spec(root: Path) -> pathspec.PathSpec | None:
    """Load .gitignore patterns from the root directory."""
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        return None
    with open(gitignore_path) as f:
        return pathspec.PathSpec.from_lines("gitignore", f)


def _file_priority(relative_path: str) -> int:
    """Assign priority to a file. Lower number = processed first."""
    filename = Path(relative_path).name
    if filename in PRIORITY_FILENAMES:
        # README-like files get highest priority
        if filename.lower().startswith("readme"):
            return 0
        # Entry points and config files
        return 1
    # Regular source files
    return 2


def scan_codebase(
    target: Path,
    config: ScannerConfig,
) -> list[FileInfo]:
    """Walk a codebase directory and return prioritized file list.

    Respects .gitignore, applies include/exclude patterns, skips binaries
    and oversized files.
    """
    target = target.resolve()
    include_spec = pathspec.PathSpec.from_lines("gitignore", config.include)
    exclude_spec = pathspec.PathSpec.from_lines("gitignore", config.exclude)
    gitignore_spec = _load_gitignore_spec(target) if config.respect_gitignore else None

    max_size = config.max_file_size_kb * 1024
    files: list[FileInfo] = []

    for path in target.rglob("*"):
        if not path.is_file():
            continue

        relative = str(path.relative_to(target))

        # Apply exclude patterns
        if exclude_spec.match_file(relative):
            continue

        # Apply gitignore
        if gitignore_spec and gitignore_spec.match_file(relative):
            continue

        # Apply include patterns
        if not include_spec.match_file(relative):
            continue

        # Skip oversized files
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > max_size:
            continue

        # Skip binary files
        if _is_binary(path):
            continue

        files.append(FileInfo(
            path=path,
            relative_path=relative,
            language=detect_language(path),
            size_bytes=size,
            priority=_file_priority(relative),
        ))

    # Sort by priority, then alphabetically
    files.sort(key=lambda f: (f.priority, f.relative_path))
    return files
