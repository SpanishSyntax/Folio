# Folio 📝❄️

> **Hermetic Multi-Mode Document & Presentation Compiler (Typst + LaTeX)**

Folio is an opinionated, ultra-fast document compiler that turns standard GitHub Flavored Markdown (GFM), Typst, and LaTeX into publication-grade PDFs, IEEE academic papers, and 16:9 presentation slide decks.

---

## ✨ Features

- 🔒 **100% Hermetic & Self-Contained**: Zero host toolchain dependencies. Folio packages `pandoc`, `typst`, and `tectonic` inside its Nix closure, guaranteeing identical PDF compilation on any machine.
- 🎯 **Three Distinct Operating Modes**:
  - 📄 **`report` (Default)**: Clean minimal sans-serif report layout with Inter, dynamic margins, headers, footers, and callouts (A4/Letter).
  - 🖥️ **`slides` (16:9 Presentation)**: Ultra-crisp 16:9 widescreen presentation deck (1920×1080) with dark/light themes, slide counters, and slide breaks on `---` or headers.
  - 📜 **`paper` (IEEE Academic Paper)**: Two-column camera-ready layout with IEEE Roman section numbering (`I.`, `II.`, `A.`), full-width title/abstract/keywords, and serif typography.
- ⚡ **Multi-Format & Polyglot Engine**:
  - Compiles **Markdown** via Typst or LaTeX/Tectonic based on frontmatter `engine: typst | latex` (or `--engine`).
  - Compiles native **`.typ`** files directly with Typst (`typst:report`, `typst:slides`, `typst:paper`).
  - Compiles native **`.tex`** files directly with Tectonic (`latex:report`, `latex:slides`, `latex:paper`).
- 📑 **YAML Frontmatter Integration**: Control title, authors, affiliations, operating mode (`mode: slides`), preset (`preset: ieee`), engine (`engine: typst` or `latex`), theme (`theme: dark`), and geometry directly in Markdown frontmatter.
- 👁️ **Live Watch Mode (`folio <doc> -w`)**: Continuous background watcher that detects file saves and automatically re-compiles the PDF in milliseconds.
- 🤝 **Flaker Integration**: Scaffolding is completely delegated to [Flaker](https://github.com/SpanishSyntax/Flaker) (`flaker init md:report`, `flaker init typst:slides`, `flaker init latex:paper`), providing the full 9-way document scaffolding matrix.

---

## 🚀 Quick Start

1. **Scaffold workspace using Flaker**:
```bash
# Initialize DevShell + templates (template.typ, slides.typ, ieee.typ) + starters
flaker init folio

# Or drop templates into an existing workspace
flaker project folio

# Or drop starter leaf documents
flaker new folio
```

2. **Compile with Folio**:
```bash
# Auto-discover report.md, slides.md, or paper.md in current directory
folio

# Compile a report
folio report.md

# Compile 16:9 presentation slides with live watch mode
folio slides.md -m slides -w

# Compile an IEEE 2-column academic paper
folio paper.md -m paper

# Directly compile native Typst or LaTeX documents
folio main.typ -w
folio main.tex -w
```

---

## 💻 CLI Commands & Options

```text
Usage:
  folio [file] [options]             Build PDF from Markdown, Typst, or LaTeX
  folio build [file] [options]       Explicit build command
  folio init [name] [options]        Scaffold starter document and template

Operating Modes:
  -m, --mode MODE        Document operating mode:
                         • report: Minimal sans-serif document (default, A4/Letter)
                         • slides: 16:9 widescreen presentation (1920x1080)
                         • paper:  Academic paper (IEEE 2-column layout)
  -p, --preset PRESET    Layout preset (e.g., 'ieee', 'default')

Options:
  -o, --output PATH      Specify output PDF filename
  -t, --template PATH    Use custom Typst template file
  -w, --watch            Watch mode: recompile automatically on file changes
  --engine ENGINE        Compiler engine: 'typst' (default) or 'tectonic'
  --root PATH            Typst compilation root directory (default: current directory)
  --font-path PATH       Additional directory containing fonts for Typst
  --open                 Open generated PDF in system viewer after build
  -f, --force            Overwrite existing files during init without prompting
  --color MODE           Color output mode: auto, always, never (default: auto)
  --no-color             Disable colored output
  -h, --help             Show this help message and exit
  -V, -v, --version      Show version information and exit
```

---

## 📄 Frontmatter Formats

Folio dynamically configures layout and styling from standard Markdown YAML frontmatter:

### 1. Presentation Slides (16:9 / 1920×1080)
```markdown
---
title: "Distributed Swarm Intelligence"
subtitle: "Real-time Consensus in GPS-Denied Environments"
author: "Juan José Martínez Guerrero"
dependency: "TUDelft Systems & Control"
date: "October 2026"
mode: "slides"
theme: "dark"          # 'dark' or 'light'
aspect-ratio: "16-9"
---

# Problem Formulation
- Sensor limitations: $O(t^2)$ drift
- Intermittent peer-to-peer wireless links

---

# Mathematical Formulation
Each agent minimizes relative pose error:
$$
\min_{\mathbf{x}_i} \sum_{j \in \mathcal{N}_i} \|\mathbf{x}_i - \mathbf{x}_j - \mathbf{d}_{ij}\|^2
$$
```

### 2. Academic Paper (IEEE 2-Column)
```markdown
---
title: "Resilient Distributed State Estimation for Autonomous Swarms"
author: "Juan José Martínez Guerrero, Member, IEEE, and Alex Rivera"
dependency: "Department of Systems and Control, Delft University of Technology"
email: "j.j.martinezguerrero@tudelft.nl"
abstract: "Autonomous micro-aerial vehicle swarms face rapid dead-reckoning drift..."
keywords: "Swarm robotics, distributed factor graphs, ADMM."
mode: "paper"
preset: "ieee"
---

# Introduction
Autonomous multi-agent systems require distributed awareness...

# System Architecture
Consider an undirected communication graph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$...
```

### 3. Report Document (Default)
```markdown
---
title: "Autonomous Space Exploration Systems"
author: "Juan José Martínez Guerrero"
dependency: "TUDelft Systems & Control"
date: "25/09/2026"
mode: "report"
---

# Introduction
Minimal Inter typography with automatic headers, footers, and page counters.
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

---

## 📁 Repository Structure

```text
Folio/
├── flake.nix               # Flake packaging wrapping pandoc, typst, and tectonic
├── pyproject.toml          # PEP 517 / 621 Python packaging
├── LICENSE                 # MIT License
├── README.md               # Documentation & usage guide
└── folio/
    ├── __init__.py         # Package metadata
    ├── __main__.py         # python -m folio entrypoint
    ├── cli.py              # Multi-mode compiler pipeline & watch daemon
    └── ui.py               # Interactive CLI styling, spinners & menus
```

---

## 📜 License

MIT © SpanishSyntax
