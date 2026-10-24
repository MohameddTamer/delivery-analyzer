#!/usr/bin/env python3
import argparse, csv, html, json, logging, os, sys
from collections import defaultdict

REQUIRED_COLUMNS = ["order_id", "courier", "area", "status", "failure_reason", "shipping_out", "shipping_return"]
VALID_STATUSES = {"delivered", "failed"}
log = logging.getLogger("delivery_analyzer")


def pct(n, d):
    return round(100.0 * n / d, 1) if d else 0.0


def setup_log(path):
    logging.basicConfig(filename=path, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    log.info("run started")


def load_orders(path):
    # Returns clean rows, malformed rows and duplicate rows. Nothing is dropped quietly.
    clean, malformed, duplicates = [], [], []
    seen = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("file is empty, no header row found")
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError("missing required columns: " + ", ".join(missing))
        for lineno, raw in enumerate(reader, start=2):
            reason = row_problem(raw)
            if reason:
                malformed.append({"row": lineno, "reason": reason, "data": {k: v for k, v in raw.items() if k}})
                log.warning("malformed row %s: %s", lineno, reason)
                continue
            oid = raw["order_id"].strip()
            if oid in seen:
                duplicates.append({"row": lineno, "order_id": oid, "first_row": seen[oid]})
                log.warning("duplicate order_id %s on row %s, first seen on row %s", oid, lineno, seen[oid])
                continue
            seen[oid] = lineno
            clean.append(raw)
    return clean, malformed, duplicates


def row_problem(raw):
    if None in raw or any(v is None for v in raw.values()):
        return "wrong number of fields for the header"
    if not (raw.get("order_id") or "").strip():
        return "order_id is empty"
    if not (raw.get("courier") or "").strip():
        return "courier is empty"
    if not (raw.get("area") or "").strip():
        return "area is empty"
    status = (raw.get("status") or "").strip().lower()
    if status not in VALID_STATUSES:
        return f"status '{raw.get('status')}' is not delivered or failed"
    for col in ("shipping_out", "shipping_return"):
        val = (raw.get(col) or "").strip()
        try:
            if float(val) < 0:
                return f"{col} is negative"
        except ValueError:
            return f"{col} value '{val}' is not a number"
    return None


def analyze(rows):
    total = len(rows)
    failed = [r for r in rows if r.get("status", "").strip().lower() == "failed"]
    delivered = [r for r in rows if r.get("status", "").strip().lower() == "delivered"]

    def breakdown(key):
        out = {}
        groups = defaultdict(list)
        for r in rows:
            groups[r.get(key, "unknown") or "unknown"].append(r)
        for name, g in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            f = sum(1 for r in g if r.get("status", "").strip().lower() == "failed")
            out[name] = {"orders": len(g), "failed": f, "failure_rate_pct": pct(f, len(g))}
        return out

    reasons = defaultdict(int)
    money_lost = 0.0
    for r in failed:
        reasons[r.get("failure_reason", "not stated") or "not stated"] += 1
        money_lost += float(r.get("shipping_out") or 0) + float(r.get("shipping_return") or 0)

    return {
        "total_orders": total,
        "delivered": len(delivered),
        "failed": len(failed),
        "failure_rate_pct": pct(len(failed), total),
        "money_lost_on_failed": round(money_lost, 2),
        "by_courier": breakdown("courier"),
        "by_area": breakdown("area"),
        "failure_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
    }


PARTIAL_BLOCKS = " ▏▎▍▌▋▊▉█"


def block_bar(value, top, cells=26):
    # The chart is text, the same blocks the terminal would print. No SVG, no costume.
    if top <= 0:
        return ""
    filled = value / top * cells
    whole = int(filled)
    part = int(round((filled - whole) * 8))
    if part == 8:
        whole, part = whole + 1, 0
    return "█" * whole + (PARTIAL_BLOCKS[part] if part else "")


def tui_rows(data, alert_pct):
    top = max([d[1] for d in data] or [0]) or 1
    rows = []
    for label, rate, failed, orders in data:
        cls = "hot" if rate >= alert_pct else ""
        rows.append(
            f'<div class="ln rowline"><span class="lab">{html.escape(str(label))}</span>'
            f'<span class="bar {cls}">{block_bar(rate, top)}</span>'
            f'<span class="fig">{rate}%  {failed}/{orders}</span></div>')
    return rows


def write_html_report(rep, path, alert_pct, source_name="orders.csv"):
    courier_data = [(k, v["failure_rate_pct"], v["failed"], v["orders"]) for k, v in rep["by_courier"].items()]
    area_data = [(k, v["failure_rate_pct"], v["failed"], v["orders"]) for k, v in rep["by_area"].items()]
    lines = []
    lines.append('<div class="ln prompt"><span class="sigil">$</span> '
                 f'python3 analyzer.py {html.escape(source_name)} --report report.html</div>')
    lines.append('<div class="ln dim">delivery-analyzer — failure report, printed from the run itself.'
                 f' alert threshold {alert_pct}%. bars at or over it burn amber.</div>')
    lines.append('<div class="ln rule"></div>')
    lines.append(f'<div class="ln">orders analysed : {rep["total_orders"]}</div>')
    lines.append(f'<div class="ln">delivered       : {rep["delivered"]}</div>')
    lines.append(f'<div class="ln">failed          : {rep["failed"]}  ({rep["failure_rate_pct"]}%)</div>')
    lines.append(f'<div class="ln">money lost on failed deliveries: {rep["money_lost_on_failed"]}</div>')
    lines.append('<div class="ln rule"></div>')
    lines.append('<div class="ln head">FAILURE RATE BY COURIER</div>')
    lines.extend(tui_rows(courier_data, alert_pct))
    lines.append('<div class="ln head">FAILURE RATE BY AREA</div>')
    lines.extend(tui_rows(area_data, alert_pct))
    lines.append('<div class="ln head">TOP FAILURE REASONS</div>')
    for reason, count in rep["failure_reasons"].items():
        lines.append(f'<div class="ln rowline"><span class="lab">{html.escape(str(reason))}</span>'
                     f'<span class="fig">{count}</span></div>')
    lines.append('<div class="ln head">INPUT HYGIENE</div>')
    if rep["malformed_rows"]:
        for m in rep["malformed_rows"]:
            lines.append(f'<div class="ln hot">malformed row {m["row"]}: {html.escape(m["reason"])}</div>')
    else:
        lines.append('<div class="ln dim">malformed rows: none</div>')
    if rep["duplicates"]:
        for d in rep["duplicates"]:
            lines.append(f'<div class="ln hot">duplicate row {d["row"]}: order_id {html.escape(d["order_id"])}'
                         f' duplicates row {d["first_row"]}</div>')
    else:
        lines.append('<div class="ln dim">duplicate orders: none</div>')
    lines.append('<div class="ln rule"></div>')
    lines.append(f'<div class="ln">verdict: {rep["failed"]} of {rep["total_orders"]} orders failed'
                 f' ({rep["failure_rate_pct"]}%), {rep["money_lost_on_failed"]} burned on shipping'
                 ' that went out and came back.<span class="cursor"></span></div>')
    body = "\n".join(
        line.replace('class="ln', f'style="--d:{min(i * 55, 1400)}ms" class="ln', 1) if 'style=' not in line
        else line for i, line in enumerate(lines))
    mark = ('<svg width="30" height="30" viewBox="0 0 30 30" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="delivery analyzer mark"><rect x="1" y="1" width="28" height="28" fill="none" '
            'stroke="#4ADE80" stroke-width="2"/><rect x="6" y="17" width="4" height="7" fill="#4ADE80"/>'
            '<rect x="13" y="12" width="4" height="12" fill="#4ADE80"/>'
            '<rect x="20" y="6" width="4" height="18" fill="#F5B83D"/></svg>')
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>delivery-analyzer — failure report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#0B0E0B;color:#4ADE80;font-family:"JetBrains Mono",ui-monospace,"Cascadia Mono",Menlo,Consolas,monospace;
font-size:15px;line-height:1.65;font-variant-numeric:tabular-nums}}
.sheet{{max-width:84ch;margin:0 auto;padding:40px 24px 72px}}
.top{{display:flex;gap:16px;align-items:flex-start;margin-bottom:10px}}
.wordmark{{font-weight:700;letter-spacing:.14em;font-size:13px;padding-top:6px}}
.wordmark small{{display:block;color:#2C5F3F;font-weight:400;letter-spacing:.08em}}
.ln{{opacity:0;animation:appear 1ms steps(1) both;animation-delay:var(--d,0ms);white-space:pre-wrap;word-break:break-word}}
@keyframes appear{{to{{opacity:1}}}}
.dim{{color:#2C5F3F}}
.hot{{color:#F5B83D}}
.rule{{border-top:1px solid #223322;margin:14px 0}}
.head{{margin-top:22px;font-weight:700;letter-spacing:.12em}}
.rowline{{display:flex;gap:2ch;align-items:baseline}}
.lab{{flex:0 0 18ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.bar{{color:#4ADE80;letter-spacing:.06em;white-space:pre}}
.bar.hot{{color:#F5B83D}}
.fig{{color:#4ADE80}}
.prompt .sigil{{color:#F5B83D;font-weight:700}}
.cursor{{display:inline-block;width:.62em;height:1.05em;background:#4ADE80;margin-left:1ch;vertical-align:text-bottom;
animation:blink 1.06s steps(1) infinite}}
@keyframes blink{{50%{{opacity:0}}}}
@media (prefers-reduced-motion: reduce){{.ln{{opacity:1;animation:none}} .cursor{{animation:none}}}}
@media print{{body{{background:#fff;color:#111}} .dim,.fig,.bar{{color:#111}} .hot,.bar.hot,.prompt .sigil{{color:#111}}
.rule{{border-color:#999}} .cursor{{display:none}}}}
</style></head><body>
<main class="sheet">
<div class="top">{mark}<div class="wordmark">DELIVERY-ANALYZER<small>failure report · tui sheet</small></div></div>
{body}
</main></body></html>"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)


def print_report(rep):
    print(f"Orders analysed : {rep['total_orders']}")
    print(f"Delivered       : {rep['delivered']}")
    print(f"Failed          : {rep['failed']}  ({rep['failure_rate_pct']}%)")
    print(f"Money lost on failed deliveries: {rep['money_lost_on_failed']}")
    print("\nWorst couriers by failure rate:")
    for name, s in sorted(rep["by_courier"].items(), key=lambda kv: -kv[1]["failure_rate_pct"]):
        print(f"  {name:<18} {s['failed']:>4}/{s['orders']:<4} failed  {s['failure_rate_pct']}%")
    print("\nWorst areas by failure rate:")
    for name, s in sorted(rep["by_area"].items(), key=lambda kv: -kv[1]["failure_rate_pct"]):
        print(f"  {name:<18} {s['failed']:>4}/{s['orders']:<4} failed  {s['failure_rate_pct']}%")
    print("\nTop failure reasons:")
    for reason, count in rep["failure_reasons"].items():
        print(f"  {reason:<28} {count}")
    if rep["malformed_rows"]:
        print(f"\nMalformed rows skipped: {len(rep['malformed_rows'])}")
        for m in rep["malformed_rows"]:
            print(f"  row {m['row']}: {m['reason']}")
    if rep["duplicates"]:
        print(f"\nDuplicate orders skipped: {len(rep['duplicates'])}")
        for d in rep["duplicates"]:
            print(f"  row {d['row']}: order_id {d['order_id']} duplicates row {d['first_row']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Analyse delivery failures in an orders CSV.")
    ap.add_argument("csv_file")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--report", dest="report_out", help="write a standalone HTML report")
    ap.add_argument("--strict", action="store_true", help="exit with code 2 when malformed or duplicate rows are found")
    ap.add_argument("--log", dest="log_file", default=os.environ.get("ANALYZER_LOG_FILE", "analyzer.log"))
    args = ap.parse_args(argv)
    setup_log(args.log_file)
    alert_pct = float(os.environ.get("ANALYZER_ALERT_PCT", "30"))
    try:
        rows, malformed, duplicates = load_orders(args.csv_file)
    except (OSError, ValueError) as exc:
        log.error("cannot read input: %s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rep = analyze(rows)
    rep["malformed_rows"] = malformed
    rep["duplicates"] = duplicates
    rep["config"] = {"alert_pct": alert_pct, "log_file": args.log_file}
    print_report(rep)
    log.info("analysed %s clean rows, %s malformed, %s duplicates", len(rows), len(malformed), len(duplicates))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=2)
        print(f"\nJSON report written to {args.json_out}")
    if args.report_out:
        write_html_report(rep, args.report_out, alert_pct, os.path.basename(args.csv_file))
        print(f"HTML report written to {args.report_out}")
    if args.strict and (malformed or duplicates):
        log.warning("strict mode, exiting 2 because the input was not clean")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
