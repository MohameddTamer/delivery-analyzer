# Redesign Critique — Delivery Analyzer (Retro TUI report + English pass)

Redesign executed 2026-10-24 against `DESIGN-RESEARCH.md` §3.10 and the
18-item anti-list. This file is the evidence record.

## What changed

- `analyzer.py`: the HTML report was rebuilt from a Georgia-and-cards page
  with two SVG bar charts into a Retro TUI sheet — JetBrains Mono only,
  near-black `#0B0E0B`, phosphor `#4ADE80`, dim `#2C5F3F`, amber `#F5B83D`
  for failure data at or over the alert threshold, red banned. The header is
  the literal command that produced the report (`$ python3 analyzer.py
  <file> --report report.html`, the input filename is now passed in from the
  CLI). Charts are block-character bars (full + eighth partials) computed
  from the same rates the CLI prints. Lines reveal in sequence once (55ms
  steps, capped), the verdict line ends with a blinking block cursor, and
  `prefers-reduced-motion` shows the identical final sheet with no motion.
  A drawn pixel-bar brand mark (inline SVG) replaces the text-only title.
  Print styles invert to black on white.
- `tests/test_analyzer.py`: the one HTML assertion updated from "two SVG
  charts with old titles" to the terminal sheet's real markers (section
  heads, block glyph, literal command line, JetBrains Mono).
- `README.md`: the `--report` description and the alert-threshold table row
  now describe the block-character sheet and the amber rule.
- `DESIGN.md`: added.
- Language: the CLI output, sample data and README were already English;
  verified end to end, no Arabic strings remain in user-facing text.

## Evidence

- Tests: **19/19 before, 19/19 after** (`python3 tests/test_analyzer.py`).
- Numbers unchanged: the sample run's terminal output after the redesign is
  byte-identical to the pre-redesign baseline (diff clean, excluding the
  "HTML report written" notice). The sample still reads **12 orders, 6
  delivered, 6 failed (50.0%), money lost 680.0**; courier split still
  A 3/5 60.0%, B 2/4 50.0%, C 1/3 33.3%; reasons still 2/2/2. The generated
  HTML verdict line states the same figures: "6 of 12 orders failed
  (50.0%), 680.0 burned on shipping that went out and came back."
- Analysis logic untouched: `load_orders`, `row_problem`, `analyze` and
  `print_report` are byte-for-byte what they were; only the report writer
  and its call site changed.

## Anti-list items killed in this project

KPI stat-card row (5), one-long-page card stack (6), rounded-everything +
soft shadow (4), traffic-light palette (7), proportional numbers (16 —
mono is tabular by birth), no brand mark (17), absent motion (18 — the run
sequence, with a reduced-motion path), system-stack typography (1).

## Honest gaps

- The report loads JetBrains Mono from Google Fonts; offline it falls back
  to the system mono stack. The sheet is designed to survive that, but the
  exact phosphor look is font-dependent.
- Headless Chromium in this VM hangs on screenshot capture (two attempts,
  one with a fresh profile and a virtual-time budget), so the new sheet was
  verified by markup inspection and test assertions, not by a rendered
  screenshot. First task on a machine with a working browser build: open
  `analyzer.py sample_orders.csv --report report.html` and eyeball the
  reveal timing and bar alignment.
- The line-reveal uses per-line animation delays computed in Python; a very
  large input (hundreds of couriers) caps the delay at 1400ms by design, so
  late lines arrive together rather than one by one. Acceptable for a
  report, noted rather than hidden.
