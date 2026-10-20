"""Tests for frontmatter parsing, mode normalization, and typst kwargs."""

from pathlib import Path
from folio.frontmatter import normalize_mode, parse_frontmatter, build_typst_kwargs


def test_normalize_mode():
    assert normalize_mode("report") == "report"
    assert normalize_mode("slides") == "slides"
    assert normalize_mode("presentation") == "slides"
    assert normalize_mode("deck") == "slides"
    assert normalize_mode("paper") == "paper"
    assert normalize_mode("ieee") == "paper"
    assert normalize_mode("academic") == "paper"
    assert normalize_mode("unknown") == "report"
    assert normalize_mode(None, "ieee") == "paper"
    assert normalize_mode(None, None) == "report"


def test_parse_frontmatter_standard(tmp_path: Path):
    doc = tmp_path / "test.md"
    doc.write_text(
        "---\n"
        "title: Robust Control\n"
        "author: SpanishSyntax\n"
        "date: 2026-10-20\n"
        "mode: report\n"
        "---\n"
        "# Introduction\n"
        "Body content.\n",
        encoding="utf-8",
    )
    fm = parse_frontmatter(doc)
    assert fm["title"] == "Robust Control"
    assert fm["author"] == "SpanishSyntax"
    assert fm["date"] == "2026-10-20"
    assert fm["mode"] == "report"


def test_parse_frontmatter_with_comments_and_quotes(tmp_path: Path):
    doc = tmp_path / "test_comments.md"
    doc.write_text(
        "---\n"
        'engine: "latex" # Options: typst | latex\n'
        'theme: dark # Color theme\n'
        'subtitle: "State-Space & Observers"\n'
        "# Full line comment\n"
        "---\n"
        "Content.\n",
        encoding="utf-8",
    )
    fm = parse_frontmatter(doc)
    assert fm["engine"] == "latex"
    assert fm["theme"] == "dark"
    assert fm["subtitle"] == "State-Space & Observers"


def test_parse_frontmatter_empty_or_none(tmp_path: Path):
    doc = tmp_path / "no_fm.md"
    doc.write_text("# Heading only\nNo frontmatter here.\n", encoding="utf-8")
    assert parse_frontmatter(doc) == {}


def test_build_typst_kwargs():
    fm = {
        "title": 'Control "Special" & Dynamics',
        "author": "Jane Doe",
        "has_notes": "true",
        "margin": "none",
        "mode": "report",  # should be skipped
        "bibliography": "custom.bib",
    }
    kwargs = build_typst_kwargs(fm, "doc.md")
    assert 'md-path: "doc.md"' in kwargs
    assert 'title: "Control \\"Special\\" & Dynamics"' in kwargs
    assert 'author: "Jane Doe"' in kwargs
    assert "has-notes: true" in kwargs
    assert "margin: none" in kwargs
    assert 'bibliography: bibliography("custom.bib")' in kwargs
    assert "mode:" not in kwargs


def test_build_typst_kwargs_paper_default_bib(tmp_path: Path):
    (tmp_path / "library.bib").write_text("@article{test}", encoding="utf-8")
    fm = {"title": "Paper Title"}
    kwargs = build_typst_kwargs(fm, "paper.md", compile_root=tmp_path, mode="paper")
    assert 'bibliography: bibliography("library.bib")' in kwargs
