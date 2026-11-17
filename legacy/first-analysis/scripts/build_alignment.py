"""Merge coded alignment data + verifier corrections into final files and pre-registered scores.

Inputs  (data/alignment/): positions_*.csv, messaging_*.csv, israel_gaza_*.csv, selection.csv, verify_*.csv
Outputs (data/alignment/): alignment_final.csv  (one row per candidate x indicator, final value + provenance)
                           scores.csv           (one row per state, pre-registered scores from SCHEMA.md)
Run: python3 scripts/build_alignment.py   (from the session folder)
"""
import csv
import glob
from collections import defaultdict
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data" / "alignment"

DIMENSIONS = {
    # gnd stays coded but is not scored (decided after collection): a 2019-20 label that 14 of 16 candidates
    # never mentioned either way in 2026, so it mainly recorded that Markey co-authored it.
    # m4a / min_wage_17plus replaced by graded health_level / min_wage_level (SCHEMA.md revision); old codes kept for reference.
    "policy": ["health_level", "min_wage_level", "no_corp_pac", "end_citizens_united"],
    # Justice Democrats and CPC PAC stay coded in alignment_final.csv but are not scored: both endorsed only House candidates in 2026.
    "orgs": ["endorsed_our_revolution", "endorsed_wfp", "endorsed_pccc"],
    "message": ["msg_affordability", "msg_anti_oligarchy", "msg_anti_corporate"],
    # Israel/Gaza redo (SCHEMA.md): one assessed stance 0-4, reconciled from two assessors (ig_stance_final.csv).
    # The old item codes (ceasefire_call, condition_aid, genocide_term, aipac_reject) stay in alignment_final.csv for reference.
    "israel_gaza": ["ig_stance"],
}
CONTEXT = ["sanders_endorsed", "cpc_member", "aipac_backed"]
# graded values: full Sanders position = 1, partial step toward it = 0.5
POINTS = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "yes": 1, "m4a": 1, "17plus": 1, "public_option": 0.5, "raise": 0.5}
UNKNOWN = {"unclear", "", "unknown"}


