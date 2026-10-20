import ctypes
import os
import re
import signal
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

from folio import __version__
from folio.ui import ui


def _linux_set_pdeathsig():
    """Ensures child subprocesses receive SIGTERM if the parent Python process dies."""
    if sys.platform.startswith("linux"):
        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            PR_SET_PDEATHSIG = 1
            libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)
        except Exception:
            pass


def load_user_config() -> dict[str, Any]:
    """Loads optional user defaults from ~/.config/folio/folio.toml."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    cfg_path = base / "folio" / "folio.toml"
    if cfg_path.is_file():
        try:
            with cfg_path.open("rb") as f:
                data = tomllib.load(f)
            return data.get("general", data) if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


USAGE = f"""{ui.badge()} {ui.bold("Polyglot Document & Presentation Compiler (Typst + LaTeX)")}

{ui.blue("Usage:")}
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
  folio                              # Auto-discover target document in workspace
  folio report.md                    # Compile report.md -> report.pdf (using template.typ)
  folio assemble chapters            # Assemble chapters/*.md -> report.md (with pagebreaks)
  folio assemble modules -m slides   # Assemble modules/*.md -> slides.md
  folio deck.md -m slides -w         # Live watch 16:9 presentation (using slides.typ)
  folio paper.md -m paper            # Compile IEEE 2-column paper (using ieee.typ)
  folio main.typ -w                  # Direct Typst compilation with live reload
  folio main.tex                     # Direct LaTeX compilation via Tectonic
