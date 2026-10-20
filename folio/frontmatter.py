"""Frontmatter extraction, mode normalization, and Typst kwargs builder for Folio."""

from __future__ import annotations

from pathlib import Path


def normalize_mode(mode_val: str | None, preset_val: str | None = None) -> str:
    """Normalizes document mode alias ('report', 'slides', 'paper')."""
    raw = (mode_val or preset_val or "report").lower().strip()
    if raw in ("slides", "presentation", "deck"):
        return "slides"
    if raw in ("paper", "ieee", "academic"):
        return "paper"
    return "report"


def parse_frontmatter(file_path: Path) -> dict[str, str]:
    """Extracts key-value YAML frontmatter from a Markdown document.

    Handles quotes, inline comments (e.g. `engine: latex # comment`),
    and normalizes keys to snake_case.
    """
    fm: dict[str, str] = {}
    try:
        content = file_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            end_idx = content.find("\n---", 3)
            if end_idx != -1:
                yaml_block = content[3:end_idx]
                for raw_line in yaml_block.splitlines():
                    line = raw_line.strip()
                    if line and not line.startswith("#") and ":" in line:
                        k, v = line.split(":", 1)
                        v = v.strip()
                        # Strip inline comments (e.g. `engine: "latex" # Options: typst | latex`)
                        if "#" in v:
                            if (v.startswith('"') and '"' in v[1:]) or (
                                v.startswith("'") and "'" in v[1:]
                            ):
                                q = v[0]
                                close_idx = v.find(q, 1)
                                if close_idx != -1:
                                    v = v[1:close_idx]
                            else:
                                v = v.split("#", 1)[0].strip()
                        clean_key = k.strip().lower().replace("-", "_")
                        fm[clean_key] = v.strip().strip("\"'")
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
                clean_bib = v_str.strip("\"'")
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

    if (
        not has_bib
        and mode == "paper"
        and compile_root
        and (compile_root / "library.bib").exists()
    ):
        kwargs.append('bibliography: bibliography("library.bib")')

    return ", ".join(kwargs)
