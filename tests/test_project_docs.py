"""Tests for repository ADR and Attention Point hygiene."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = REPO_ROOT / "docs" / "adr"
ACTIVE_DOCS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "docs" / "artefakte.md",
    *sorted(ADR_DIR.glob("*.md")),
    *sorted((REPO_ROOT / "journal").glob("*.md")),
)


def test_agents_attention_points_have_no_numbers_or_tombstones() -> None:
    """Attention Points use titles, not numbers, and obsolete entries are removed."""
    text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert not re.search(r"^### AP-\d+", text, re.MULTILINE)
    assert "entfernt (" not in text
    assert "Involvierte ADRs" not in text
    assert "**Kontext**" not in text


def test_adr_numbers_are_contiguous() -> None:
    """The ADR directory contains a gapless 0001-0005 sequence."""
    numbers: list[int] = []
    for path in ADR_DIR.glob("*.md"):
        match = re.match(r"^(\d{4})-", path.name)
        if match is not None:
            numbers.append(int(match.group(1)))
    assert sorted(numbers) == list(range(1, 6))


def test_active_docs_do_not_reference_removed_adrs() -> None:
    """Removed ADRs are described in prose, not linked by their old numbers."""
    removed = re.compile(r"ADR-000[6-9]")
    for path in ACTIVE_DOCS:
        assert not removed.search(path.read_text(encoding="utf-8")), path.relative_to(REPO_ROOT)
