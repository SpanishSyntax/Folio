import os
import subprocess
import sys
import time
from pathlib import Path

from folio.ui import ui

USAGE = f"""{ui.badge()} {ui.bold("Markdown -> Typst PDF Document Compiler")}

{ui.blue("Usage:")}
  folio [file.md] [options]          Build PDF from Markdown
  folio build [file.md] [options]    Explicit build command
  folio init [name] [options]        Scaffold starter template.typ and markdown file

{ui.blue("Options:")}
  -o, --output PATH      Specify output PDF filename
  -t, --template PATH    Use custom Typst template file
  -w, --watch            Watch mode: recompile automatically on file changes
  --root PATH            Typst compilation root directory (default: current directory)
  --font-path PATH       Additional directory containing fonts for Typst
  --open                 Open generated PDF in system viewer after build
  -f, --force            Overwrite existing files during init without prompting
  --color MODE           Color output mode: auto, always, never (default: auto)
  --no-color             Disable colored output
  -h, --help             Show this help message and exit
  -V, -v, --version      Show version information and exit

{ui.blue("Examples:")}
  folio                              # Auto-discover input.md or unique *.md
  folio report.md                    # Compile report.md -> report.pdf
  folio report.md -o final.pdf       # Custom output destination
  folio report.md -w                 # Live recompile on save (watch mode)
  folio report.md --root ..          # Pass compilation root directory to Typst
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
            ui.error(f"File '{arg_path}' not found.")
            sys.exit(1)
        return target

    if Path("input.md").exists():
        return Path("input.md")

    md_files = sorted(list(Path(".").glob("*.md")))
    if len(md_files) == 1:
        return md_files[0]
    elif len(md_files) > 1:
        if sys.stdin.isatty():
            options = [(str(f), f"📄 {f.name}") for f in md_files]
            chosen = ui.select("Multiple Markdown documents found. Select one to compile:", options)
            return Path(chosen)
        names = ", ".join(f.name for f in md_files)
        ui.error(f"Multiple Markdown files found ({names}). Specify one: folio <file.md>")
        sys.exit(1)

    if sys.stdin.isatty():
        action = ui.select(
            "No Markdown document found. What would you like to do?",
            [
                ("init", "Scaffold starter template.typ and input.md (folio init)"),
                ("exit", "Exit"),
            ],
        )
        if action == "init":
            init_workspace()
            return Path("input.md")
        sys.exit(0)

    ui.error("No Markdown file found. Run 'folio init' to scaffold a document.")
    sys.exit(1)


def resolve_template(custom_template: str | None) -> tuple[Path, bool]:
    """
    Resolves the Typst template.
    Returns (template_path, is_temporary).
    """
    if custom_template:
        t_path = Path(custom_template)
        if not t_path.exists():
            ui.error(f"Custom template '{custom_template}' not found.")
            sys.exit(1)
        return t_path, False

    local_template = Path("template.typ")
    if local_template.exists():
        return local_template, False

    bundled = get_bundled_assets_dir() / "template.typ"
    if bundled.exists():
        temp_tpl = Path("_folio_template.typ")
        temp_tpl.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")
        return temp_tpl, True

    ui.error("template.typ not found. Run 'folio init' to scaffold a template.")
    sys.exit(1)


def build_pdf(
    target_file: str | None = None,
    output_filename: str | None = None,
    custom_template: str | None = None,
    root_path: str | None = None,
    font_path: str | None = None,
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
            ui.action(f"Parsing '{md_path.name}' via Pandoc...", symbol="⚙️ ")

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
            ui.error(f"Pandoc conversion failed:\n{res_pandoc.stderr.strip()}")
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
            ui.action(f"Compiling PDF: {out_pdf}...", symbol="⚙️ ")

        compile_cmd = ["typst", "compile"]
        compile_root = str(Path(root_path).resolve()) if root_path else "."
        compile_cmd.extend(["--root", compile_root])
        if font_path:
            compile_cmd.extend(["--font-path", str(Path(font_path).resolve())])
        compile_cmd.extend([str(entry_path), out_pdf])

        res = subprocess.run(
            compile_cmd,
            env=run_env,
            capture_output=True,
            text=True,
        )

        if res.returncode == 0:
            ui.success(f"Successfully compiled {out_pdf}")
            if open_after:
                open_cmd = "xdg-open" if sys.platform.startswith("linux") else "open"
                subprocess.Popen([open_cmd, out_pdf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        else:
            ui.error(f"Typst compilation failed:\n{res.stderr.strip()}")
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
    root_path: str | None = None,
    font_path: str | None = None,
    open_after: bool = False,
):
    """Watches markdown file and template for changes, recompiling automatically."""
    md_path = find_target_markdown(target_file)
    ui.info(f"Watching '{md_path.name}' for changes (Ctrl+C to stop)...", symbol="👁️ ")

    # Initial build
    build_pdf(
        target_file=str(md_path),
        output_filename=output_filename,
        custom_template=custom_template,
        root_path=root_path,
        font_path=font_path,
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
                ui.action(f"[{timestamp}] Change detected, rebuilding...", symbol="🔄")
                build_pdf(
                    target_file=str(md_path),
                    output_filename=output_filename,
                    custom_template=custom_template,
                    root_path=root_path,
                    font_path=font_path,
                    open_after=False,
                    quiet=True,
                )
    except KeyboardInterrupt:
        print()
        ui.info("Watch mode stopped.", symbol="🛑")


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
                ans = ui.select(
                    f"{dest.name} already exists. Overwrite?",
                    [
                        ("no", f"Keep existing {dest.name}"),
                        ("yes", f"Overwrite {dest.name}"),
                    ],
                )
                if ans != "yes":
                    ui.warn(f"Skipped {dest.name}")
                    continue
            else:
                ui.error(f"{dest.name} already exists. Pass --force to overwrite.")
                sys.exit(1)

        if src.exists():
            content = src.read_text(encoding="utf-8")
            if name and dest == dest_doc:
                content = content.replace("Document Title", name.replace("_", " ").title())
            dest.write_text(content, encoding="utf-8")
            ui.success(f"Scaffolded {dest.name}")
        else:
            ui.error(f"Source asset {src} not found.")

    ui.info(f"Ready! Run 'folio {doc_name}' or 'folio {doc_name} -w' to build.", symbol="🚀")


def handle_color_args():
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--no-color":
            ui.set_color_mode("never")
        elif arg.startswith("--color="):
            ui.set_color_mode(arg.split("=", 1)[1])
        elif arg == "--color" and i + 1 < len(sys.argv[1:]):
            ui.set_color_mode(sys.argv[1:][i + 1])


def main():
    handle_color_args()
    args = sys.argv[1:]

    if any(a in ("-h", "--help", "help") for a in args):
        print(USAGE)
        sys.exit(0)

    if any(a in ("-V", "-v", "--version", "version") for a in args):
        print(f"{ui.badge()} {ui.bold('v0.1.0')}")
        sys.exit(0)

    if not args:
        if not Path("input.md").exists() and not list(Path(".").glob("*.md")):
            if sys.stdin.isatty():
                action = ui.select(
                    "No Markdown document found in current directory. What would you like to do?",
                    [
                        ("init", "Scaffold starter template.typ and input.md (folio init)"),
                        ("help", "Show help and command usage"),
                        ("exit", "Exit"),
                    ],
                )
                if action == "init":
                    init_workspace()
                    sys.exit(0)
                elif action == "help":
                    print(USAGE)
                    sys.exit(0)
                else:
                    sys.exit(0)
            else:
                print(USAGE)
                sys.exit(0)

    cmd = args[0] if args else ""
    rest = args[1:] if args else []

    if cmd == "init":
        force = "-f" in rest or "--force" in rest
        filtered = [a for a in rest if a not in ("-f", "--force")]
        name = filtered[0] if filtered else None
        init_workspace(name, force=force)
        sys.exit(0)

    rest_args = rest if cmd == "build" else args

    target_file = None
    output_filename = None
    custom_template = None
    root_path = None
    font_path = None
    is_watch = False
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
            custom_template=custom_template,
            root_path=root_path,
            font_path=font_path,
            open_after=open_after,
        )
    else:
        success = build_pdf(
            target_file=target_file,
            output_filename=output_filename,
            custom_template=custom_template,
            root_path=root_path,
            font_path=font_path,
            open_after=open_after,
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
