"""File watcher and live recompilation loop for Folio."""

from __future__ import annotations

import time
from pathlib import Path

from folio.compiler import build_pdf
from folio.discovery import find_target_file
from folio.ui import ui


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
    poll_interval: float = 0.5,
) -> None:
    """Watches document and template files for changes, recompiling automatically."""
    target_path = find_target_file(target_file)
    ui.info(
        f"Watching '{target_path.name}' for changes (Ctrl+C to stop)...",
        symbol="👁️ ",
    )

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
        cand = Path(tpl_name)
        if cand.exists():
            watched_files.append(cand)

    mtimes = {f: f.stat().st_mtime for f in watched_files if f.exists()}

    try:
        while True:
            time.sleep(poll_interval)
            changed = False
            for f in watched_files:
                if f.exists():
                    current_mtime = f.stat().st_mtime
                    if current_mtime != mtimes.get(f):
                        mtimes[f] = current_mtime
                        changed = True

            if changed:
                timestamp = time.strftime("%H:%M:%S")
                ui.action(
                    f"[{timestamp}] Change detected, rebuilding...",
                    symbol="🔄",
                )
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
