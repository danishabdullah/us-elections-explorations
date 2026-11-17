"""Reconcile the two independent health/wage passes into data/alignment/health_wage_final.csv.

Agreeing values are kept (pass A's row, with pass B's source noted). Each disagreement is resolved at the
source; the resolution and reason are recorded in RESOLVE and written to the notes column.
Run: python3 scripts/reconcile_health_wage.py
"""
import csv
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data" / "alignment"
A = {(r["state"], r["indicator"]): r for r in csv.DictReader(open(D / "health_wage_A.csv", newline=""))}
B = {(r["state"], r["indicator"]): r for r in csv.DictReader(open(D / "health_wage_B.csv", newline=""))}

# (state, indicator): (take_from, value, figure, reason)
RESOLVE = {
    ("ME", "min_wage_level"): ("A", "17plus", "$20", "A's source is newer and the campaign's own: Sept 2026 release says his platform includes 'a $20 an hour federal minimum wage' (re-checked on the page). B's 2014 statement is superseded."),
    ("KS", "health_level"): ("B", "unclear", "", "He rejected Medicare for All but never rejected a public option or defended the current system; the rule's 'neither' needs both. Scores 0 either way."),
    ("NC", "min_wage_level"): ("A", "raise", "$15", "Only record is a 2020 survey asking about the federal minimum; he answered Yes ('$15 is an admirable goal'). Older-only and his comment leans state-level: low confidence."),
    ("NE", "min_wage_level"): ("B", "raise", "$15", "Latest clear position wins: Oct 2024 (Bloomberg Government) he backed a federal $15 minimum, after the July 2024 site text (raise to Nebraska's $12)."),
    ("TX", "min_wage_level"): ("B", "raise", "$15 (said $15 'not enough', Jul 2026)", "Site says $15; on Jul 1 2026 he said $15 'is not going to be enough' without naming a figure, so not confirmed at $17+."),
    ("MN", "min_wage_level"): ("B", "17plus", "$17 indexed", "Both passes 17plus; B cites the campaign's own priorities page."),
    ("MS", "min_wage_level"): ("B", "raise", "indexed", "Both passes raise; B cites the campaign's own priorities page ('tie it to the cost of living')."),
    ("IA", "min_wage_level"): ("A", "raise", "$15 indexed", "Both passes agree; figure formatting only."),
}

out = []
for k in sorted(A):
    a, b = A[k], B[k]
    if k in RESOLVE:
        src, val, fig, why = RESOLVE[k]
        r = dict(a if src == "A" else b)
        r.update(value=val, figure=fig, notes=f"RECONCILED: {why} | A: {a['value']} ({a['source_url']}) | B: {b['value']} ({b['source_url']})")
        r["verify_status"] = "passes disagreed, resolved at source"
    else:
        assert a["value"].strip() == b["value"].strip(), k
        r = dict(a)
        r["notes"] = f"Both passes agree. {a['notes']} | Pass B source: {b['source_url']}"
        r["verify_status"] = "two passes agree"
    out.append(r)

# Recency rule (SCHEMA.md): only 2025-26 evidence decides. Targeted re-search for values that rested on older sources.
rp = D / "health_wage_recent.csv"
if rp.exists():
    idx = {(r["state"], r["indicator"]): r for r in out}
    for n in csv.DictReader(open(rp, newline="")):
        if (n["state"], n["indicator"]) not in idx:
            continue  # rows for other items are applied in build_alignment.py
        r = idx[(n["state"], n["indicator"])]
        old = f'last known {r["value"]}{" " + r["figure"] if r.get("figure") else ""} ({r["source_date"]}: {r["evidence"]})'
        val = n["value"].strip().lower()
        if val == "unclear":
            # no newer evidence: the older position stands, flagged as dated
            r["verify_status"] = "dated: no 2025-26 position found"
            r["evidence"] = f'As of {r["source_date"][:4]}: {r["evidence"]} (no 2025-26 statement found)'
            r["notes"] = f'RECENCY: {n["notes"]}'
            continue
        r.update(value=val, figure=n.get("figure", ""), source_publisher=n["source_publisher"], source_url=n["source_url"],
                 source_date=n["source_date"], verify_status="2025-26 re-search")
        if val == "unclear":
            r["evidence"] = f"No 2025-26 position found; {old}"
        else:
            r["evidence"] = n["evidence"] + f" (earlier: {old})"
        r["notes"] = f'RECENCY: {n["notes"]}'

cols = list(A[next(iter(A))].keys()) + ["verify_status"]
with open(D / "health_wage_final.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); w.writerows(out)
print(len(out), "rows")
for r in out:
    print(r["state"], r["indicator"][:6], r["value"], r["figure"])
