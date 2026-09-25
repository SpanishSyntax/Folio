# Folio 📝❄️

> **Hermetic Markdown to Typst PDF Document Compiler**

Folio is an opinionated, ultra-fast document compiler that turns standard GitHub Flavored Markdown (GFM) and LaTeX math into publication-grade, beautifully typeset PDF documents via Typst.

---

## ✨ Features

- 🔒 **100% Self-Contained & Hermetic**: Zero host toolchain dependencies. Folio packages and wraps both `pandoc` and `typst` in its Nix closure, guaranteeing identical PDF output on any machine.
- 🎨 **Modern Typographic Engine**: Out-of-the-box minimal sans-serif design system with Inter, automatic page headers/footers, dynamic margin layouts, callout blocks, and syntax highlighting.
- 📑 **YAML Frontmatter Integration**: Extracts metadata (`title`, `author`, `dependency`, `date`) from standard Markdown YAML headers directly into document layout headers.
- 👁️ **Live Watch Mode (`folio watch`)**: Continuous background watcher that detects file saves and automatically re-compiles the PDF in milliseconds.
- 📦 **Built-in Template Fallback**: Compiles any standalone `.md` file without requiring a local `template.typ`. If a local template is present, Folio seamlessly uses your custom layout.
- 🚀 **Instant Scaffolding (`folio init`)**: Generates starter documents (`input.md`) and local `template.typ` files for full layout customization.
- 🌐 **Universal Portability**: Run anywhere with zero installation using `nix run github:SpanishSyntax/Folio`.

---

## 🚀 Quick Start

Run Folio directly with Nix:

```bash
# Compile any markdown document to PDF
nix run github:SpanishSyntax/Folio -- document.md

# Auto-discover input.md or unique *.md in the current folder
nix run github:SpanishSyntax/Folio

# Continuous watch mode (recompiles on save)
nix run github:SpanishSyntax/Folio -- watch document.md

# Specify custom PDF output name
nix run github:SpanishSyntax/Folio -- document.md -o output.pdf

# Open in system PDF viewer after compiling
nix run github:SpanishSyntax/Folio -- document.md --open

# Scaffold starter document and local template.typ
nix run github:SpanishSyntax/Folio -- init my_report
```

---

## 💻 CLI Commands & Options

```text
Usage:
  folio [file.md] [options]          Build PDF from Markdown
  folio build [file.md] [options]    Explicit build command
  folio watch [file.md] [options]    Watch for changes and continuously rebuild
  folio init [name] [options]        Scaffold starter template.typ and markdown file

Options:
  -o, --output PATH      Specify output PDF filename
  -t, --template PATH    Use custom Typst template file
  -w, --watch            Watch mode: recompile automatically on file changes
  --open                 Open generated PDF in system viewer after build
  -f, --force            Overwrite existing files during init without prompting
  -h, --help             Show this help message and exit
  -v, --version          Show version information and exit
```

---

## 📄 Markdown & Frontmatter Format

Folio uses standard GitHub Flavored Markdown with YAML frontmatter:

```markdown
---
title: "Autonomous Space Exploration Systems"
author: "Juan José Martínez Guerrero"
dependency: "TUDelft Systems & Control"
date: "25/09/2026"
---

# Introduction

Folio compiles standard Markdown directly into Typst.

- Standard GFM lists and checklists
- Math equations: $E = m c^2$
- Raw Typst blocks when you need special formatting:

```{=typst}
#lorem(30)
```
```

---

## 🛠️ Home Manager Configuration

Add Folio to your `flake.nix`:

```nix
{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    folio = {
      url = "github:SpanishSyntax/Folio";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, folio, ... }: {
    homeConfigurations.user = home-manager.lib.homeManagerConfiguration {
      modules = [
        folio.homeManagerModules.default
        {
          programs.folio.enable = true;
        }
      ];
    };
  };
}
```

Once enabled, `folio` is directly accessible in your interactive shell with all wrapped binaries.

---

## 📁 Repository Structure

```text
Folio/
├── flake.nix               # Flake package & Home Manager module definition
├── pyproject.toml          # Standard PEP 517 / 621 Python project packaging
├── MANIFEST.in             # Asset bundling manifest
├── LICENSE                 # MIT License
├── README.md               # Documentation & usage guide
└── folio/
    ├── __init__.py         # Package metadata
    ├── __main__.py         # python -m folio entrypoint
    ├── cli.py              # CLI core logic, compiler pipeline & watch daemon
    └── templates/          # Default Typst document styling & starter assets
        ├── template.typ    # Turnkey minimal sans-serif Typst design system
        └── input.md        # Starter document with frontmatter examples
```

---

## 📜 License

MIT © SpanishSyntax
