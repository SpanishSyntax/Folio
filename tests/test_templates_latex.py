"""Tests for LaTeX and Beamer preambles and templates."""

from pathlib import Path
from folio.templates_latex import (
    tex_safe,
    get_doc_class,
    get_beamer_theme,
    build_latex_entry_document,
)


def test_tex_safe():
    assert tex_safe("A & B") == r"A \& B"
    assert tex_safe(r"Already \& Escaped") == r"Already \& Escaped"
    assert tex_safe(None) == ""
    assert tex_safe("Simple text") == "Simple text"


def test_get_doc_class():
    assert "IEEEtran" in get_doc_class("paper")
    assert "beamer" in get_doc_class("slides")
    assert "report" in get_doc_class("report")


def test_get_beamer_theme():
    light = get_beamer_theme("light")
    assert "FBFBFD" in light
    assert "usetheme{default}" in light

    dark = get_beamer_theme("dark")
    assert "000000" in dark
    assert "cardbg}{HTML}{161618}" in dark


def test_build_latex_entry_document_paper(tmp_path: Path):
    fm = {
        "title": "Observer Design & Verification",
        "author": "Dr. Smith",
        "dependency": "TU Delft",
        "email": "smith@tudelft.nl",
        "abstract": "This is the paper abstract.",
        "keywords": "Control, Estimation",
    }
    entry = build_latex_entry_document(fm, "paper", "body.tex", tmp_path)
    assert r"\documentclass[10pt, journal, compsoc]{IEEEtran}" in entry
    assert r"\title{Observer Design \& Verification}" in entry
    assert r"The author is with the TU Delft (e-mail: smith@tudelft.nl)" in entry
    assert r"\begin{abstract}" in entry
    assert r"\begin{IEEEkeywords}" in entry
    assert r"\input{body.tex}" in entry


def test_build_latex_entry_document_slides(tmp_path: Path):
    fm = {
        "title": "Weekly Standup",
        "author": "Alice",
        "theme": "dark",
    }
    entry = build_latex_entry_document(fm, "slides", "body.tex", tmp_path)
    assert r"\documentclass[aspectratio=169, 11pt]{beamer}" in entry
    assert r"\titlepage" in entry
    assert r"\input{body.tex}" in entry
