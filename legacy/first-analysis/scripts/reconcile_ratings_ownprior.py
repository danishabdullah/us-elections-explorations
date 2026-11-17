"""Reconcile the two independent collections of (1) Crystal Ball rating histories and (2) candidates' own earlier statewide results.

Outputs: data/alignment/rating_history.csv, data/own_prior.csv
Run: python3 scripts/reconcile_ratings_ownprior.py   (from the session folder)
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AL, D = ROOT / "data" / "alignment", ROOT / "data"


def read(p):
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh))


# ---------- ratings: both passes found the same 54 ratings and changes; they differ only on two dates by days.
# Pass B's dates are used: MN 2025-02-19 (date of the standalone article; an editors' note suggests it may date to Feb 13,
# pass A's date) and OH 2025-08-12 (the change announced on X; written article Aug 13-14, pass A's date). Neither falls near
# a date the page uses. Pass B's "reaffirmed, not a change" rows for the final ratings are dropped.
A = [r for r in read(AL / "rating_history_A.csv")]
B = [r for r in read(AL / "rating_history_B.csv") if r["previous_rating"] != r["rating"]]
key = lambda rs: sorted((r["state"], r["rating"], r["previous_rating"]) for r in rs)
assert key(A) == key(B), "rating passes disagree on the sequence of ratings"
out = []
for r in B:
    a = next(x for x in A if (x["state"], x["rating"], x["previous_rating"]) == (r["state"], r["rating"], r["previous_rating"]))
    out.append(dict(state=r["state"], date=r["date"], rating=r["rating"], previous_rating=r["previous_rating"],
                    source_title=r["source_title"], source_url=r["source_url"],
                    check=("pass A same date" if a["date"] == r["date"] else f"pass A dated it {a['date']}") + f" ({a['source_url']})",
                    notes=r["notes"]))
out.sort(key=lambda r: (r["state"], r["date"]))
with open(AL / "rating_history.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(len(out), "rating rows")

# ---------- own earlier statewide results: both passes agree on every count except GA 2020 president's total
# (pass A has no write-in line; pass B's FEC figure includes 2,244 write-ins). Pass B is primary throughout: it used the Clerk of
# the House, the FEC and the NC certified abstract directly, while pass A reached the OH, AK and GA state files only through
# Internet Archive copies after the live sites blocked automated access. Pass A's state-file figures are recorded as the check.
# Peltola's final RCV round rests only on an archive copy, so it is not used.
PA = {(r["state"], r["contest"]): r for r in read(D / "passA" / "own_prior.csv")}
rows = []
for r in read(D / "passB" / "own_prior.csv"):
    a = PA[(r["state"], r["contest"])]
    diff = [f for f in ("dem_votes", "rep_votes", "total_votes") if a[f] != r[f]]
    r = dict(r, dem_votes_final_round="", rep_votes_final_round="",
             check=(f"state file ({a['source_name']}) identical counts" if not diff else
                    f"state file ({a['source_name']}) differs on {', '.join(diff)}: " + ", ".join(a[f] for f in diff) + " (no write-in line)"),
             check_url=a["source_url"])
    r["dem_margin_pct"] = f'{100 * (int(r["dem_votes"]) - int(r["rep_votes"])) / int(r["total_votes"]):.2f}'
    rows.append(r)
with open(D / "own_prior.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows:
    print(r["state"], r["contest"], r["year"], r["dem_margin_pct"], "|", r["check"][:90])
