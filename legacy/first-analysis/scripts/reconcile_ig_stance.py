"""Reconcile the two independent Israel/Gaza stance assessments into data/alignment/ig_stance_final.csv.

Agreements keep the assessor with more/better-dated evidence. Each disagreement is resolved at the sources;
the decision and reason are in RESOLVE and written to notes.
Run: python3 scripts/reconcile_ig_stance.py
"""
import csv
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data" / "alignment"
A = {r["state"]: r for r in csv.DictReader(open(D / "ig_stance_A.csv", newline=""))}
B = {r["state"]: r for r in csv.DictReader(open(D / "ig_stance_B.csv", newline=""))}

# state: (row to take evidence from, final stance, reason)
RESOLVE = {
    "NE": ("B", "4", "A missed his 2026 platform. Re-checked on osbornforsenate.com: 'cutting off aid to Israel until they end their aggression against Gaza', and in May 2026 'They're starving people to death... we should not be complicit.' Cutting off all aid plus calling it starvation he won't be complicit in meets level 4 in substance. His 2024 'justified' remark is superseded."),
    "MA": ("B", "4", "Same arms record as Sanders (Yea on every resolution, 9 of 9 through Apr 2026) and in 2026 he demanded the war stop: 'stop the bombing in Gaza' (primary night) and Netanyahu's 'unconscionable war against Gaza'. Level 4 doesn't require the word genocide; a demand that the atrocity end, with Sanders's arms votes, is equivalent."),
    "IA": ("B", "3", "Direct quote (Council Bluffs, Aug 2025, via The Nonpareil/Gazette): the response 'has been disproportionate'; taxpayer dollars and US support should not go 'toward the hurting or killing of children or civilians' or impeding aid. That is conditioning US support on conduct, plus his Iowa House amendment conditioning support on humanitarian law. His campaign wouldn't address suspending arms sales: medium confidence."),
    "SC": ("A", "2", "Two separate statements criticize the conduct: a 2026 candidate guide ('events... under Netanyahu's leadership have gone too far') and Sept 2025 (Netanyahu's government not acting within international law). No arms position. B saw only the Oct 2026 debate answer."),
    "AK": ("B", "1", "Record is 2023-24 House votes for Israel aid and against withholding it, plus 'I stand firmly with Israel'. Level 0 requires defending the conduct as justified as well; neither assessor found that. Her 2026 campaign declined to say whether her view changed: low confidence."),
    "MS": ("B", "1", "A found nothing; B found an Oct 2026 interview (Mississippi Free Press): won't commit on aid ('would study' it), opposes 'any war crimes', wants Palestinians' dignity respected. No criticism of Israel's conduct, no arms position: low confidence, closest to 1."),
}

out = []
for st in sorted(A):
    a, b = A[st], B[st]
    if st in RESOLVE:
        src, stance, why = RESOLVE[st]
        r = dict(a if src == "A" else b)
        r["stance"], r["verify_status"] = stance, "assessors disagreed, resolved at source"
        r["notes"] = f"RECONCILED: {why} | A rated {a['stance']}, B rated {b['stance']}. {r['notes']}"
    else:
        assert a["stance"] == b["stance"], st
        def n_ev(r): return sum(bool(r[f"evidence_{i}"]) for i in range(1, 5))
        r = dict(b if n_ev(b) >= n_ev(a) else a)
        r["verify_status"] = "two assessors agree"
        r["notes"] = f"Both assessors rated {a['stance']}. {r['notes']}"
    out.append(r)

cols = list(next(iter(A.values())).keys()) + ["verify_status"]
with open(D / "ig_stance_final.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); w.writerows(out)
print(" ".join(f"{r['state']}={r['stance']}" for r in out))
