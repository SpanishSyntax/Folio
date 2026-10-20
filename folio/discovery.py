"""Workspace discovery, document resolution, and status dashboard panel for Folio."""

from __future__ import annotations

import sys
from pathlib import Path

from folio import __version__
from folio.config import check_toolchain
from folio.frontmatter import normalize_mode
from folio.ui import ui


def discover_workspace_documents(directory: Path | str = ".") -> list[Path]:
    """Finds all non-internal document files (.md, .typ, .tex) in the directory."""
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return []

    doc_files = (
        sorted(list(dir_path.glob("*.md")))
        + sorted(list(dir_path.glob("*.typ")))
        + sorted(list(dir_path.glob("*.tex")))
    )
    return [
        f
        for f in doc_files
        if not f.name.startswith(("_body", "_entry", "_folio"))
        and f.name not in ("README.md", "LICENSE.md", "CONTRIBUTING.md")
    ]


def find_target_file(arg_path: str | None, base_dir: Path | str = ".") -> Path:
    """Discovers target document (.md, .typ, .tex) or prompts interactively."""
    base = Path(base_dir)
    if arg_path:
        target = base / arg_path if not Path(arg_path).is_absolute() else Path(arg_path)
        if not target.exists():
            ui.error(f"File '{arg_path}' not found.")
            sys.exit(1)
        return target

    # Preferred standard starters
    for candidate in (
        "report.md",
        "input.md",
        "slides.md",
        "paper.md",
        "report.typ",
        "slides.typ",
        "paper.typ",
        "report.tex",
        "slides.tex",
        "paper.tex",
        "main.typ",
        "main.tex",
    ):
        cand_path = base / candidate
        if cand_path.exists():
            return cand_path

    doc_files = discover_workspace_documents(base)

    if len(doc_files) == 1:
        return doc_files[0]
    elif len(doc_files) > 1:
        if sys.stdin.isatty():
            options = []
            for f in doc_files:
                if f.suffix == ".md":
                    icon = "📄"
                elif f.suffix == ".typ":
                    icon = "❄️"
                else:
                    icon = "📜"
                options.append(
                    (str(f), f"{icon} {f.name}", f"{f.stat().st_size:,} bytes")
                )
            chosen = ui.select("Multiple documents found. Select one to compile:", options)
            return Path(chosen)
        names = ", ".join(f.name for f in doc_files)
        ui.error(f"Multiple documents found ({names}). Specify one: folio <file>")
        sys.exit(1)

    ui.error(
        "No document found. Scaffold one with 'flaker init folio' or 'flaker new folio'."
    )
    sys.exit(1)


def resolve_typst_template(
    mode: str, custom_template: str | None, base_dir: Path | str = "."
) -> tuple[Path, str]:
    """Resolves the local Typst template and entry function name for the given mode.

    Returns (template_path, entry_func_name).
    """
    mode = normalize_mode(mode)
    entry_funcs = {
        "report": "report",
        "slides": "slides",
        "paper": "paper",
    }
    entry_func = entry_funcs[mode]
    base = Path(base_dir)

    if custom_template:
        t_path = Path(custom_template)
        if not t_path.is_absolute():
            t_path = base / t_path
        if not t_path.exists():
            ui.error(f"Custom template '{custom_template}' not found.")
            sys.exit(1)
        return t_path, entry_func

    local_candidates = {
        "report": ["report.typ", "template.typ"],
        "slides": ["slides.typ", "presentation.typ", "template.typ"],
        "paper": ["paper.typ", "ieee.typ", "template.typ"],
    }

    expected_name = {
        "report": "report.typ",
        "slides": "slides.typ",
        "paper": "paper.typ",
    }[mode]

    for cand in local_candidates[mode]:
        cand_path = base / cand
        if cand_path.exists():
            return cand_path, entry_func

    ui.error(
        f"Template '{expected_name}' not found in workspace.\n"
        f"  Run '{ui.bold('flaker project folio')}' to scaffold templates, or specify --template <path>."
    )
    sys.exit(1)


def print_status_dashboard(base_dir: Path | str = ".") -> list[Path]:
    """Renders the standard SpanishSyntax bounding box panel for Folio.

    Returns list of discovered workspace documents.
    """
    base = Path(base_dir).resolve()
    docs = discover_workspace_documents(base)
    toolchain = check_toolchain()

    # Toolchain status badges
    tc_badges: list[str] = []
    for tool, info in toolchain.items():
        if info["installed"]:
            v_short = (info["version"] or "").split()[1] if info["version"] and len(info["version"].split()) > 1 else "ok"
            tc_badges.append(f"{ui.bold_green('✔')} {tool}({v_short})")
        else:
            tc_badges.append(f"{ui.dim('✘ ' + tool)}")

    # Templates in workspace
    tpl_found = [
        f.name
        for f in (
            base / "report.typ",
            base / "slides.typ",
            base / "paper.typ",
            base / "template.typ",
            base / "ieee.typ",
        )
        if f.exists()
    ]
    tpl_str = ", ".join(tpl_found) if tpl_found else ui.dim("none (use flaker project folio)")

    # Docs summary
    if docs:
        doc_names = ", ".join(f"{d.name} ({d.stat().st_size:,}B)" for d in docs[:3])
        if len(docs) > 3:
            doc_names += f" and {len(docs) - 3} more"
        docs_display = doc_names
    else:
        docs_display = ui.dim("no documents found in workspace")

    lines = [
        f"{ui.bold('Folio Version:')}     {ui.bold_cyan(f'v{__version__}')} (Engines: Typst, Tectonic/LaTeX, Pandoc)",
        f"{ui.bold('Active Workspace:')}  {base}",
        f"{ui.bold('Backend Tools:')}     {'  '.join(tc_badges)}",
        f"{ui.bold('Found Templates:')}   {tpl_str}",
        f"{ui.bold('Target Documents:')}  {docs_display}",
    ]

    ui.panel("FOLIO DOCUMENT & PRESENTATION COMPILER", lines)
    return docs
