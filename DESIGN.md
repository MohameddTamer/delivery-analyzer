# Design — Delivery Analyzer report

## Concept

The report does not pretend to be a dashboard. It is the terminal run, printed:
the prompt line that produced it at the top, the numbers in the order the tool
prints them, and the charts drawn from the same block characters the terminal
itself would use. A courier manager who trusts a terminal at 6am should trust
this page at 6am. The aesthetic is the artifact, not a costume over it.

## Palette

- Ground: near-black green `#0B0E0B`
- Phosphor (text, bars, the mark): `#4ADE80`
- Dim green (secondary lines, the "nothing wrong" rows): `#2C5F3F`
- Amber, failure data at or over the alert threshold only: `#F5B83D`
- Red: banned. In a terminal, red means the system broke, not that a courier did.

Print inverts to black on white; the amber goes with it. Colour is data or it
is nothing.

## Type

**JetBrains Mono**, one face, every size — Google Fonts with a
`ui-monospace / Cascadia Mono / Menlo / Consolas` fallback stack. Weight 400
carries the sheet, 700 marks the section heads and the wordmark. Mono is
tabular by birth, so every column of figures aligns without being asked.
Scale is a flat terminal rhythm (15px base, 1.65 leading), not a marketing
scale; a report is read at arm's length, top to bottom, once.

## Signature move

The report *runs* when it opens. Lines appear in sequence, a few dozen
milliseconds apart, the way the tool printed them, and the sheet ends on the
verdict line with a blinking block cursor after it. Once. Then it is still
forever — a printed run does not keep performing. Under
`prefers-reduced-motion` the whole sheet is simply there, and the final state
is identical either way: the motion is the order of reading, never information.

The charts are horizontal bars built from full and partial block glyphs
(█ ▉ ▊ ▋ ▌ ▍ ▎ ▏), scaled to the worst offender in each section, so the HTML
report and the raw CLI output are visibly the same numbers wearing the same
clothes.

## Deliberate avoidances

- No SVG charts, no cards, no border radius, no shadows — the sheet is one
  column of text ruled by hairlines.
- No scanlines, no glow, no CRT cosplay. The phosphor is a colour, not an effect.
- No red for failure, no traffic-light palette, no pill badges.
- No second typeface and no proportional figures anywhere on the page.
- No filler copy. Every line is either a number, a finding, or the verdict.
