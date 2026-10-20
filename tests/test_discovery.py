"""Tests for document discovery, template resolution, and status dashboard."""

from pathlib import Path
import pytest
from folio.discovery import (
    discover_workspace_documents,
    find_target_file,
    resolve_typst_template,
    print_status_dashboard,
)


def test_discover_workspace_documents(tmp_path: Path):
    (tmp_path / "report.md").write_text("# Report", encoding="utf-8")
    (tmp_path / "slides.typ").write_text("// Slides", encoding="utf-8")
    (tmp_path / "paper.tex").write_text("% Paper", encoding="utf-8")
    (tmp_path / "_body.typ").write_text("// Internal", encoding="utf-8")
    (tmp_path / "_entry.tex").write_text("% Internal", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Readme", encoding="utf-8")

    docs = discover_workspace_documents(tmp_path)
    names = [d.name for d in docs]
    assert "report.md" in names
    assert "slides.typ" in names
    assert "paper.tex" in names
    assert "_body.typ" not in names
    assert "_entry.tex" not in names
    assert "README.md" not in names


def test_find_target_file_explicit(tmp_path: Path):
    doc = tmp_path / "custom.md"
    doc.write_text("# Test", encoding="utf-8")
    found = find_target_file(str(doc), base_dir=tmp_path)
    assert found == doc


def test_find_target_file_standard_order(tmp_path: Path):
    (tmp_path / "paper.md").write_text("# Paper", encoding="utf-8")
    (tmp_path / "report.md").write_text("# Report", encoding="utf-8")
    found = find_target_file(None, base_dir=tmp_path)
    # report.md has higher precedence than paper.md
    assert found.name == "report.md"


def test_resolve_typst_template(tmp_path: Path):
    tpl = tmp_path / "report.typ"
    tpl.write_text("// Report Template", encoding="utf-8")
    path, func = resolve_typst_template("report", None, base_dir=tmp_path)
    assert path.name == "report.typ"
    assert func == "report"


def test_print_status_dashboard(tmp_path: Path, capsys):
    (tmp_path / "input.md").write_text("# Document", encoding="utf-8")
    docs = print_status_dashboard(tmp_path)
    assert len(docs) == 1
    captured = capsys.readouterr()
    assert "FOLIO DOCUMENT & PRESENTATION COMPILER" in captured.out
    assert "input.md" in captured.out
