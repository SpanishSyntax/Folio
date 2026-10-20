"""CLI router, argument parser, and interactive status dashboard for Folio."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

from folio import __version__
from folio.assembler import assemble_documents, natural_sort_key
from folio.compiler import (
    _linux_set_pdeathsig,
    build_pdf,
    compile_markdown_latex,
    compile_markdown_typst,
    compile_tectonic,
    compile_typst_direct,
)
from folio.config import check_toolchain, load_user_config
from folio.discovery import (
    discover_workspace_documents,
    find_target_file,
    print_status_dashboard,
    resolve_typst_template,
)
from folio.frontmatter import build_typst_kwargs, normalize_mode, parse_frontmatter
from folio.templates_latex import tex_safe
from folio.ui import handle_color_args, ui
from folio.watcher import watch_pdf

__all__ = [
    "main",
    "build_pdf",
    "assemble_documents",
    "watch_pdf",
    "find_target_file",
    "resolve_typst_template",
    "parse_frontmatter",
    "build_typst_kwargs",
    "normalize_mode",
    "compile_tectonic",
    "compile_typst_direct",
    "compile_markdown_latex",
    "compile_markdown_typst",
    "print_status_dashboard",
    "load_user_config",
    "tex_safe",
    "natural_sort_key",
    "check_toolchain",
    "discover_workspace_documents",
    "_linux_set_pdeathsig",
]

USAGE = f"""{ui.badge()} {ui.bold("Polyglot Document & Presentation Compiler (Typst + LaTeX)")}

{ui.blue("Usage:")}
  folio                              Open interactive dashboard & quick compiler
  folio [file] [options]             Build PDF from Markdown, Typst, or LaTeX
  folio build [file] [options]       Explicit build command
  folio assemble [dir] [options]     Assemble modular chapters into master Markdown

{ui.blue("Operating Modes:")}
  -m, --mode MODE        Document operating mode:
                         • {ui.bold("report")}: Minimal sans-serif document (default, A4/Letter)
                         • {ui.bold("slides")}: 16:9 widescreen presentation (1920x1080)
                         • {ui.bold("paper")}:  Academic paper (IEEE 2-column layout)
  -p, --preset PRESET    Layout preset (e.g., 'ieee', 'default')

{ui.blue("Options:")}
  -o, --output PATH      Specify output PDF filename
  -t, --template PATH    Use custom Typst template file
  -w, --watch            Watch mode: recompile automatically on file changes
  --engine ENGINE        Compiler engine: 'typst' (default) or 'tectonic'
  --root PATH            Typst compilation root directory (default: current directory)
  --font-path PATH       Additional directory containing fonts for Typst
  --open                 Open generated PDF in system viewer after build
  --color MODE           Color output mode: auto, always, never (default: auto)
  --no-color             Disable colored output
  -h, --help             Show this help message and exit
  -V, -v, --version      Show version information and exit

{ui.blue("Scaffolding Note:")}
  Workspace scaffolding and templates are managed by {ui.bold("flaker")}:
  • flaker init folio     # Bootstrap DevShell + template.typ, slides.typ, ieee.typ
  • flaker project folio  # Drop template foundations into current workspace
  • flaker new folio      # Drop starter documents (report.md, slides.md, paper.md)

{ui.blue("Examples:")}
  folio                              # Interactive telemetry & documents dashboard
  folio report.md                    # Compile report.md -> report.pdf (using template.typ)
  folio assemble chapters            # Assemble chapters/*.md -> report.md (with pagebreaks)
  folio assemble modules -m slides   # Assemble modules/*.md -> slides.md
  folio deck.md -m slides -w         # Live watch 16:9 presentation (using slides.typ)
  folio paper.md -m paper            # Compile IEEE 2-column paper (using ieee.typ)
  folio main.typ -w                  # Direct Typst compilation with live reload
  folio main.tex                     # Direct LaTeX compilation via Tectonic
