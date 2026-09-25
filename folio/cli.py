import os
import subprocess
import sys
import time
from pathlib import Path

USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def style(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


BLUE, GREEN, BOLD_GREEN, YELLOW, RED, BOLD = "1;34", "32", "1;32", "33", "1;31", "1"


def status(icon: str, msg: str, code: str = BOLD) -> str:
    return f"{style('❄️  [folio]', BLUE)} {style(f'{icon} {msg}', code)}"


USAGE = f"""{style("❄️  [folio]", BLUE)} {style("Markdown -> Typst PDF Document Compiler", BOLD)}

{style("Usage:", BLUE)}
  folio [file.md] [options]          Build PDF from Markdown
  folio build [file.md] [options]    Explicit build command
  folio watch [file.md] [options]    Watch for changes and continuously rebuild
  folio init [name] [options]        Scaffold starter template.typ and markdown file

{style("Options:", BLUE)}
  -o, --output PATH      Specify output PDF filename
  -t, --template PATH    Use custom Typst template file
  -w, --watch            Watch mode: recompile automatically on file changes
  --open                 Open generated PDF in system viewer after build
  -f, --force            Overwrite existing files during init without prompting
  -h, --help             Show this help message and exit
  -v, --version          Show version information and exit

{style("Examples:", BLUE)}
  folio                              # Auto-discover input.md or unique *.md
  folio report.md                    # Compile report.md -> report.pdf
  folio report.md -o final.pdf       # Custom output destination
  folio watch document.md            # Live recompile on save
  folio init my_paper                # Scaffold template.typ and my_paper.md
"""


def get_bundled_assets_dir() -> Path:
    """Finds the bundled templates directory."""
    env_dir = os.environ.get("FOLIO_TEMPLATES")
    if env_dir and Path(env_dir).exists():
        return Path(env_dir)
    pkg_dir = Path(__file__).resolve().parent / "templates"
    return pkg_dir


def find_target_markdown(arg_path: str | None) -> Path:
    """Discovers target Markdown document."""
    if arg_path:
        target = Path(arg_path)
        if not target.exists():
            print(status("✘", f"File '{arg_path}' not found.", RED), file=sys.stderr)
            sys.exit(1)
        return target

    if Path("input.md").exists():
        return Path("input.md")

    md_files = sorted(list(Path(".").glob("*.md")))
    if len(md_files) == 1:
        return md_files[0]
    elif len(md_files) > 1:
        names = ", ".join(f.name for f in md_files)
        print(
            status(
                "✘",
                f"Multiple Markdown files found ({names}). Specify one: folio <file.md>",
                RED,
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        status("✘", "No Markdown file found. Run 'folio init' to scaffold a document.", RED),
        file=sys.stderr,
    )
    sys.exit(1)


def resolve_template(custom_template: str | None) -> tuple[Path, bool]:
    """
    Resolves the Typst template.
    Returns (template_path, is_temporary).
    """
    if custom_template:
        t_path = Path(custom_template)
        if not t_path.exists():
            print(status("✘", f"Custom template '{custom_template}' not found.", RED), file=sys.stderr)
            sys.exit(1)
        return t_path, False

    local_template = Path("template.typ")
    if local_template.exists():
        return local_template, False

    # Check bundled fallback
    bundled = get_bundled_assets_dir() / "template.typ"
    if bundled.exists():
        # Copy bundled template locally as temporary file so Typst root can import it cleanly
        temp_tpl = Path("_folio_template.typ")
        temp_tpl.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")
        return temp_tpl, True

    print(
        status(
            "✘",
            "template.typ not found. Run 'folio init' to scaffold a template.",
            RED,
        ),
        file=sys.stderr,
    )
    sys.exit(1)


def build_pdf(
    target_file: str | None = None,
    output_filename: str | None = None,
    custom_template: str | None = None,
    open_after: bool = False,
    quiet: bool = False,
) -> bool:
    """Compiles Markdown document into Typst and produces a PDF."""
    md_path = find_target_markdown(target_file)

    if output_filename:
        out_pdf = output_filename
    else:
        out_pdf = f"{md_path.stem.replace('-', '_').replace(' ', '_').lower()}.pdf"

    template_path, is_temp_template = resolve_template(custom_template)

    body_path = Path("_body.typ")
    entry_path = Path("_entry.typ")

    try:
        if not quiet:
            print(status("⚙️ ", f"Parsing '{md_path.name}' via Pandoc...", BLUE))

        res_pandoc = subprocess.run(
            [
                "pandoc",
                str(md_path),
                "-f",
                "markdown",
                "-t",
                "typst",
                "-o",
                str(body_path),
            ],
            capture_output=True,
            text=True,
        )
        if res_pandoc.returncode != 0:
            print(status("✘", f"Pandoc conversion failed:\n{res_pandoc.stderr.strip()}", RED), file=sys.stderr)
            return False

        body_content = body_path.read_text(encoding="utf-8")
        body_path.write_text(
            f'#import "{template_path.name}": *\n\n{body_content}', encoding="utf-8"
        )

        entry_path.write_text(
            f'#import "{template_path.name}": *\n#show: doc => report(md-path: "{md_path.name}", doc)\n#include "{body_path.name}"\n',
            encoding="utf-8",
        )

        run_env = os.environ.copy()
        if not run_env.get("TYPST_ROOT"):
            run_env.pop("TYPST_ROOT", None)

        if not quiet:
            print(status("⚙️ ", f"Compiling PDF: {out_pdf}...", BLUE))

        res = subprocess.run(
            ["typst", "compile", "--root", ".", str(entry_path), out_pdf],
            env=run_env,
            capture_output=True,
            text=True,
        )

        if res.returncode == 0:
            print(status("✔", f"Successfully compiled {out_pdf}", BOLD_GREEN))
            if open_after:
                open_cmd = "xdg-open" if sys.platform.startswith("linux") else "open"
                subprocess.Popen([open_cmd, out_pdf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        else:
            print(status("✘", f"Typst compilation failed:\n{res.stderr.strip()}", RED), file=sys.stderr)
            return False

    finally:
        for temp_file in [entry_path, body_path]:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
        if is_temp_template and template_path.exists():
            try:
                template_path.unlink()
            except OSError:
                pass


def watch_pdf(
    target_file: str | None = None,
    output_filename: str | None = None,
    custom_template: str | None = None,
    open_after: bool = False,
):
    """Watches markdown file and template for changes, recompiling automatically."""
    md_path = find_target_markdown(target_file)
    print(status("👁️ ", f"Watching '{md_path.name}' for changes (Ctrl+C to stop)...", BLUE))

    # Initial build
    build_pdf(
        target_file=str(md_path),
        output_filename=output_filename,
        custom_template=custom_template,
        open_after=open_after,
    )

    watched_files = [md_path]
    if custom_template and Path(custom_template).exists():
        watched_files.append(Path(custom_template))
    elif Path("template.typ").exists():
        watched_files.append(Path("template.typ"))

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
                print(status("🔄", f"[{timestamp}] Change detected, rebuilding...", YELLOW))
                build_pdf(
                    target_file=str(md_path),
                    output_filename=output_filename,
                    custom_template=custom_template,
                    open_after=False,
                    quiet=True,
                )
    except KeyboardInterrupt:
        print(f"\n{status('🛑', 'Watch mode stopped.', BLUE)}")


def init_workspace(name: str | None = None, force: bool = False):
    """Scaffolds template.typ and an input markdown document."""
    bundled_dir = get_bundled_assets_dir()
    template_src = bundled_dir / "template.typ"
    input_src = bundled_dir / "input.md"

    doc_name = f"{name}.md" if name else "input.md"
    dest_doc = Path(doc_name)
    dest_template = Path("template.typ")

    for dest, src in [(dest_template, template_src), (dest_doc, input_src)]:
        if dest.exists() and not force:
            if sys.stdin.isatty():
                ans = input(f"⚠️  {dest.name} already exists. Overwrite? [y/N]: ").strip().lower()
                if ans not in ("y", "yes"):
                    print(f"Skipping {dest.name}")
                    continue
            else:
                print(f"Error: {dest.name} already exists. Pass --force to overwrite.", file=sys.stderr)
                sys.exit(1)

        if src.exists():
            content = src.read_text(encoding="utf-8")
            if name and dest == dest_doc:
                content = content.replace("Document Title", name.replace("_", " ").title())
            dest.write_text(content, encoding="utf-8")
            print(status("✔", f"Scaffolded {dest.name}", BOLD_GREEN))
        else:
            print(status("✘", f"Source asset {src} not found.", RED), file=sys.stderr)

    print(status("🚀", f"Ready! Run 'folio {doc_name}' or 'folio watch {doc_name}' to build.", BLUE))


def main():
    args = sys.argv[1:]

    if not args or args[0] in ["-h", "--help", "help"]:
        print(USAGE)
        sys.exit(0)

    if args[0] in ["-v", "--version", "version"]:
        print("folio 0.1.0")
        sys.exit(0)

    # Subcommands
    cmd = args[0]
    rest = args[1:]

    if cmd == "init":
        force = "-f" in rest or "--force" in rest
        filtered = [a for a in rest if a not in ("-f", "--force")]
        name = filtered[0] if filtered else None
        init_workspace(name, force=force)
        sys.exit(0)

    # Watch or build
    is_watch = cmd == "watch"
    if is_watch:
        rest_args = rest
    elif cmd == "build":
        rest_args = rest
    else:
        rest_args = args

    # Extract options
    target_file = None
    output_filename = None
    custom_template = None
    open_after = False

    i = 0
    while i < len(rest_args):
        a = rest_args[i]
        if a in ("-w", "--watch"):
            is_watch = True
        elif a == "--open":
            open_after = True
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
            custom_template=custom_template,
            open_after=open_after,
        )
    else:
        success = build_pdf(
            target_file=target_file,
            output_filename=output_filename,
            custom_template=custom_template,
            open_after=open_after,
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
