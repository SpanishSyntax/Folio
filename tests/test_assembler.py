"""Tests for chapter assembler and natural ordering."""

from pathlib import Path
from folio.assembler import natural_sort_key, assemble_documents


def test_natural_sort_key():
    files = [Path(f) for f in ["ch10.md", "ch1.md", "ch2.md", "ch20.md"]]
    sorted_files = sorted(files, key=natural_sort_key)
    assert [f.name for f in sorted_files] == ["ch1.md", "ch2.md", "ch10.md", "ch20.md"]


def test_assemble_documents_report(tmp_path: Path):
    ch_dir = tmp_path / "chapters"
    ch_dir.mkdir()

    (ch_dir / "01_intro.md").write_text(
        "---\ntitle: Local Title\nauthor: Someone\n---\n# Chapter 1\nIntro text.\n",
        encoding="utf-8",
    )
    (ch_dir / "02_analysis.md").write_text(
        "# Chapter 2\nAnalysis text.\n",
        encoding="utf-8",
    )

    out_file = tmp_path / "custom_report.md"
    success = assemble_documents(
        chapters_dir="chapters",
        output_filename="custom_report.md",
        title="Master Title",
        subtitle="Reader",
        author="Lead Author",
        mode="report",
        base_dir=tmp_path,
    )

    assert success is True
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")

    assert 'title: "Master Title"' in content
    assert 'subtitle: "Reader"' in content
    assert 'author: "Lead Author"' in content
    assert 'mode: "report"' in content
    assert "Local Title" not in content
    assert "#pagebreak()" in content
    assert "Intro text." in content
    assert "Analysis text." in content


def test_assemble_documents_slides(tmp_path: Path):
    mod_dir = tmp_path / "modules"
    mod_dir.mkdir()

    (mod_dir / "slide1.md").write_text("# Slide 1 Content", encoding="utf-8")
    (mod_dir / "slide2.md").write_text("# Slide 2 Content", encoding="utf-8")

    out_file = tmp_path / "slides.md"
    success = assemble_documents(
        chapters_dir="modules",
        output_filename="slides.md",
        title="Keynote Deck",
        mode="slides",
        theme="dark",
        base_dir=tmp_path,
    )

    assert success is True
    content = out_file.read_text(encoding="utf-8")
    assert 'mode: "slides"' in content
    assert 'theme: "dark"' in content
    assert 'aspect-ratio: "16-9"' in content
    assert "\n\n---\n\n# Slide 2 Content" in content


def test_assemble_documents_missing_dir(tmp_path: Path):
    success = assemble_documents(
        chapters_dir="nonexistent_folder",
        base_dir=tmp_path,
    )
    assert success is False
