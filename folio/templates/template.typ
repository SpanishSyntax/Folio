// ==========================================
// MINIMAL SANS-SERIF TEMPLATE (Typst 0.13+)
// ==========================================
#import "@preview/mmdr:0.2.2": mermaid

// ==========================================
// COLOR PALETTE
// ==========================================
#let theme = (
  text: rgb("#18181b"),
  heading: rgb("#09090b"),
  grey-900: rgb("#18181b"),
  grey-800: rgb("#27272a"),
  grey-700: rgb("#3f3f46"),
  grey-600: rgb("#52525b"),
  grey-500: rgb("#71717a"),
  grey-400: rgb("#a1a1aa"),
  grey-300: rgb("#d4d4d8"),
  grey-200: rgb("#e4e4e7"),
  grey-100: rgb("#f4f4f5"),
  subtle-text: rgb("#3f3f46"),
  muted: rgb("#71717a"),
  border: rgb("#e4e4e7"),
  border-dark: rgb("#27272a"),
  bg-subtle: rgb("#f4f4f5"),
  highlight: rgb("#fef08a"),
  inserted: rgb("#15803d"),
)

// ==========================================
// GLOBAL FONT FAMILIES
// ==========================================
#let fonts = (
  sans: ("Inter", "Liberation Sans", "FreeSans"),
  display: ("Inter Display", "Inter"),
  mono: ("Iosevka NF", "Source Code Pro", "Consolas"),
)

#let horizontalrule = (
  v(0.5em) + line(length: 100%, stroke: 0.35pt + theme.border) + v(0.5em)
)

