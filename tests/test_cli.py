"""Tests for Folio CLI parsing and execution routing."""

from pathlib import Path
from folio import __version__
from folio.cli import main


def test_cli_version(capsys):
    ret = main(["--version"])
    assert ret == 0
    captured = capsys.readouterr()
    assert f"v{__version__}" in captured.out


def test_cli_help(capsys):
    ret = main(["--help"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Polyglot Document & Presentation Compiler" in captured.out
    assert "Operating Modes:" in captured.out


def test_cli_init(capsys):
    ret = main(["init"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "flaker init folio" in captured.out


def test_cli_assemble_dispatch(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ch = tmp_path / "chapters"
    ch.mkdir()
    (ch / "ch1.md").write_text("# Chapter 1", encoding="utf-8")

    ret = main(["assemble", "chapters", "-m", "report", "--title", "CLI Test"])
    assert ret == 0
    out_file = tmp_path / "report.md"
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert 'title: "CLI Test"' in content


def test_cli_dashboard_no_args(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ret = main([])
    assert ret == 0
    captured = capsys.readouterr()
    assert "FOLIO DOCUMENT & PRESENTATION COMPILER" in captured.out