"""


def _print_init_info() -> None:
    ui.info(
        "Scaffolding is handled by Flaker. Run:\n"
        f"  • {ui.bold('flaker init folio')}     # Bootstrap DevShell + report.typ, slides.typ, paper.typ\n"
        f"  • {ui.bold('flaker project folio')}  # Scaffold template files into current directory\n"
        f"  • {ui.bold('flaker new folio')}      # Drop starter documents (report.md, slides.md, paper.md)",
        symbol="❄️ ",
    )


def run_interactive_hub(docs: list[Path], user_cfg: dict[str, Any]) -> int:
    """Provides interactive quick actions when Folio is run without arguments."""
    actions: list[tuple[str, str, str]] = []

    if docs:
        first_doc = docs[0]
        actions.append(("build", f"Compile '{first_doc.name}' to PDF", "Immediate Typst/LaTeX compilation"))
        actions.append(("watch", f"Watch & live compile '{first_doc.name}'", "Recompiles instantly on file save"))
        if len(docs) > 1:
            actions.append(("select_build", "Pick from discovered documents...", f"{len(docs)} document targets found"))
    else:
        actions.append(("build_custom", "Compile a document to PDF...", "Specify a document file path to compile"))
        actions.append(("watch_custom", "Watch & live compile a document...", "Live reload a specific document file path"))

    # Check for chapters / modules directory or offer assemble
    ch_dirs = [d.name for d in Path(".").iterdir() if d.is_dir() and not d.name.startswith(".")] if Path(".").exists() else []
    detected_ch = [d for d in ("chapters", "modules", "sections", "parts") if d in ch_dirs]
    if detected_ch:
        desc = f"Join markdown files from ./{detected_ch[0]}/ into a master document"
    else:
        desc = "Join modular chapter markdown files into a master document"
    actions.append(("assemble", "Assemble modular chapters (join multiple .md files)", desc))

    actions.append(("init_info", "Workspace scaffolding & templates", "Flaker bootstrap guides and starter templates"))
    actions.append(("exit", "Exit", "Close Folio"))

    choice = ui.select("Folio Quick Actions:", actions)

    if choice == "exit":
        return 0
    elif choice == "init_info":
        _print_init_info()
        return 0
    elif choice == "assemble":
        default_dir = detected_ch[0] if detected_ch else "chapters"
        ch_dir = ui.prompt("Directory containing chapter markdown files", default=default_dir)
        ok = assemble_documents(chapters_dir=ch_dir)
        if ok and ui.confirm("Compile assembled document to PDF now?", default=True):
            build_pdf(
                target_file=None,
                open_after=bool(user_cfg.get("open", False)),
            )
        return 0 if ok else 1
    elif choice == "build" and docs:
        ok = build_pdf(
            target_file=str(docs[0]),
            open_after=bool(user_cfg.get("open", False)),
        )
        return 0 if ok else 1
    elif choice == "watch" and docs:
        watch_pdf(
            target_file=str(docs[0]),
            open_after=bool(user_cfg.get("open", False)),
        )
        return 0
    elif choice == "select_build" and docs:
        options = [
            (
                str(d),
                f"{'📄' if d.suffix == '.md' else ('❄️' if d.suffix == '.typ' else '📜')} {d.name}",
                f"{d.stat().st_size:,} bytes",
            )
            for d in docs
        ]
        chosen = ui.select("Select document to compile:", options)
        ok = build_pdf(
            target_file=chosen,
            open_after=bool(user_cfg.get("open", False)),
        )
        return 0 if ok else 1
    elif choice == "build_custom":
        target = ui.prompt("Document path to compile (.md, .typ, .tex)", default="report.md")
        if not Path(target).exists():
            ui.error(f"File not found: '{target}'")
            return 1
        ok = build_pdf(
            target_file=target,
            open_after=bool(user_cfg.get("open", False)),
        )
        return 0 if ok else 1
    elif choice == "watch_custom":
        target = ui.prompt("Document path to watch & live compile", default="report.md")
        if not Path(target).exists():
            ui.error(f"File not found: '{target}'")
            return 1
        watch_pdf(
            target_file=target,
            open_after=bool(user_cfg.get("open", False)),
        )
        return 0

    return 0


def _parse_assemble_args(rest: list[str]) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="folio assemble", add_help=False)
    parser.add_argument("chapters_dir", nargs="?", default="chapters")
    parser.add_argument("-o", "--output", dest="output_filename", default=None)
    parser.add_argument("-m", "--mode", dest="mode", default=None)
    parser.add_argument("--title", dest="title", default=None)
    parser.add_argument("--subtitle", dest="subtitle", default=None)
    parser.add_argument("--author", dest="author", default=None)
    parser.add_argument("--dependency", dest="dependency", default=None)
    parser.add_argument("--date", dest="date", default=None)
    parser.add_argument("--engine", dest="engine", default=None)
    parser.add_argument("--theme", dest="theme", default=None)
    parser.add_argument("--aspect-ratio", dest="aspect_ratio", default=None)
    parser.add_argument("--pattern", dest="pattern", default="*.md")
    parser.add_argument(
        "--no-pagebreaks",
        dest="add_pagebreaks",
        action="store_false",
        default=True,
    )
    args, _ = parser.parse_known_args(rest)
    return vars(args)


def _parse_build_args(rest: list[str], user_cfg: dict[str, Any]) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="folio", add_help=False)
    parser.add_argument("target_file", nargs="?", default=None)
    parser.add_argument("-o", "--output", dest="output_filename", default=None)
    parser.add_argument("-m", "--mode", dest="mode", default=None)
    parser.add_argument("-p", "--preset", dest="preset", default=None)
    parser.add_argument("-t", "--template", dest="custom_template", default=user_cfg.get("template"))
    parser.add_argument("-w", "--watch", dest="is_watch", action="store_true", default=False)
    parser.add_argument("--engine", dest="engine", default=user_cfg.get("engine"))
    parser.add_argument("--root", dest="root_path", default=user_cfg.get("root"))
    parser.add_argument("--font-path", dest="font_path", default=user_cfg.get("font_path"))
    parser.add_argument("--open", dest="open_after", action="store_true", default=bool(user_cfg.get("open", False)))
    args, _ = parser.parse_known_args(rest)
    return vars(args)


def main(argv: Sequence[str] | None = None) -> int:
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    user_cfg = load_user_config()
    if "color" in user_cfg:
        ui.set_color_mode(str(user_cfg["color"]))
    handle_color_args(raw_args)

    if any(a in ("-h", "--help", "help") for a in raw_args):
        print(USAGE)
        return 0

    if any(a in ("-V", "-v", "--version", "version") for a in raw_args):
        print(f"{ui.badge()} {ui.bold(f'v{__version__}')}")
        return 0

    # No arguments provided: display dashboard panel!
    if not raw_args:
        docs = print_status_dashboard()
        if sys.stdin.isatty():
            return run_interactive_hub(docs, user_cfg)
        else:
            if docs:
                ok = build_pdf(
                    target_file=str(docs[0]),
                    open_after=bool(user_cfg.get("open", False)),
                )
                return 0 if ok else 1
            return 0

    cmd = raw_args[0]
    rest = raw_args[1:]

    if cmd == "init":
        _print_init_info()
        return 0

    if cmd == "assemble":
        asm_kwargs = _parse_assemble_args(rest)
        ok = assemble_documents(**asm_kwargs)
        return 0 if ok else 1

    # Build command or direct file/options
    build_args = rest if cmd == "build" else raw_args
    opts = _parse_build_args(build_args, user_cfg)
    is_watch = opts.pop("is_watch", False)

    if is_watch:
        watch_pdf(**opts)
        return 0
    else:
        ok = build_pdf(**opts)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