"""


def parse_frontmatter(file_path: Path) -> dict[str, str]:
    """Extracts simple key-value YAML frontmatter from a Markdown file."""
    fm: dict[str, str] = {}
    try:
        content = file_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            end_idx = content.find("\n---", 3)
            if end_idx != -1:
                yaml_block = content[3:end_idx]
                for line in yaml_block.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and ":" in line:
                        k, v = line.split(":", 1)
                        v = v.strip()
                        # Strip inline comments (e.g. `engine: "latex" # Options: typst | latex`)
                        if "#" in v:
                            if (v.startswith('"') and '"' in v[1:]) or (v.startswith("'") and "'" in v[1:]):
                                q = v[0]
                                close_idx = v.find(q, 1)
                                if close_idx != -1:
                                    v = v[1:close_idx]
                            else:
                                v = v.split("#", 1)[0].strip()
                        fm[k.strip().lower().replace("-", "_")] = v.strip().strip("\"'")
    except Exception:
        pass
    return fm


def build_typst_kwargs(
    fm: dict[str, str],
    rel_md_path: str,
    compile_root: Path | None = None,
    mode: str = "report",
) -> str:
    """Builds keyword arguments string for Typst show rule from frontmatter."""
    kwargs = [f'md-path: "{rel_md_path}"']
    has_bib = False
    for k, v in fm.items():
        if k in ("mode", "preset", "template"):
            continue
        arg_name = k.replace("_", "-")
        if arg_name == "bibliography":
            has_bib = True
            v_str = str(v).strip()
            if v_str.lower() == "none":
                kwargs.append("bibliography: none")
            else:
                clean_bib = v_str.strip('"\'')
                kwargs.append(f'bibliography: bibliography("{clean_bib}")')
            continue
        if arg_name.replace("-", "").isidentifier():
            v_str = str(v).strip()
            if v_str.lower() == "none":
                kwargs.append(f"{arg_name}: none")
            elif v_str.lower() in ("true", "false"):
                kwargs.append(f"{arg_name}: {v_str.lower()}")
            else:
                escaped_v = v_str.replace("\\", "\\\\").replace('"', '\\"')
                kwargs.append(f'{arg_name}: "{escaped_v}"')

    if not has_bib and mode == "paper" and compile_root and (compile_root / "library.bib").exists():
        kwargs.append('bibliography: bibliography("library.bib")')

    return ", ".join(kwargs)


def normalize_mode(mode_val: str | None, preset_val: str | None = None) -> str:
    """Normalizes mode aliases to canonical modes: 'report', 'slides', or 'paper'."""
    val = (mode_val or "").strip().lower()
    preset = (preset_val or "").strip().lower()

    if preset == "ieee" or val in ("paper", "ieee", "article"):
        return "paper"
    if val in ("slides", "presentation", "slide", "deck", "ppt"):
        return "slides"
    return "report"


def find_target_file(arg_path: str | None) -> Path:
    """Discovers target document (.md, .typ, .tex)."""
    if arg_path:
        target = Path(arg_path)
        if not target.exists():
            ui.error(f"File '{arg_path}' not found.")
            sys.exit(1)
        return target

    for candidate in (
        "report.md", "input.md", "slides.md", "paper.md",
        "report.typ", "slides.typ", "paper.typ",
        "report.tex", "slides.tex", "paper.tex",
        "main.typ", "main.tex",
    ):
        if Path(candidate).exists():
            return Path(candidate)

    doc_files = (
        sorted(list(Path(".").glob("*.md")))
        + sorted(list(Path(".").glob("*.typ")))
        + sorted(list(Path(".").glob("*.tex")))
    )

    doc_files = [f for f in doc_files if not f.name.startswith(("_body", "_entry", "_folio"))]

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
                options.append((str(f), f"{icon} {f.name}", f"{f.stat().st_size:,} bytes"))
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
    mode: str, custom_template: str | None
) -> tuple[Path, str]:
    """
    Resolves the local Typst template and entry function name for the given mode.
    Returns (template_path, entry_func_name).
    """
    mode = normalize_mode(mode)
    entry_funcs = {
        "report": "report",
        "slides": "slides",
        "paper": "paper",
    }
    entry_func = entry_funcs[mode]

    if custom_template:
        t_path = Path(custom_template)
        if not t_path.exists():
            ui.error(f"Custom template '{custom_template}' not found.")
            sys.exit(1)
        return t_path, entry_func

    # Look for local template in workspace
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
        cand_path = Path(cand)
        if cand_path.exists():
            return cand_path, entry_func

    ui.error(
        f"Template '{expected_name}' not found in workspace.\n"
        f"  Run '{ui.bold('flaker project folio')}' to scaffold templates, or specify --template <path>."
    )
    sys.exit(1)


def compile_tectonic(
    tex_path: Path,
    out_pdf: str,
    quiet: bool = False,
    preexec: Any = None,
) -> bool:
    """Compiles LaTeX document using Tectonic."""
    out_path = Path(out_pdf).resolve()
    out_dir = out_path.parent
    expected_out = out_dir / f"{tex_path.stem}.pdf"

    compile_cmd = ["tectonic", str(tex_path), "-o", str(out_dir)]

    if not quiet:
        with ui.spinner(f"Compiling LaTeX via Tectonic: {ui.bold(out_pdf)}...") as sp:
            res = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                preexec_fn=preexec,
            )
            if res.returncode == 0:
                if expected_out != out_path and expected_out.exists():
                    expected_out.replace(out_path)
                sp.stop(f"Successfully compiled {ui.bold(out_pdf)}", ok=True)
                return True
            else:
                sp.stop(f"Tectonic compilation failed for {out_pdf}.", ok=False)
                ui.error_panel("Tectonic Compilation Error", res.stderr.strip() or res.stdout.strip())
                return False
    else:
        res = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            preexec_fn=preexec,
        )
        if res.returncode == 0:
            if expected_out != out_path and expected_out.exists():
                expected_out.replace(out_path)
            ui.success(f"Successfully compiled {out_pdf}")
            return True
        else:
            ui.error_panel("Tectonic Compilation Error", res.stderr.strip() or res.stdout.strip())
            return False


def compile_typst_direct(
    typ_path: Path,
    out_pdf: str,
    root_path: str | None = None,
    font_path: str | None = None,
    quiet: bool = False,
    preexec: Any = None,
) -> bool:
    """Directly compiles a Typst document."""
    compile_cmd = ["typst", "compile"]
    compile_root = str(Path(root_path).resolve()) if root_path else "."
    compile_cmd.extend(["--root", compile_root])
    if font_path:
        compile_cmd.extend(["--font-path", str(Path(font_path).resolve())])
    compile_cmd.extend([str(typ_path), out_pdf])

    run_env = os.environ.copy()

    if not quiet:
        with ui.spinner(f"Compiling Typst PDF: {ui.bold(out_pdf)}...") as sp:
            res = subprocess.run(
                compile_cmd,
                env=run_env,
                capture_output=True,
                text=True,
                preexec_fn=preexec,
            )
            if res.returncode == 0:
                sp.stop(f"Successfully compiled {ui.bold(out_pdf)}", ok=True)
                return True
            else:
                sp.stop(f"Typst compilation failed for {out_pdf}.", ok=False)
                ui.error_panel("Typst Compilation Error", res.stderr.strip())
                return False
    else:
        res = subprocess.run(
            compile_cmd,
            env=run_env,
            capture_output=True,
            text=True,
            preexec_fn=preexec,
        )
        if res.returncode == 0:
            ui.success(f"Successfully compiled {out_pdf}")
            return True
        else:
            ui.error_panel("Typst Compilation Error", res.stderr.strip())
            return False


def build_pdf(
    target_file: str | None = None,
    output_filename: str | None = None,
    mode: str | None = None,
    preset: str | None = None,
    custom_template: str | None = None,
    engine: str | None = None,
    root_path: str | None = None,
    font_path: str | None = None,
    open_after: bool = False,
    quiet: bool = False,
) -> bool:
    """Compiles document (Markdown, Typst, or LaTeX) into PDF."""
    target_path = find_target_file(target_file)
    preexec = _linux_set_pdeathsig if sys.platform.startswith("linux") else None

    if output_filename:
        out_pdf = output_filename
    else:
        out_pdf = f"{target_path.stem.replace('-', '_').replace(' ', '_').lower()}.pdf"

    # Direct LaTeX handling
    if target_path.suffix == ".tex" or engine == "tectonic":
        success = compile_tectonic(target_path, out_pdf, quiet=quiet, preexec=preexec)
        if success and open_after:
            open_cmd = "xdg-open" if sys.platform.startswith("linux") else "open"
            subprocess.Popen([open_cmd, out_pdf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return success

    # Direct Typst handling
    if target_path.suffix == ".typ":
        success = compile_typst_direct(
            target_path,
            out_pdf,
            root_path=root_path,
            font_path=font_path,
            quiet=quiet,
            preexec=preexec,
        )
        if success and open_after:
            open_cmd = "xdg-open" if sys.platform.startswith("linux") else "open"
            subprocess.Popen([open_cmd, out_pdf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return success

    # Markdown pipeline
    fm = parse_frontmatter(target_path)
    effective_engine = (engine or fm.get("engine") or "typst").lower().strip()
    effective_mode = normalize_mode(mode or fm.get("mode"), preset or fm.get("preset"))
    compile_root = Path(root_path).resolve() if root_path else Path(".").resolve()

    # Branch A: Markdown -> LaTeX -> Tectonic
    if effective_engine in ("latex", "tectonic", "tex"):
        body_path = compile_root / "_body.tex"
        entry_path = compile_root / "_entry.tex"
        latex_target_fmt = "beamer" if effective_mode == "slides" else "latex"
        try:
            if not quiet:
                with ui.spinner(f"Parsing '{ui.bold(target_path.name)}' ({ui.bold_cyan(effective_mode)}) via Pandoc (LaTeX)...") as sp:
                    res_p = subprocess.run(
                        ["pandoc", str(target_path), "-f", "markdown", "-t", latex_target_fmt, "-o", str(body_path)],
                        capture_output=True,
                        text=True,
                        preexec_fn=preexec,
                    )
                    if res_p.returncode != 0:
                        sp.stop("Pandoc conversion failed.", ok=False)
                        ui.error_panel("Pandoc Conversion Error", res_p.stderr.strip())
                        return False
            else:
                res_p = subprocess.run(
                    ["pandoc", str(target_path), "-f", "markdown", "-t", latex_target_fmt, "-o", str(body_path)],
                    capture_output=True,
                    text=True,
                    preexec_fn=preexec,
                )
                if res_p.returncode != 0:
                    ui.error_panel("Pandoc Conversion Error", res_p.stderr.strip())
                    return False

            doc_classes = {
                "paper": "\\documentclass[10pt, journal, compsoc]{IEEEtran}",
                "slides": "\\documentclass[aspectratio=169, 11pt]{beamer}",
                "report": "\\documentclass[11pt, a4paper]{report}",
            }
            doc_class = doc_classes.get(effective_mode, "\\documentclass[11pt, a4paper]{report}")
            pkg_input = "\\input{packages.tex}\n" if (compile_root / "packages.tex").exists() else ""
            def tex_safe(val: Any) -> str:
                if not val:
                    return ""
                import re
                return re.sub(r'(?<!\\)&', r'\&', str(val).strip())

            title_val = tex_safe(fm.get("title", ""))
            author_val = tex_safe(fm.get("author", ""))
            date_val = tex_safe(fm.get("date", ""))
            dep_val = tex_safe(fm.get("dependency", ""))
            email_val = fm.get("email", "")
            abstract_val = fm.get("abstract", "")
            keywords_val = fm.get("keywords", "")

            title_cmd = f"\\title{{{title_val}}}\n" if title_val else ""
            date_cmd = f"\\date{{{date_val}}}\n" if date_val else ""

            if effective_mode == "paper":
                if dep_val and email_val:
                    thanks_str = f"\\thanks{{The author is with the {dep_val} (e-mail: {email_val}).}}"
                elif dep_val:
                    thanks_str = f"\\thanks{{The author is with the {dep_val}.}}"
                elif email_val:
                    thanks_str = f"\\thanks{{e-mail: {email_val}}}"
                else:
                    thanks_str = ""
                author_cmd = (
                    f"\\author{{{author_val},~\\IEEEmembership{{Member,~IEEE}}%{thanks_str}}}\n"
                    if author_val
                    else ""
                )
                institute_cmd = ""
            elif effective_mode == "report":
                if author_val and dep_val:
                    author_cmd = f"\\author{{{author_val} \\\\ \\large \\textit{{{dep_val}}}}}\n"
                elif author_val:
                    author_cmd = f"\\author{{{author_val}}}\n"
                else:
                    author_cmd = ""
                institute_cmd = ""
            elif effective_mode == "slides":
                author_cmd = f"\\author{{{author_val}}}\n" if author_val else ""
                institute_cmd = f"\\institute{{{dep_val}}}\n" if dep_val else ""
            else:
                author_cmd = f"\\author{{{author_val}}}\n" if author_val else ""
                institute_cmd = ""

            abstract_cmd = (
                f"\\begin{{abstract}}\n{abstract_val}\n\\end{{abstract}}\n"
                if (abstract_val and effective_mode == "paper")
                else ""
            )
            keywords_cmd = (
                f"\\begin{{IEEEkeywords}}\n{keywords_val}\n\\end{{IEEEkeywords}}\n"
                if (keywords_val and effective_mode == "paper")
                else ""
            )

            pandoc_compat = (
                "\\usepackage{longtable}\n"
                "\\usepackage{fancyvrb}\n"
                "\\providecommand{\\tightlist}{%\n"
                "  \\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}}\n"
                "\\ifdefined\\sout\n"
                "  \\providecommand{\\st}[1]{\\sout{#1}}\n"
                "\\else\n"
                "  \\providecommand{\\st}[1]{#1}\n"
                "\\fi\n"
                "\\newcommand{\\VerbBar}{|}\n"
                "\\newcommand{\\VERB}{\\Verb[commandchars=\\\\\\{\\}]}\n"
                "\\DefineVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\\\\{\\}}\n"
                "\\newenvironment{Shaded}{}{}\n"
                "\\providecommand{\\AlertTok}[1]{\\textcolor[rgb]{1.00,0.00,0.00}{\\textbf{#1}}}\n"
                "\\providecommand{\\AnnotationTok}[1]{\\textcolor[rgb]{0.38,0.63,0.69}{\\textbf{\\textit{#1}}}}\n"
                "\\providecommand{\\AttributeTok}[1]{\\textcolor[rgb]{0.49,0.56,0.16}{#1}}\n"
                "\\providecommand{\\BaseNTok}[1]{\\textcolor[rgb]{0.25,0.63,0.44}{#1}}\n"
                "\\providecommand{\\BuiltInTok}[1]{\\textcolor[rgb]{0.00,0.50,0.00}{#1}}\n"
                "\\providecommand{\\CharTok}[1]{\\textcolor[rgb]{0.25,0.44,0.63}{#1}}\n"
                "\\providecommand{\\CommentTok}[1]{\\textcolor[rgb]{0.38,0.63,0.69}{\\textit{#1}}}\n"
                "\\providecommand{\\CommentVarTok}[1]{\\textcolor[rgb]{0.38,0.63,0.69}{\\textbf{\\textit{#1}}}}\n"
                "\\providecommand{\\ConstantTok}[1]{\\textcolor[rgb]{0.53,0.00,0.00}{#1}}\n"
                "\\providecommand{\\ControlFlowTok}[1]{\\textcolor[rgb]{0.00,0.44,0.13}{\\textbf{#1}}}\n"
                "\\providecommand{\\DataTypeTok}[1]{\\textcolor[rgb]{0.56,0.13,0.00}{#1}}\n"
                "\\providecommand{\\DecValTok}[1]{\\textcolor[rgb]{0.25,0.63,0.44}{#1}}\n"
                "\\providecommand{\\DocumentationTok}[1]{\\textcolor[rgb]{0.73,0.13,0.13}{\\textit{#1}}}\n"
                "\\providecommand{\\ErrorTok}[1]{\\textcolor[rgb]{1.00,0.00,0.00}{\\textbf{#1}}}\n"
                "\\providecommand{\\ExtensionTok}[1]{#1}\n"
                "\\providecommand{\\FloatTok}[1]{\\textcolor[rgb]{0.25,0.63,0.44}{#1}}\n"
                "\\providecommand{\\FunctionTok}[1]{\\textcolor[rgb]{0.02,0.16,0.49}{#1}}\n"
                "\\providecommand{\\ImportTok}[1]{\\textcolor[rgb]{0.00,0.50,0.00}{\\textbf{#1}}}\n"
                "\\providecommand{\\InformationTok}[1]{\\textcolor[rgb]{0.38,0.63,0.69}{\\textbf{\\textit{#1}}}}\n"
                "\\providecommand{\\KeywordTok}[1]{\\textcolor[rgb]{0.00,0.44,0.13}{\\textbf{#1}}}\n"
                "\\providecommand{\\NormalTok}[1]{#1}\n"
                "\\providecommand{\\OperatorTok}[1]{\\textcolor[rgb]{0.40,0.40,0.40}{#1}}\n"
                "\\providecommand{\\OtherTok}[1]{\\textcolor[rgb]{0.00,0.44,0.13}{#1}}\n"
                "\\providecommand{\\PreprocessorTok}[1]{\\textcolor[rgb]{0.74,0.48,0.00}{#1}}\n"
                "\\providecommand{\\RegionMarkerTok}[1]{#1}\n"
                "\\providecommand{\\SpecialCharTok}[1]{\\textcolor[rgb]{0.25,0.44,0.63}{#1}}\n"
                "\\providecommand{\\SpecialStringTok}[1]{\\textcolor[rgb]{0.73,0.40,0.53}{#1}}\n"
                "\\providecommand{\\StringTok}[1]{\\textcolor[rgb]{0.25,0.44,0.63}{#1}}\n"
                "\\providecommand{\\VariableTok}[1]{\\textcolor[rgb]{0.10,0.09,0.49}{#1}}\n"
                "\\providecommand{\\VerbatimStringTok}[1]{\\textcolor[rgb]{0.25,0.44,0.63}{#1}}\n"
                "\\providecommand{\\WarningTok}[1]{\\textcolor[rgb]{0.38,0.63,0.69}{\\textbf{\\textit{#1}}}}\n"
            )
            bib_style = "IEEEtran" if effective_mode == "paper" else "plain"
            bib_block = (
                f"\\nocite{{*}}\n\\bibliographystyle{{{bib_style}}}\n\\bibliography{{library}}\n"
                if (compile_root / "library.bib").exists()
                else ""
            )

            if effective_mode == "report":
                layout_customization = (
                    "\\usepackage[a4paper, top=2.0cm, bottom=2.0cm, left=2.5cm, right=2.5cm]{geometry}\n"
                    "\\makeatletter\n"
                    "\\patchcmd{\\@makechapterhead}{\\vspace*{50\\p@}}{\\vspace*{0pt}}{}{}\n"
                    "\\patchcmd{\\@makeschapterhead}{\\vspace*{50\\p@}}{\\vspace*{0pt}}{}{}\n"
                    "\\makeatother\n"
                )
            else:
                layout_customization = ""

            if effective_mode == "slides":
                theme_val = fm.get("theme", "light")
                if theme_val == "dark":
                    palette_defs = (
                        "\\definecolor{canvasbg}{HTML}{000000}\n"
                        "\\definecolor{cardbg}{HTML}{161618}\n"
                        "\\definecolor{codebg}{HTML}{121214}\n"
                        "\\definecolor{bordercolor}{HTML}{2C2C2E}\n"
                        "\\definecolor{normaltext}{HTML}{F5F5F7}\n"
                        "\\definecolor{headingcolor}{HTML}{FFFFFF}\n"
                        "\\definecolor{subheadingcolor}{HTML}{A1A1A6}\n"
                        "\\definecolor{mutedcolor}{HTML}{86868B}\n"
                        "\\definecolor{accentblue}{HTML}{2997FF}\n"
                    )
                else:
                    palette_defs = (
                        "\\definecolor{canvasbg}{HTML}{FBFBFD}\n"
                        "\\definecolor{cardbg}{HTML}{F5F5F7}\n"
                        "\\definecolor{codebg}{HTML}{F0F0F2}\n"
                        "\\definecolor{bordercolor}{HTML}{E5E5EA}\n"
                        "\\definecolor{normaltext}{HTML}{1D1D1F}\n"
                        "\\definecolor{headingcolor}{HTML}{000000}\n"
                        "\\definecolor{subheadingcolor}{HTML}{515154}\n"
                        "\\definecolor{mutedcolor}{HTML}{86868B}\n"
                        "\\definecolor{accentblue}{HTML}{0071E3}\n"
                    )

                theme_styling = (
                    "\\usetheme{default}\n"
                    "\\usecolortheme{dove}\n"
                    "\\setbeamertemplate{navigation symbols}{}\n"
                    "\\setbeamersize{text margin left=2.0cm, text margin right=2.0cm}\n"
                    "\\setsansfont{Liberation Sans}\n"
                    "\\setmonofont{Liberation Mono}\n"
                    "\\renewcommand{\\familydefault}{\\sfdefault}\n"
                    + palette_defs
                    + "\\setbeamercolor{background canvas}{bg=canvasbg}\n"
                    "\\setbeamercolor{normal text}{fg=normaltext}\n"
                    "\\setbeamercolor{structure}{fg=accentblue}\n"
                    "\\setbeamercolor{frametitle}{fg=headingcolor}\n"
                    "\\setbeamercolor{framesubtitle}{fg=subheadingcolor}\n"
                    "\\setbeamercolor{title}{fg=headingcolor}\n"
                    "\\setbeamercolor{subtitle}{fg=subheadingcolor}\n"
                    "\\setbeamercolor{author}{fg=normaltext}\n"
                    "\\setbeamercolor{institute}{fg=mutedcolor}\n"
                    "\\setbeamercolor{date}{fg=mutedcolor}\n"
                    "\\usebeamercolor[fg]{normal text}\n"
                    "\\setbeamerfont{frametitle}{size=\\fontsize{20pt}{24pt}\\bfseries}\n"
                    "\\setbeamerfont{framesubtitle}{size=\\fontsize{12pt}{15pt}\\normalfont}\n"
                    "\\setbeamerfont{title}{size=\\fontsize{28pt}{34pt}\\bfseries}\n"
                    "\\setbeamerfont{subtitle}{size=\\fontsize{15pt}{20pt}\\normalfont}\n"
                    "\\setbeamertemplate{frametitle}{%\n"
                    "  \\vspace{0.8em}%\n"
                    "  \\begin{beamercolorbox}[wd=\\paperwidth,leftskip=2.0cm,rightskip=2.0cm]{frametitle}%\n"
                    "    {\\usebeamerfont{frametitle}\\textbf{\\insertframetitle}}\\par%\n"
                    "    \\ifx\\insertframesubtitle\\@empty\\else%\n"
                    "      \\vspace{0.25em}%\n"
                    "      {\\usebeamerfont{framesubtitle}\\textcolor{subheadingcolor}{\\insertframesubtitle}}\\par%\n"
                    "    \\fi%\n"
                    "  \\end{beamercolorbox}%\n"
                    "  \\vspace{0.4em}%\n"
                    "}\n"
                    "\\setbeamertemplate{footline}{%\n"
                    "  \\ifnum\\thepage>1%\n"
                    "    \\leavevmode\\hbox{%\n"
                    "      \\begin{beamercolorbox}[wd=\\paperwidth,ht=0ex,dp=3.5ex,leftskip=2.0cm,rightskip=2.0cm]{footline}%\n"
                    "        {\\fontsize{8.5pt}{11pt}\\selectfont\\textcolor{mutedcolor}{\\insertshortauthor\\ifx\\insertshortauthor\\@empty\\else\\ \\textbullet\\ \\fi\\insertshorttitle}}%\n"
                    "        \\hfill%\n"
                    "        {\\fontsize{8.5pt}{11pt}\\selectfont\\textcolor{mutedcolor}{\\insertframenumber{}~/~\\inserttotalframenumber}}%\n"
                    "      \\end{beamercolorbox}%\n"
                    "    }%\n"
                    "    \\vspace{2ex}%\n"
                    "  \\fi%\n"
                    "}\n"
                    "\\setbeamertemplate{title page}{%\n"
                    "  \\begin{minipage}[c][\\textheight][c]{\\textwidth}\n"
                    "    \\centering\n"
                    "    \\vspace{-1.5em}\n"
                    "    {\\usebeamerfont{title}\\inserttitle}\\par\n"
                    "    \\ifx\\insertsubtitle\\@empty\\else\n"
                    "      \\vspace{0.8em}\n"
                    "      {\\usebeamerfont{subtitle}\\textcolor{subheadingcolor}{\\insertsubtitle}}\\par\n"
                    "    \\fi\n"
                    "    \\vspace{2.2em}\n"
                    "    {\\fontsize{13pt}{16pt}\\selectfont\\textbf{\\insertauthor}}\\par\n"
                    "    \\ifx\\insertinstitute\\@empty\\else\n"
                    "      \\vspace{0.4em}\n"
                    "      {\\fontsize{10pt}{14pt}\\selectfont\\textcolor{mutedcolor}{\\insertinstitute}}\\par\n"
                    "    \\fi\n"
                    "    \\ifx\\insertdate\\@empty\\else\n"
                    "      \\vspace{0.3em}\n"
                    "      {\\fontsize{9pt}{13pt}\\selectfont\\textcolor{mutedcolor}{\\insertdate}}\\par\n"
                    "    \\fi\n"
                    "  \\end{minipage}\n"
                    "}\n"
                    "\\setbeamertemplate{itemize item}{\\textcolor{mutedcolor}{\\small$\\bullet$}}\n"
                    "\\setbeamertemplate{itemize subitem}{\\textcolor{mutedcolor}{\\scriptsize\\textendash}}\n"
                    "\\setbeamertemplate{block begin}{\n"
                    "  \\vspace{0.6em}\n"
                    "  \\begin{tcolorbox}[\n"
                    "    enhanced,\n"
                    "    arc=3mm,\n"
                    "    boxrule=0.5pt,\n"
                    "    colframe=bordercolor,\n"
                    "    colback=cardbg,\n"
                    "    coltext=normaltext,\n"
                    "    coltitle=headingcolor,\n"
                    "    title={\\textbf{\\insertblocktitle}},\n"
                    "    fonttitle=\\bfseries\\normalsize,\n"
                    "    attach boxed title to top left={yshift=-2mm, xshift=3mm},\n"
                    "    boxed title style={colback=cardbg, boxrule=0pt},\n"
                    "    top=3mm, bottom=3mm, left=4mm, right=4mm\n"
                    "  ]\n"
                    "}\n"
                    "\\setbeamertemplate{block end}{\\end{tcolorbox}\\vspace{0.4em}}\n"
                )
                entry_content = f"{doc_class}\n{pkg_input}{pandoc_compat}{theme_styling}{title_cmd}{author_cmd}{institute_cmd}{date_cmd}\\begin{{document}}\n\\begin{{frame}}[plain]\n\\titlepage\n\\end{{frame}}\n\\input{{{body_path.name}}}\n{bib_block}\\end{{document}}\n"
            else:
                entry_content = f"{doc_class}\n{pkg_input}{pandoc_compat}{layout_customization}{title_cmd}{author_cmd}{date_cmd}\\begin{{document}}\n\\maketitle\n{abstract_cmd}{keywords_cmd}\\input{{{body_path.name}}}\n{bib_block}\\end{{document}}\n"

            entry_path.write_text(entry_content, encoding="utf-8")
            success = compile_tectonic(entry_path, out_pdf, quiet=quiet, preexec=preexec)
            if success and open_after:
                open_cmd = "xdg-open" if sys.platform.startswith("linux") else "open"
                subprocess.Popen([open_cmd, out_pdf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return success
        finally:
            for temp_file in [entry_path, body_path]:
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except OSError:
                        pass

    # Branch B: Markdown -> Typst pipeline
    template_path, entry_func = resolve_typst_template(
        effective_mode, custom_template or fm.get("template")
    )
    try:
        rel_md_path = os.path.relpath(target_path.resolve(), compile_root)
    except ValueError:
        rel_md_path = str(target_path)

    try:
        rel_template_path = os.path.relpath(template_path.resolve(), compile_root)
    except ValueError:
        rel_template_path = template_path.name

    body_path = compile_root / "_body.typ"
    entry_path = compile_root / "_entry.typ"
    typst_kwargs = build_typst_kwargs(
        fm, rel_md_path, compile_root=compile_root, mode=effective_mode
    )
    packages_import = '#import "packages.typ": *\n' if (compile_root / "packages.typ").exists() else ""
    template_import = (
        '#import "template.typ": *\n'
        if (compile_root / "template.typ").exists() and rel_template_path != "template.typ"
        else ""
    )
    bib_inclusion = (
        f'\n#bibliography("library.bib", title: "References")\n'
        if (compile_root / "library.bib").exists() and effective_mode != "paper"
        else ""
    )

    try:
        if not quiet:
            spinner_msg = f"Parsing '{ui.bold(target_path.name)}' ({ui.bold_cyan(effective_mode)}) via Pandoc..."
            with ui.spinner(spinner_msg) as sp:
                res_pandoc = subprocess.run(
                    [
                        "pandoc",
                        str(target_path),
                        "-f",
                        "markdown",
                        "-t",
                        "typst",
                        "-o",
                        str(body_path),
                    ],
                    capture_output=True,
                    text=True,
                    preexec_fn=preexec,
                )
                if res_pandoc.returncode != 0:
                    sp.stop("Pandoc conversion failed.", ok=False)
                    ui.error_panel("Pandoc Conversion Error", res_pandoc.stderr.strip())
                    return False

                body_content = body_path.read_text(encoding="utf-8")
                body_path.write_text(
                    f'{template_import}{packages_import}#import "{rel_template_path}": *\n\n{body_content}',
                    encoding="utf-8",
                )

                entry_path.write_text(
                    f'{template_import}{packages_import}#import "{rel_template_path}": *\n#show: doc => {entry_func}({typst_kwargs}, doc)\n#include "{body_path.name}"{bib_inclusion}\n',
                    encoding="utf-8",
                )

                sp.update(f"Compiling PDF: {ui.bold(out_pdf)} ({effective_mode})...")

                compile_cmd = ["typst", "compile", "--root", str(compile_root)]
                if font_path:
                    compile_cmd.extend(["--font-path", str(Path(font_path).resolve())])
                compile_cmd.extend([str(entry_path), out_pdf])

                res = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    preexec_fn=preexec,
                )

                if res.returncode == 0:
                    sp.stop(f"Successfully compiled {ui.bold(out_pdf)}", ok=True)
                else:
                    sp.stop(f"Typst compilation failed for {out_pdf}.", ok=False)
                    ui.error_panel("Typst Compilation Error", res.stderr.strip())
                    return False
        else:
            res_pandoc = subprocess.run(
                [
                    "pandoc",
                    str(target_path),
                    "-f",
                    "markdown",
                    "-t",
                    "typst",
                    "-o",
                    str(body_path),
                ],
                capture_output=True,
                text=True,
                preexec_fn=preexec,
            )
            if res_pandoc.returncode != 0:
                ui.error_panel("Pandoc Conversion Error", res_pandoc.stderr.strip())
                return False

            body_content = body_path.read_text(encoding="utf-8")
            body_path.write_text(
                f'{template_import}{packages_import}#import "{rel_template_path}": *\n\n{body_content}',
                encoding="utf-8",
            )

            entry_path.write_text(
                f'{template_import}{packages_import}#import "{rel_template_path}": *\n#show: doc => {entry_func}({typst_kwargs}, doc)\n#include "{body_path.name}"{bib_inclusion}\n',
                encoding="utf-8",
            )

            compile_cmd = ["typst", "compile", "--root", str(compile_root)]
            if font_path:
                compile_cmd.extend(["--font-path", str(Path(font_path).resolve())])
            compile_cmd.extend([str(entry_path), out_pdf])

            res = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                preexec_fn=preexec,
            )
            if res.returncode == 0:
                ui.success(f"Successfully compiled {out_pdf}")
            else:
                ui.error_panel("Typst Compilation Error", res.stderr.strip())
                return False

        if open_after:
            open_cmd = "xdg-open" if sys.platform.startswith("linux") else "open"
            subprocess.Popen([open_cmd, out_pdf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True

    finally:
        for temp_file in [entry_path, body_path]:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass


def watch_pdf(
    target_file: str | None = None,
    output_filename: str | None = None,
    mode: str | None = None,
    preset: str | None = None,
    custom_template: str | None = None,
    engine: str | None = None,
    root_path: str | None = None,
    font_path: str | None = None,
    open_after: bool = False,
):
    """Watches document and template files for changes, recompiling automatically."""
    target_path = find_target_file(target_file)
    ui.info(f"Watching '{target_path.name}' for changes (Ctrl+C to stop)...", symbol="👁️ ")

    # Initial build
    build_pdf(
        target_file=str(target_path),
        output_filename=output_filename,
        mode=mode,
        preset=preset,
        custom_template=custom_template,
        engine=engine,
        root_path=root_path,
        font_path=font_path,
        open_after=open_after,
    )

    watched_files = [target_path]
    if custom_template and Path(custom_template).exists():
        watched_files.append(Path(custom_template))
    for tpl_name in (
        "report.typ",
        "slides.typ",
        "paper.typ",
        "packages.typ",
        "packages.tex",
        "template.typ",
        "ieee.typ",
    ):
        if Path(tpl_name).exists():
            watched_files.append(Path(tpl_name))

    mtimes = {f: f.stat().st_mtime for f in watched_files if f.exists()}

    try:
        while True:
            time.sleep(0.5)
            changed = False
            for f in watched_files:
                if f.exists():
                    current_mtime = f.stat().st_mtime
                    if current_mtime != mtimes.get(f):
                        mtimes[f] = current_mtime
                        changed = True

            if changed:
                timestamp = time.strftime("%H:%M:%S")
                ui.action(f"[{timestamp}] Change detected, rebuilding...", symbol="🔄")
                build_pdf(
                    target_file=str(target_path),
                    output_filename=output_filename,
                    mode=mode,
                    preset=preset,
                    custom_template=custom_template,
                    engine=engine,
                    root_path=root_path,
                    font_path=font_path,
                    open_after=False,
                    quiet=True,
                )
    except KeyboardInterrupt:
        print()
        ui.info("Watch mode stopped.", symbol="🛑")



def assemble_documents(
    chapters_dir: str = "chapters",
    output_filename: str | None = None,
    mode: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    author: str | None = None,
    dependency: str | None = None,
    date: str | None = None,
    engine: str | None = None,
    theme: str | None = None,
    aspect_ratio: str | None = None,
    pattern: str = "*.md",
    add_pagebreaks: bool = True,
) -> bool:
    """Assembles modular chapter Markdown files into a unified document with consolidated frontmatter."""
    work_path = Path(".").resolve()
    ch_path = Path(chapters_dir)
    if not ch_path.is_dir():
        ui.error(f"Chapters directory '{chapters_dir}' not found.")
        return False

    def _natural_key(p: Path) -> list[Any]:
        return [
            int(c) if c.isdigit() else c.lower()
            for c in re.split(r"(\d+)", p.name)
        ]

    matched_files = sorted(
        [f for f in ch_path.glob(pattern) if f.is_file()],
        key=_natural_key,
    )
    if not matched_files:
        ui.error(f"No chapter files matching '{pattern}' found in '{chapters_dir}'.")
        return False

    final_mode = normalize_mode(mode)
    if output_filename:
        out_path = Path(output_filename)
    else:
        out_path = Path("slides.md" if final_mode == "slides" else "report.md")

    existing_meta: dict[str, str] = {}
    if out_path.is_file():
        existing_meta = parse_frontmatter(out_path)

    default_title = work_path.name.replace("-", " ").replace("_", " ").title()
    final_title = (title or existing_meta.get("title") or default_title).strip()
    final_subtitle = (subtitle or existing_meta.get("subtitle") or "").strip()
    final_author = (author or existing_meta.get("author") or "Author").strip()
    final_dependency = (dependency or existing_meta.get("dependency") or "").strip()
    final_date = (date or existing_meta.get("date") or "").strip()
    final_engine = (engine or existing_meta.get("engine") or "typst").strip().lower()

    fm_lines = ["---", f'title: "{final_title}"']
    if final_subtitle:
        fm_lines.append(f'subtitle: "{final_subtitle}"')
    if final_author:
        fm_lines.append(f'author: "{final_author}"')
    if final_dependency:
        fm_lines.append(f'dependency: "{final_dependency}"')
    if final_date:
        fm_lines.append(f'date: "{final_date}"')
    fm_lines.append(f'mode: "{final_mode}"')
    fm_lines.append(f'engine: "{final_engine}"')

    if final_mode == "slides":
        final_theme = (theme or existing_meta.get("theme") or "dark").strip().lower()
        final_aspect = (aspect_ratio or existing_meta.get("aspect_ratio") or "16-9").strip()
        fm_lines.append(f'theme: "{final_theme}"')
        fm_lines.append(f'aspect-ratio: "{final_aspect}"')

    fm_lines.append("---")
    header_block = "\n".join(fm_lines)

    processed_names: list[str] = []
    chapter_bodies: list[str] = []

    for cf in matched_files:
        try:
            content = cf.read_text(encoding="utf-8")
        except Exception as exc:
            ui.error(f"Failed to read chapter file '{cf.name}': {exc}")
            return False

        clean_body = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", content, flags=re.DOTALL).strip()
        if clean_body:
            processed_names.append(cf.name)
            chapter_bodies.append(clean_body)

    if not chapter_bodies:
        ui.error(f"All matched chapter files in '{chapters_dir}' were empty.")
        return False

    if final_mode == "slides":
        separator = "\n\n---\n\n"
    elif add_pagebreaks:
        separator = "\n\n```{=typst}\n#pagebreak()\n```\n\n"
    else:
        separator = "\n\n"

    assembled_content = f"{header_block}\n\n" + separator.join(chapter_bodies) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(assembled_content, encoding="utf-8")

    ui.success(
        f"Assembled {ui.bold(str(len(processed_names)))} chapters into {ui.bold(str(out_path))} ({final_mode} mode)"
    )
    return True


def handle_color_args():
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--no-color":
            ui.set_color_mode("never")
        elif arg.startswith("--color="):
            ui.set_color_mode(arg.split("=", 1)[1])
        elif arg == "--color" and i + 1 < len(sys.argv[1:]):
            ui.set_color_mode(sys.argv[1:][i + 1])


def main():
    user_cfg = load_user_config()
    if "color" in user_cfg:
        ui.set_color_mode(str(user_cfg["color"]))
    handle_color_args()
    args = sys.argv[1:]

    if any(a in ("-h", "--help", "help") for a in args):
        print(USAGE)
        sys.exit(0)

    if any(a in ("-V", "-v", "--version", "version") for a in args):
        print(f"{ui.badge()} {ui.bold(f'v{__version__}')}")
        sys.exit(0)

    cmd = args[0] if args else ""
    rest = args[1:] if args else []

    if cmd == "init":
        ui.info(
            "Scaffolding is handled by Flaker. Run:\n"
            f"  • {ui.bold('flaker init folio')}     # Bootstrap DevShell + report.typ, slides.typ, paper.typ\n"
            f"  • {ui.bold('flaker project folio')}  # Scaffold template files into current directory\n"
            f"  • {ui.bold('flaker new folio')}      # Drop starter documents (report.md, slides.md, paper.md)",
            symbol="❄️ ",
        )
        sys.exit(0)

    if cmd == "assemble":
        chapters_dir = "chapters"
        out_fn = None
        asm_mode = None
        asm_title = None
        asm_sub = None
        asm_author = None
        asm_dep = None
        asm_date = None
        asm_engine = None
        asm_theme = None
        asm_aspect = None
        asm_pat = "*.md"
        add_pb = True

        j = 0
        while j < len(rest):
            arg = rest[j]
            if arg in ("-o", "--output"):
                if j + 1 < len(rest):
                    out_fn = rest[j + 1]
                    j += 1
            elif arg.startswith("--output="):
                out_fn = arg.split("=", 1)[1]
            elif arg in ("-m", "--mode"):
                if j + 1 < len(rest):
                    asm_mode = rest[j + 1]
                    j += 1
            elif arg.startswith("--mode="):
                asm_mode = arg.split("=", 1)[1]
            elif arg.startswith("--title="):
                asm_title = arg.split("=", 1)[1]
            elif arg == "--title" and j + 1 < len(rest):
                asm_title = rest[j + 1]
                j += 1
            elif arg.startswith("--subtitle="):
                asm_sub = arg.split("=", 1)[1]
            elif arg == "--subtitle" and j + 1 < len(rest):
                asm_sub = rest[j + 1]
                j += 1
            elif arg.startswith("--author="):
                asm_author = arg.split("=", 1)[1]
            elif arg == "--author" and j + 1 < len(rest):
                asm_author = rest[j + 1]
                j += 1
            elif arg.startswith("--dependency="):
                asm_dep = arg.split("=", 1)[1]
            elif arg == "--dependency" and j + 1 < len(rest):
                asm_dep = rest[j + 1]
                j += 1
            elif arg.startswith("--date="):
                asm_date = arg.split("=", 1)[1]
            elif arg == "--date" and j + 1 < len(rest):
                asm_date = rest[j + 1]
                j += 1
            elif arg.startswith("--engine="):
                asm_engine = arg.split("=", 1)[1]
            elif arg == "--engine" and j + 1 < len(rest):
                asm_engine = rest[j + 1]
                j += 1
            elif arg.startswith("--theme="):
                asm_theme = arg.split("=", 1)[1]
            elif arg == "--theme" and j + 1 < len(rest):
                asm_theme = rest[j + 1]
                j += 1
            elif arg.startswith("--aspect-ratio="):
                asm_aspect = arg.split("=", 1)[1]
            elif arg == "--aspect-ratio" and j + 1 < len(rest):
                asm_aspect = rest[j + 1]
                j += 1
            elif arg.startswith("--pattern="):
                asm_pat = arg.split("=", 1)[1]
            elif arg == "--pattern" and j + 1 < len(rest):
                asm_pat = rest[j + 1]
                j += 1
            elif arg == "--no-pagebreaks":
                add_pb = False
            elif not arg.startswith("-"):
                chapters_dir = arg
            j += 1

        ok = assemble_documents(
            chapters_dir=chapters_dir,
            output_filename=out_fn,
            mode=asm_mode,
            title=asm_title,
            subtitle=asm_sub,
            author=asm_author,
            dependency=asm_dep,
            date=asm_date,
            engine=asm_engine,
            theme=asm_theme,
            aspect_ratio=asm_aspect,
            pattern=asm_pat,
            add_pagebreaks=add_pb,
        )
        sys.exit(0 if ok else 1)

    rest_args = rest if cmd == "build" else args

    target_file = None
    output_filename = None
    mode = None
    preset = None
    custom_template = user_cfg.get("template")
    engine = user_cfg.get("engine")
    root_path = user_cfg.get("root")
    font_path = user_cfg.get("font_path")
    is_watch = False
    open_after = bool(user_cfg.get("open", False))

    i = 0
    while i < len(rest_args):
        a = rest_args[i]
        if a in ("-w", "--watch"):
            is_watch = True
        elif a == "--open":
            open_after = True
        elif a in ("-m", "--mode"):
            if i + 1 < len(rest_args):
                mode = rest_args[i + 1]
                i += 1
        elif a.startswith("--mode="):
            mode = a.split("=", 1)[1]
        elif a in ("-p", "--preset"):
            if i + 1 < len(rest_args):
                preset = rest_args[i + 1]
                i += 1
        elif a.startswith("--preset="):
            preset = a.split("=", 1)[1]
        elif a == "--engine":
            if i + 1 < len(rest_args):
                engine = rest_args[i + 1]
                i += 1
        elif a.startswith("--engine="):
            engine = a.split("=", 1)[1]
        elif a in ("-o", "--output"):
            if i + 1 < len(rest_args):
                output_filename = rest_args[i + 1]
                i += 1
        elif a.startswith("--output="):
            output_filename = a.split("=", 1)[1]
        elif a in ("-t", "--template"):
            if i + 1 < len(rest_args):
                custom_template = rest_args[i + 1]
                i += 1
        elif a.startswith("--template="):
            custom_template = a.split("=", 1)[1]
        elif a == "--root":
            if i + 1 < len(rest_args):
                root_path = rest_args[i + 1]
                i += 1
        elif a.startswith("--root="):
            root_path = a.split("=", 1)[1]
        elif a == "--font-path":
            if i + 1 < len(rest_args):
                font_path = rest_args[i + 1]
                i += 1
        elif a.startswith("--font-path="):
            font_path = a.split("=", 1)[1]
        elif a in ("--color", "--no-color") or a.startswith("--color="):
            if a == "--color" and i + 1 < len(rest_args):
                i += 1
        elif a in ("-h", "--help"):
            print(USAGE)
            sys.exit(0)
        elif not a.startswith("-"):
            if not target_file:
                target_file = a
        i += 1

    if is_watch:
        watch_pdf(
            target_file=target_file,
            output_filename=output_filename,
            mode=mode,
            preset=preset,
            custom_template=custom_template,
            engine=engine,
            root_path=root_path,
            font_path=font_path,
            open_after=open_after,
        )
    else:
        success = build_pdf(
            target_file=target_file,
            output_filename=output_filename,
            mode=mode,
            preset=preset,
            custom_template=custom_template,
            engine=engine,
            root_path=root_path,
            font_path=font_path,
            open_after=open_after,
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