#let report(
  md-path: none,
  author: "Juan José Martínez Guerrero",
  dependency: "TUDelft",
  date: datetime.today().display("[Day]/[Month repr:numerical]/[Year]"),
  doc,
) = {
  // ==========================================
  // READ MARKDOWN FRONTMATTER
  // ==========================================
  let fm = (:)
  if md-path != none {
    let text = read(md-path)
    let m = text.match(regex("^---\\s*\\n([\\s\\S]*?)\\n---\\s*\\n"))
    if m != none {
      let yaml-text = m.captures.at(0)
      for line in yaml-text.split("\n") {
        let trimmed = line.trim()
        if trimmed != "" and trimmed.contains(":") {
          let parts = trimmed.split(":")
          let key = parts.first().trim()
          // Join the rest in case the value itself contains a colon
          let val = parts.slice(1).join(":").trim().trim("\"").trim("'")
          fm.insert(key, val)
        }
      }
    }
  }

  let front-title = fm.at("title", default: none)
  let final-author = fm.at("author", default: author)
  let final-dep = fm.at("dependency", default: dependency)
  let final-date = fm.at("date", default: date)

  // ==========================================
  // PAGE CONFIGURATION
  // ==========================================
  set page(
    paper: "a4",
    margin: (
      x: 2.2cm,
      top: 2.5cm,
      bottom: 2.5cm,
    ),
    header: context {
      set text(
        font: fonts.sans,
        size: 8pt,
        fill: theme.muted,
      )

      if here().page() > 1 {
        grid(
          columns: (1fr, 1fr),
          align(left)[#if final-author != none [#upper(final-author)]],
          align(right)[#final-date],
        )

        v(4pt)

        line(
          length: 100%,
          stroke: 0.35pt + theme.border,
        )
      }
    },
    footer: context {
      set text(
        font: fonts.sans,
        size: 8pt,
        fill: theme.muted,
      )

      line(
        length: 100%,
        stroke: 0.35pt + theme.border,
      )

      v(6pt)

      grid(
        columns: (1fr, 1fr),
        align(left)[
          #if final-dep != none [#final-dep #h(4pt) — #h(4pt)]
          #if final-author != none [#final-author]
        ],
        align(right)[
          Página
          #counter(page).display()
          de
          #counter(page).final().first()
        ],
      )
    },
  )

  // ==========================================
  // BASE TYPOGRAPHY
  // ==========================================
  set text(
    font: fonts.sans,
    size: 9.5pt,
    fill: theme.text,
    lang: "en",
    region: "us"
  )

  set par(
    justify: true,
    leading: 0.65em,
    spacing: 1.5em,
    first-line-indent: 1em,
  )

  // ==========================================
  // TITLE BANNER (Only if provided in frontmatter)
  // ==========================================
  if front-title != none {
    block(
      width: 100%,
      inset: (bottom: 12pt),
    )[
      #text(
        size: 24pt,
        weight: "bold",
        fill: theme.heading,
        tracking: -0.025em,
      )[
        #front-title
      ]

      #if final-author != none or final-dep != none [
        #v(5pt)
        #grid(
          columns: (1fr, 1fr),
          gutter: 12pt,
          if final-author != none [
            #text(
              size: 7.5pt,
              fill: theme.muted,
              tracking: 0.05em,
            )[AUTOR]

            #v(2pt)

            #text(
              size: 8.5pt,
              weight: "bold",
              fill: theme.heading,
            )[#final-author]
          ],
          if final-dep != none [
            #text(
              size: 7.5pt,
              fill: theme.muted,
              tracking: 0.05em,
            )[DEPENDENCIA]

            #v(2pt)

            #text(
              size: 8.5pt,
              weight: "bold",
              fill: theme.heading,
            )[#final-dep]
          ],
        )
      ]
    ]
    v(0.35em)
  }

  // ==========================================
  // TYPOGRAPHIC HIERARCHY
  // ==========================================
  show heading: set block(
    above: 1.4em,
    below: 0.8em,
  )

  show heading.where(level: 1): it => block(
    above: 1.8em,
    below: 1.0em,
    text(
      size: 22pt,
      weight: "bold",
      fill: theme.heading,
      tracking: -0.035em,
      it.body,
    ),
  )

  show heading.where(level: 2): it => block(
    above: 1.5em,
    below: 1em,
    text(
      size: 15pt,
      weight: "bold",
      fill: theme.grey-800,
      tracking: -0.02em,
      it.body,
    ),
  )

  show heading.where(level: 3): it => block(
    above: 1.4em,
    below: 1em,
    text(
      size: 11.5pt,
      weight: "bold",
      fill: theme.grey-500,
      tracking: -0.005em,
      it.body,
    ),
  )

  show heading.where(level: 4): it => block(
    above: 1.3em,
    below: 1em,
    text(
      size: 8.5pt,
      weight: "bold",
      style: "italic",
      fill: theme.grey-800,
      tracking: 0.14em,
      upper(it.body),
    ),
  )

  show heading.where(level: 5): it => block(
    above: 1.2em,
    below: 1em,
    text(
      size: 9.5pt,
      weight: "light",
      style: "italic",
      fill: theme.grey-600,
      it.body,
    ),
  )

  show heading.where(level: 6): it => block(
    above: 1.2em,
    below: 1em,
    text(
      size: 8pt,
      weight: "bold",
      style: "oblique",
      fill: theme.grey-600,
      it.body,
    ),
  )

  // ==========================================
  // BLOCKQUOTES
  // ==========================================
  show quote.where(block: true): it => {
    pad(
      left: 0.5em,
      y: 0.35em,
    )[
      #block(
        stroke: (
          left: 1.5pt + theme.grey-800,
        ),
        inset: (
          left: 10pt,
          y: 2pt,
        ),
        text(
          fill: theme.subtle-text,
          style: "normal",
          it.body,
        ),
      )
    ]
  }

  // ==========================================
  // CODE BLOCKS
  // ==========================================
  show raw.where(block: true): it => {
    block(
      width: 100%,
      fill: theme.bg-subtle,
      inset: (
        x: 12pt,
        y: 10pt,
      ),
      radius: 4pt,
      stroke: 0.3pt + theme.border,
      text(
        font: fonts.mono,
        size: 8pt,
        fill: theme.text,
        it,
      ),
    )
  }

  // ==========================================
  // INLINE CODE
  // ==========================================
  show raw.where(block: false): it => {
    box(
      fill: theme.bg-subtle,
      inset: (
        x: 4pt,
        y: 1.5pt,
      ),
      radius: 3pt,
      stroke: 0.3pt + theme.border,
      text(
        font: fonts.mono,
        size: 8pt,
        fill: theme.heading,
        it,
      ),
    )
  }

  // ==========================================
  // TABLES
  // ==========================================
  set table(
    stroke: none,
    inset: (
      x: 8pt,
      y: 7pt,
    ),
  )

  show table.cell: it => {
    set text(
      size: 8.5pt,
    )
    it
  }

  show table.cell.where(y: 0): it => {
    set text(
      weight: "bold",
      fill: theme.heading,
    )
    it
  }

  show table: it => block(
    stroke: (
      top: 0.5pt + theme.grey-800,
      bottom: 0.5pt + theme.grey-800,
    ),
    it,
  )

  // ==========================================
  // MERMAID
  // ==========================================
  show raw.where(lang: "mermaid"): it => {
    align(
      center,
      mermaid(it.text),
    )
  }

  // ==========================================
  // HTML <mark>
  // ==========================================
  show <mark>: it => box(
    fill: theme.highlight,
    inset: (
      x: 3pt,
      y: 1pt,
    ),
    outset: (
      y: 1.5pt,
    ),
    radius: 2pt,
    it,
  )

  // ==========================================
  // HTML <ins>
  // ==========================================
  show <ins>: it => text(
    fill: theme.inserted,
  )[
    #underline(
      offset: 2pt,
    )[
      #it
    ]
  ]

  doc
}