def read(p):
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    coded = {}
    for pat in ("positions_*.csv", "messaging_*.csv", "israel_gaza_*.csv"):
        for f in sorted(glob.glob(str(D / pat))):
            for r in read(f):
                k = (r["state"], r["indicator"])
                if k in coded:
                    print("DUPLICATE", k, f)
                r["_file"] = Path(f).name
                r["final_value"], r["verify_status"], r["verify_source"], r["verify_note"], r["verify_evidence"] = r["value"], "not yet verified", "", "", ""
                coded[k] = r

    # verifier corrections
    for f in sorted(glob.glob(str(D / "verify_*.csv"))):
        for v in read(f):
            ind = v.get("indicator") or v.get("indicator_or_field")
            k = (v["state"], ind)
            if k not in coded:
                continue  # selection.csv fields are handled below
            r = coded[k]
            st = (v.get("status") or "").strip().lower()
            r["verify_status"] = st or "checked"
            r["verify_source"] = v.get("source_url", "")
            r["verify_note"] = (v.get("evidence", "") + " " + v.get("notes", "")).strip()
            r["verify_evidence"] = v.get("evidence", "").strip()
            # "unresolved" = the verifier could not confirm the coded value under the uniform rule;
            # the value it could support (usually "unclear") stands, so no unconfirmed "yes" survives.
            if st in ("changed", "unresolved") and v.get("verified_value"):
                r["final_value"] = v["verified_value"].strip().lower()

    # Israel aid revision (SCHEMA.md): the latest clear 2025-26 campaign statement decides; votes are context and
    # decide only when there is no clear statement (then the most recent vote counts, as already coded from votes).
    stp = D / "israel_aid_statements.csv"
    if stp.exists():
        for sr in read(stp):
            k = (sr["state"], "condition_aid")
            if k not in coded:
                continue
            r = coded[k]
            votes = r["verify_evidence"] or r["evidence"]
            sv = sr["statement_value"].strip().lower()
            said = f'{sr["source_date"]}: {sr["evidence"]}' if sv != "unclear" else "No clear position in 2025-26 statements"
            if sv in ("yes", "no"):
                r["final_value"] = sv
                r["verify_source"] = sr["source_url"]
                r["verify_evidence"] = f"Campaign position ({said}). Record: {votes}"
            else:
                r["verify_evidence"] = f"{said}; decided by most recent vote. Record: {votes}"
            r["verify_status"] = "statement checked"
            r["verify_note"] = (r["verify_note"] + " | 2025-26 statement: " + sr["evidence"] + " " + sr["notes"]).strip()

    # graded health / wage items: reconciled from two independent passes (scripts/reconcile_health_wage.py)
    hw = D / "health_wage_final.csv"
    if hw.exists():
        for r in read(hw):
            r["_file"] = hw.name
            r["final_value"] = r["value"].strip().lower()
            r.setdefault("verify_status", "two passes reconciled")
            r["verify_source"], r["verify_note"] = "", r.get("notes", "")
            r["verify_evidence"] = r["evidence"] + (f' (figure: {r["figure"]})' if r.get("figure") else "")
            coded[(r["state"], r["indicator"])] = r

    igp = D / "ig_stance_final.csv"
    if igp.exists():
        for r in read(igp):
            ev = " · ".join(f'{r[f"date_{i}"]}: {r[f"evidence_{i}"]}' for i in range(1, 5) if r.get(f"evidence_{i}"))
            coded[(r["state"], "ig_stance")] = dict(
                state=r["state"], candidate=r["candidate"], indicator="ig_stance", value=r["stance"], final_value=r["stance"].strip().lower(),
                verify_status=r.get("verify_status", ""), evidence=r["rationale"], source_url=r["url_1"], source_date=r["date_1"],
                verify_source=r["url_1"], verify_evidence=r["rationale"] + (" | " + ev if ev else ""), verify_note=r.get("notes", ""),
                notes=r.get("notes", ""), _file=igp.name)

    # latest-position rule (SCHEMA.md): 2025-26 re-search for other items that rested on older evidence
    rp2 = D / "health_wage_recent.csv"
    if rp2.exists():
        for n in read(rp2):
            k = (n["state"], n["indicator"])
            if n["indicator"] in ("health_level", "min_wage_level") or k not in coded:
                continue
            r = coded[k]
            val = n["value"].strip().lower()
            if val == "unclear":
                r["verify_status"] = "dated: no 2025-26 position found"
                r["verify_evidence"] = f'As of {str(r.get("source_date", ""))[:4] or "earlier"}: ' + (r.get("verify_evidence") or r.get("evidence", "")) + " (no 2025-26 statement found)"
                continue
            old = f'last known {r["final_value"]} ({r.get("source_date", "")}: {(r.get("verify_evidence") or r.get("evidence", ""))[:160]})'
            r["final_value"], r["verify_status"], r["verify_source"] = val, "2025-26 re-search", n["source_url"]
            r["verify_evidence"] = (n["notes"] + " | " if n["indicator"] == "ig_stance" else "") + (n["evidence"] or "No 2025-26 position found") + f" (earlier: {old})"
            r["verify_note"] = "RECENCY: " + n["notes"]

    # author-directed rule revisions, one row per changed value with its reason (data/alignment/rulings.csv)
    rp = D / "rulings.csv"
    if rp.exists():
        for ru in read(rp):
            r = coded[(ru["state"], ru["indicator"])]
            r["final_value"] = ru["value"].strip().lower()
            r["verify_status"] = "revised rule"
            r["verify_evidence"] = (r["verify_evidence"] or r["evidence"]).replace("; no ceasefire call found", "").replace("the word ceasefire does not appear", "the word ceasefire does not appear, but the demand is stronger")
            r["verify_note"] = (ru["reason"] + " | " + r["verify_note"]).strip(" |")

    out = sorted(coded.values(), key=lambda r: (r["state"], r["indicator"]))
    cols = ["state", "candidate", "indicator", "final_value", "value", "verify_status", "evidence", "source_publisher",
            "source_url", "source_date", "verify_source", "verify_evidence", "verify_note", "notes", "_file"]
    with open(D / "alignment_final.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)

    sel = {r["state"]: r for r in read(D / "selection.csv")}
    by = defaultdict(dict)
    for r in out:
        by[r["state"]][r["indicator"]] = r["final_value"].strip().lower()
    rows = []
    for st, vals in sorted(by.items()):
        row = {"state": st, "candidate": sel.get(st, {}).get("candidate", "")}
        for dim, inds in DIMENSIONS.items():
            pts = sum(POINTS.get(vals.get(i, ""), 0) for i in inds)
            row[f"{dim}_yes"] = int(pts) if pts == int(pts) else pts
            row[f"{dim}_unclear"] = sum(vals.get(i, "unclear") in UNKNOWN for i in inds)
            row[f"{dim}_n"] = len(inds)
            missing = [i for i in inds if i not in vals]
            if missing:
                row[f"{dim}_missing"] = ";".join(missing)
        row["populist_index"] = row["policy_yes"] + row["message_yes"]
        for c in CONTEXT:
            row[c] = vals.get(c, "")
        s = sel.get(st, {})
        for c in ("sanders_endorse_date", "sanders_endorse_stage", "rating_at_endorse", "rating_final", "contested_primary"):
            row[c] = s.get(c, "")
        rows.append(row)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(D / "scores.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(out)} coded values, {len(rows)} states")
    for r in rows:
        print(f"{r['state']} {r['candidate'][:18]:18} S={r['sanders_endorsed']:4} policy {r['policy_yes']}/4 (?{r['policy_unclear']}) "
              f"orgs {r['orgs_yes']}/3 msg {r['message_yes']}/3 (?{r['message_unclear']}) IG {r['israel_gaza_yes']}/4 (?{r['israel_gaza_unclear']}) "
              f"aipac_backed={r['aipac_backed']} rating_final={r['rating_final']}")


if __name__ == "__main__":
    main()
