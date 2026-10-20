"""LaTeX and Beamer preamble templates, theme definitions, and entry document builder."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def tex_safe(val: Any) -> str:
    """Escapes unescaped ampersands and special characters for LaTeX."""
    if not val:
        return ""
    return re.sub(r"(?<!\\)&", r"\&", str(val).strip())


PANDOC_LATEX_COMPAT = (
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


def get_doc_class(mode: str) -> str:
    """Returns the documentclass for LaTeX mode."""
    if mode == "paper":
        return "\\documentclass[10pt, journal, compsoc]{IEEEtran}"
    elif mode == "slides":
        return "\\documentclass[aspectratio=169, 11pt]{beamer}"
    return "\\documentclass[11pt, a4paper]{report}"


def get_report_layout() -> str:
    """Returns custom report geometry and chapter head patches."""
    return (
        "\\usepackage[a4paper, top=2.0cm, bottom=2.0cm, left=2.5cm, right=2.5cm]{geometry}\n"
        "\\makeatletter\n"
        "\\patchcmd{\\@makechapterhead}{\\vspace*{50\\p@}}{\\vspace*{0pt}}{}{}\n"
        "\\patchcmd{\\@makeschapterhead}{\\vspace*{50\\p@}}{\\vspace*{0pt}}{}{}\n"
        "\\makeatother\n"
    )


def get_beamer_theme(theme_val: str = "light") -> str:
    """Generates Beamer theme definitions (colors, fonts, frames, footlines)."""
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

    return (
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


def build_latex_entry_document(
    fm: dict[str, str],
    mode: str,
    body_filename: str,
    compile_root: Path,
) -> str:
    """Builds a complete LaTeX / Tectonic entry file importing the pandoc body."""
    doc_class = get_doc_class(mode)
    pkg_input = (
        "\\input{packages.tex}\n"
        if (compile_root / "packages.tex").exists()
        else ""
    )

    title_val = tex_safe(fm.get("title", ""))
    author_val = tex_safe(fm.get("author", ""))
    date_val = tex_safe(fm.get("date", ""))
    dep_val = tex_safe(fm.get("dependency", ""))
    email_val = fm.get("email", "")
    abstract_val = fm.get("abstract", "")
    keywords_val = fm.get("keywords", "")

    title_cmd = f"\\title{{{title_val}}}\n" if title_val else ""
    date_cmd = f"\\date{{{date_val}}}\n" if date_val else ""

    if mode == "paper":
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
    elif mode == "report":
        if author_val and dep_val:
            author_cmd = (
                f"\\author{{{author_val} \\\\ \\large \\textit{{{dep_val}}}}}\n"
            )
        elif author_val:
            author_cmd = f"\\author{{{author_val}}}\n"
        else:
            author_cmd = ""
        institute_cmd = ""
    elif mode == "slides":
        author_cmd = f"\\author{{{author_val}}}\n" if author_val else ""
        institute_cmd = f"\\institute{{{dep_val}}}\n" if dep_val else ""
    else:
        author_cmd = f"\\author{{{author_val}}}\n" if author_val else ""
        institute_cmd = ""

    abstract_cmd = (
        f"\\begin{{abstract}}\n{abstract_val}\n\\end{{abstract}}\n"
        if (abstract_val and mode == "paper")
        else ""
    )
    keywords_cmd = (
        f"\\begin{{IEEEkeywords}}\n{keywords_val}\n\\end{{IEEEkeywords}}\n"
        if (keywords_val and mode == "paper")
        else ""
    )

    bib_style = "IEEEtran" if mode == "paper" else "plain"
    bib_block = (
        f"\\nocite{{*}}\n\\bibliographystyle{{{bib_style}}}\n\\bibliography{{library}}\n"
        if (compile_root / "library.bib").exists()
        else ""
    )

    if mode == "slides":
        theme_val = fm.get("theme", "light")
        theme_styling = get_beamer_theme(theme_val)
        return (
            f"{doc_class}\n"
            f"{pkg_input}"
            f"{PANDOC_LATEX_COMPAT}"
            f"{theme_styling}"
            f"{title_cmd}"
            f"{author_cmd}"
            f"{institute_cmd}"
            f"{date_cmd}"
            f"\\begin{{document}}\n"
            f"\\begin{{frame}}[plain]\n"
            f"\\titlepage\n"
            f"\\end{{frame}}\n"
            f"\\input{{{body_filename}}}\n"
            f"{bib_block}"
            f"\\end{{document}}\n"
        )
    elif mode == "report":
        layout_customization = get_report_layout()
        return (
            f"{doc_class}\n"
            f"{pkg_input}"
            f"{PANDOC_LATEX_COMPAT}"
            f"{layout_customization}"
            f"{title_cmd}"
            f"{author_cmd}"
            f"{date_cmd}"
            f"\\begin{{document}}\n"
            f"\\maketitle\n"
            f"{abstract_cmd}"
            f"{keywords_cmd}"
            f"\\input{{{body_filename}}}\n"
            f"{bib_block}"
            f"\\end{{document}}\n"
        )
    else:
        return (
            f"{doc_class}\n"
            f"{pkg_input}"
            f"{PANDOC_LATEX_COMPAT}"
            f"{title_cmd}"
            f"{author_cmd}"
            f"{date_cmd}"
            f"\\begin{{document}}\n"
            f"\\maketitle\n"
            f"{abstract_cmd}"
            f"{keywords_cmd}"
            f"\\input{{{body_filename}}}\n"
            f"{bib_block}"
            f"\\end{{document}}\n"
        )
