"""Document compiler pipelines for Folio (Typst direct, LaTeX/Tectonic, and Markdown)."""

from __future__ import annotations

import ctypes
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from folio.discovery import find_target_file, resolve_typst_template
from folio.frontmatter import build_typst_kwargs, normalize_mode, parse_frontmatter
from folio.templates_latex import build_latex_entry_document
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


def _run_subprocess(
    cmd: list[str],
    env: dict[str, str] | None = None,
    preexec: Any = None,
) -> subprocess.CompletedProcess[str]:
    """Uniform wrapper for subprocess execution."""
    return subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        preexec_fn=preexec,
    )


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
            res = _run_subprocess(compile_cmd, preexec=preexec)
            if res.returncode == 0:
                if expected_out != out_path and expected_out.exists():
                    expected_out.replace(out_path)
                sp.stop(f"Successfully compiled {ui.bold(out_pdf)}", ok=True)
                return True
            else:
                sp.stop(f"Tectonic compilation failed for {out_pdf}.", ok=False)
                ui.error_panel(
                    "Tectonic Compilation Error",
                    res.stderr.strip() or res.stdout.strip(),
                )
                return False
    else:
        res = _run_subprocess(compile_cmd, preexec=preexec)
        if res.returncode == 0:
            if expected_out != out_path and expected_out.exists():
                expected_out.replace(out_path)
            ui.success(f"Successfully compiled {out_pdf}")
            return True
        else:
            ui.error_panel(
                "Tectonic Compilation Error",
                res.stderr.strip() or res.stdout.strip(),
            )
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
            res = _run_subprocess(compile_cmd, env=run_env, preexec=preexec)
            if res.returncode == 0:
                sp.stop(f"Successfully compiled {ui.bold(out_pdf)}", ok=True)
                return True
            else:
                sp.stop(f"Typst compilation failed for {out_pdf}.", ok=False)
                ui.error_panel("Typst Compilation Error", res.stderr.strip())
                return False
    else:
        res = _run_subprocess(compile_cmd, env=run_env, preexec=preexec)
        if res.returncode == 0:
            ui.success(f"Successfully compiled {out_pdf}")
            return True
        else:
            ui.error_panel("Typst Compilation Error", res.stderr.strip())
            return False


def compile_markdown_latex(
    target_path: Path,
    out_pdf: str,
    fm: dict[str, str],
    effective_mode: str,
    compile_root: Path,
    quiet: bool = False,
    preexec: Any = None,
) -> bool:
    """Compiles Markdown document via Pandoc -> LaTeX -> Tectonic."""
    body_path = compile_root / "_body.tex"
    entry_path = compile_root / "_entry.tex"
    latex_target_fmt = "beamer" if effective_mode == "slides" else "latex"

    try:
        pandoc_cmd = [
            "pandoc",
            str(target_path),
            "-f",
            "markdown",
            "-t",
            latex_target_fmt,
            "-o",
            str(body_path),
        ]
        if not quiet:
            with ui.spinner(
                f"Parsing '{ui.bold(target_path.name)}' ({ui.bold_cyan(effective_mode)}) via Pandoc (LaTeX)..."
            ) as sp:
                res_p = _run_subprocess(pandoc_cmd, preexec=preexec)
                if res_p.returncode != 0:
                    sp.stop("Pandoc conversion failed.", ok=False)
                    ui.error_panel("Pandoc Conversion Error", res_p.stderr.strip())
                    return False
        else:
            res_p = _run_subprocess(pandoc_cmd, preexec=preexec)
            if res_p.returncode != 0:
                ui.error_panel("Pandoc Conversion Error", res_p.stderr.strip())
                return False

        entry_content = build_latex_entry_document(
            fm, effective_mode, body_path.name, compile_root
        )
        entry_path.write_text(entry_content, encoding="utf-8")
        return compile_tectonic(entry_path, out_pdf, quiet=quiet, preexec=preexec)
    finally:
        for temp_file in (entry_path, body_path):
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass


def compile_markdown_typst(
    target_path: Path,
    out_pdf: str,
    fm: dict[str, str],
    effective_mode: str,
    compile_root: Path,
    custom_template: str | None = None,
    font_path: str | None = None,
    quiet: bool = False,
    preexec: Any = None,
) -> bool:
    """Compiles Markdown document via Pandoc -> Typst wrapper."""
    template_path, entry_func = resolve_typst_template(
        effective_mode, custom_template or fm.get("template"), base_dir=compile_root
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
    packages_import = (
        '#import "packages.typ": *\n'
        if (compile_root / "packages.typ").exists()
        else ""
    )
    template_import = (
        '#import "template.typ": *\n'
        if (compile_root / "template.typ").exists()
        and rel_template_path != "template.typ"
        else ""
    )
    bib_inclusion = (
        '\n#bibliography("library.bib", title: "References")\n'
        if (compile_root / "library.bib").exists() and effective_mode != "paper"
        else ""
    )

    pandoc_cmd = [
        "pandoc",
        str(target_path),
        "-f",
        "markdown",
        "-t",
        "typst",
        "-o",
        str(body_path),
    ]

    compile_cmd = ["typst", "compile", "--root", str(compile_root)]
    if font_path:
        compile_cmd.extend(["--font-path", str(Path(font_path).resolve())])
    compile_cmd.extend([str(entry_path), out_pdf])

    try:
        if not quiet:
            spinner_msg = f"Parsing '{ui.bold(target_path.name)}' ({ui.bold_cyan(effective_mode)}) via Pandoc..."
            with ui.spinner(spinner_msg) as sp:
                res_pandoc = _run_subprocess(pandoc_cmd, preexec=preexec)
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
                res = _run_subprocess(compile_cmd, preexec=preexec)
                if res.returncode == 0:
                    sp.stop(f"Successfully compiled {ui.bold(out_pdf)}", ok=True)
                    return True
                else:
                    sp.stop(f"Typst compilation failed for {out_pdf}.", ok=False)
                    ui.error_panel("Typst Compilation Error", res.stderr.strip())
                    return False
        else:
            res_pandoc = _run_subprocess(pandoc_cmd, preexec=preexec)
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

            res = _run_subprocess(compile_cmd, preexec=preexec)
            if res.returncode == 0:
                ui.success(f"Successfully compiled {out_pdf}")
                return True
            else:
                ui.error_panel("Typst Compilation Error", res.stderr.strip())
                return False
    finally:
        for temp_file in (entry_path, body_path):
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass


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

    if effective_engine in ("latex", "tectonic", "tex"):
        success = compile_markdown_latex(
            target_path=target_path,
            out_pdf=out_pdf,
            fm=fm,
            effective_mode=effective_mode,
            compile_root=compile_root,
            quiet=quiet,
            preexec=preexec,
        )
    else:
        success = compile_markdown_typst(
            target_path=target_path,
            out_pdf=out_pdf,
            fm=fm,
            effective_mode=effective_mode,
            compile_root=compile_root,
            custom_template=custom_template,
            font_path=font_path,
            quiet=quiet,
            preexec=preexec,
        )

    if success and open_after:
        open_cmd = "xdg-open" if sys.platform.startswith("linux") else "open"
        subprocess.Popen([open_cmd, out_pdf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return success
