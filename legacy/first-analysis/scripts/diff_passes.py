"""Compare two independent collection passes and run sanity checks.

Usage: python3 scripts/diff_passes.py data/passA data/passB
"""
import csv
import sys
from pathlib import Path

NUM = ["dem_votes", "rep_votes", "total_votes", "dem_votes_final_round", "rep_votes_final_round"]
TXT = ["dem_candidate", "rep_candidate"]


def load(folder):
    rows = {}
    for f in sorted(Path(folder).glob("*.csv")):
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
                key = (r["state"], r["contest"], r["year"], r["election_type"])
                if key in rows:
                    print(f"  DUPLICATE in {folder}: {key}")
                rows[key] = r
    return rows


def num(v):
    v = v.replace(",", "")
    return int(v) if v.lstrip("-").isdigit() else None


def surname(name):
    return name.split()[-1].lower().strip(".,") if name else ""


def sanity(tag, key, r):
    d, rp, t = num(r["dem_votes"]), num(r["rep_votes"]), num(r["total_votes"])
    if None in (d, rp, t):
        print(f"  [{tag}] {key}: missing count(s) d={r['dem_votes']!r} r={r['rep_votes']!r} t={r['total_votes']!r}")
        return
    if d + rp > t:
        print(f"  [{tag}] {key}: dem+rep ({d + rp}) > total ({t})")
    if (d + rp) / t < 0.85:
        print(f"  [{tag}] {key}: dem+rep only {(d + rp) / t:.1%} of total — check (fine if strong 3rd party)")


def main(a_dir, b_dir):
    A, B = load(a_dir), load(b_dir)
    print("== Sanity checks ==")
    for tag, rows in (("A", A), ("B", B)):
        for k, r in sorted(rows.items()):
            sanity(tag, k, r)

    print("\n== Coverage ==")
    for k in sorted(set(A) - set(B)):
        print(f"  only in A: {k}")
    for k in sorted(set(B) - set(A)):
        print(f"  only in B: {k}")

    print("\n== Disagreements ==")
    agree = 0
    for k in sorted(set(A) & set(B)):
        a, b = A[k], B[k]
        diffs = []
        for c in TXT:
            if surname(a[c]) != surname(b[c]):
                diffs.append(f"{c}: {a[c]!r} vs {b[c]!r}")
        for c in NUM:
            x, y = num(a.get(c, "")), num(b.get(c, ""))
            if x != y:
                pct = f" ({abs(x - y) / max(x, y):.3%})" if x and y else ""
                diffs.append(f"{c}: {a.get(c)!r} vs {b.get(c)!r}{pct}")
        if diffs:
            print(f"  {k}  [A:{a['status']} | B:{b['status']}]")
            for d in diffs:
                print(f"      {d}")
        else:
            agree += 1
    print(f"\n{agree} rows identical on candidates and all counts; "
          f"{len(set(A) & set(B)) - agree} rows differ.")


if __name__ == "__main__":
    main(*sys.argv[1:3])
