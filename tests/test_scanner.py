"""Tests for codebase scanner."""

from pathlib import Path

from codewiki.config import ScannerConfig
from codewiki.core.scanner import detect_language, scan_codebase


def test_detect_language():
    assert detect_language(Path("foo.py")) == "Python"
    assert detect_language(Path("bar.js")) == "JavaScript"
    assert detect_language(Path("baz.rs")) == "Rust"
    assert detect_language(Path("qux.go")) == "Go"


def test_scan_basic(sample_repo: Path):
    config = ScannerConfig()
    files = scan_codebase(sample_repo, config)
    paths = [f.relative_path for f in files]

    assert "README.md" in paths
    assert "main.py" in paths
    assert "myrepo/core.py" in paths
    assert "myrepo/utils.py" in paths


def test_scan_respects_gitignore(sample_repo: Path):
    # Create a __pycache__ dir that should be ignored
    cache = sample_repo / "myrepo" / "__pycache__"
    cache.mkdir()
    (cache / "core.cpython-310.pyc").write_bytes(b"\x00\x00")

    config = ScannerConfig()
    files = scan_codebase(sample_repo, config)
    paths = [f.relative_path for f in files]

    assert not any("__pycache__" in p for p in paths)


def test_scan_skips_binary(sample_repo: Path):
    (sample_repo / "binary.dat").write_bytes(b"\x00\x01\x02\x03")
    config = ScannerConfig(include=["**/*"])
    files = scan_codebase(sample_repo, config)
    paths = [f.relative_path for f in files]

    assert "binary.dat" not in paths


def test_scan_priority_ordering(sample_repo: Path):
    config = ScannerConfig()
    files = scan_codebase(sample_repo, config)

    # README should be first (priority 0)
    assert files[0].relative_path == "README.md"
    # main.py should be before regular source files
    main_idx = next(i for i, f in enumerate(files) if f.relative_path == "main.py")
    core_idx = next(i for i, f in enumerate(files) if f.relative_path == "myrepo/core.py")
    assert main_idx < core_idx


def test_scan_max_file_size(sample_repo: Path):
    # Create a large file
    big = sample_repo / "big.py"
    big.write_text("x = 1\n" * 100000)

    config = ScannerConfig(max_file_size_kb=1)  # 1KB limit
    files = scan_codebase(sample_repo, config)
    paths = [f.relative_path for f in files]

    assert "big.py" not in paths
