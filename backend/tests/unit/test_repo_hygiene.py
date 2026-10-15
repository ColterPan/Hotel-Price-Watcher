"""Repository-wide text checks.

House style: no em dashes anywhere (docs, UI copy, comments, code). They read
as machine-written. Use a comma, colon, parentheses or a new sentence.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EM_DASH = chr(0x2014)  # written as a code point so this file passes its own check
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".ts",
    ".tsx",
    ".css",
    ".html",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".sql",
    ".example",
    ".txt",
}
SKIP_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "coverage",
}


def _text_files():
    # os.walk with pruning, so node_modules and .venv are never even listed.
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            path = Path(root) / name
            if path.suffix in TEXT_SUFFIXES or name in {"Dockerfile", ".env.example"}:
                yield path


def test_no_em_dashes_anywhere():
    offenders = []
    for path in _text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if EM_DASH in line:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{number}")
    assert offenders == [], "Em dashes found (house style):\n" + "\n".join(offenders)


def test_env_file_is_not_committed_alongside_example():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore.splitlines()
    assert (REPO_ROOT / ".env.example").exists()
