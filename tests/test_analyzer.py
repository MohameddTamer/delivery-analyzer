#!/usr/bin/env python3
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analyzer import analyze, load_orders, row_problem

RESULTS = []

def check(name, cond):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)

def write_csv(text):
    fh = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    fh.write(text); fh.close()
    return fh.name

HEADER = "order_id,courier,area,status,failure_reason,shipping_out,shipping_return\n"
GOOD = HEADER + "1,Courier A,Tanta,delivered,,60,0\n2,Courier A,Tanta,failed,no answer,60,60\n3,Courier B,Zefta,failed,refused,50,50\n"

def main():
    rows, malformed, dups = load_orders(write_csv(GOOD))
    rep = analyze(rows)
    check("core total counts every clean row", rep["total_orders"] == 3 and rep["failed"] == 2)
    check("core failure rate is two thirds", rep["failure_rate_pct"] == 66.7)
    check("core money lost sums out plus return", rep["money_lost_on_failed"] == 220.0)
    check("core courier breakdown splits rates", rep["by_courier"]["Courier B"]["failure_rate_pct"] == 100.0)
    check("clean file has no malformed or duplicates", malformed == [] and dups == [])

    bad_status = write_csv(HEADER + "9,Courier A,Tanta,lost,,60,0\n")
    rows, malformed, dups = load_orders(bad_status)
    check("unknown status is malformed with row number", len(malformed) == 1 and malformed[0]["row"] == 2 and "status" in malformed[0]["reason"])
    check("malformed row is excluded from analysis", rows == [])

    bad_money = write_csv(HEADER + "9,Courier A,Tanta,failed,x,sixty,0\n")
    rows, malformed, dups = load_orders(bad_money)
    check("non numeric shipping is malformed", len(malformed) == 1 and "not a number" in malformed[0]["reason"])

    dup_path = write_csv(HEADER + "7,Courier A,Tanta,delivered,,60,0\n7,Courier B,Zefta,failed,x,50,50\n")
    rows, malformed, dups = load_orders(dup_path)
    check("duplicate order_id is reported once", len(dups) == 1 and dups[0]["order_id"] == "7" and dups[0]["first_row"] == 2)
    check("duplicate row does not double count", len(rows) == 1)

    missing_col = write_csv("order_id,courier\n1,Courier A\n")
    try:
        load_orders(missing_col); raised = False
    except ValueError as exc:
        raised = "missing required columns" in str(exc)
    check("missing columns raise a clear error", raised)

    check("row_problem flags an empty courier", row_problem({"order_id": "1", "courier": "", "area": "Tanta", "status": "delivered", "shipping_out": "1", "shipping_return": "0"}) is not None)

    with tempfile.TemporaryDirectory() as td:
        src = write_csv(GOOD + "2,Courier A,Tanta,failed,dup,60,60\n5,Courier A,Tanta,weird,,60,0\n")
        out_json, out_html, out_log = os.path.join(td, "r.json"), os.path.join(td, "r.html"), os.path.join(td, "a.log")
        tool = os.path.join(os.path.dirname(__file__), "..", "analyzer.py")
        proc = subprocess.run([sys.executable, tool, src, "--json", out_json, "--report", out_html, "--log", out_log],
                              capture_output=True, text=True)
        check("cli exits zero without strict", proc.returncode == 0)
        check("cli prints malformed and duplicate rows", "row 5" in proc.stdout and "duplicates row 3" in proc.stdout)
        data = json.load(open(out_json, encoding="utf-8"))
        check("json carries malformed and duplicate reports", len(data["malformed_rows"]) == 1 and len(data["duplicates"]) == 1)
        doc = open(out_html, encoding="utf-8").read()
        check("html report is a terminal sheet with block charts", "FAILURE RATE BY COURIER" in doc and "FAILURE RATE BY AREA" in doc and "█" in doc and "python3 analyzer.py" in doc and "JetBrains Mono" in doc)
        check("log file is written", os.path.exists(out_log) and "analysed" in open(out_log, encoding="utf-8").read())
        strict = subprocess.run([sys.executable, tool, src, "--strict", "--log", out_log], capture_output=True, text=True)
        check("strict mode exits nonzero on dirty input", strict.returncode == 2)
        clean = subprocess.run([sys.executable, tool, write_csv(GOOD), "--strict", "--log", out_log], capture_output=True, text=True)
        check("strict mode exits zero on clean input", clean.returncode == 0)

    passed = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{passed}/{len(RESULTS)} checks passed")
    return 0 if passed == len(RESULTS) else 1

if __name__ == "__main__":
    raise SystemExit(main())
