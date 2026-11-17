"""Build charts/senate_2026.html (self-contained, no external requests) from data/results.csv.

Run: python3 scripts/build_charts.py   (from the session folder)
"""
import csv
import json
import random
import statistics as st_
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SANDERS = {"ME", "MN", "MA", "MI", "FL"}  # endorsed candidates highlighted in the original chart
# Prior race used for the same-seat comparison: the last November general for this seat.
PRIOR_PICK = {"GA": ("2020", "regular"), "NE": ("2024", "special")}

rows = list(csv.DictReader(open(ROOT / "data" / "results.csv", newline="")))
by = {}
for r in rows:
    by.setdefault(r["state"], {})[(r["contest"], r["year"], r["election_type"])] = r

data = []
for st, d in sorted(by.items()):
    s26 = next(v for k, v in d.items() if k[0] == "sen_2026")
    pres = next(v for k, v in d.items() if k[0] == "pres_2024")
    priors = {k: v for k, v in d.items() if k[0] == "sen_prior"}
    pk = PRIOR_PICK.get(st)
    prior = priors[("sen_prior",) + pk] if pk else next(iter(priors.values()))
    data.append(dict(
        st=st, sanders=st in SANDERS,
        cand=s26["dem_candidate"], party=("I" if "independent" in s26["dem_party"].lower() else "D"), party_full=s26["dem_party"], opp=s26["rep_candidate"],
        m26=float(s26["dem_margin_pct"]), status=s26["status"], as_of=s26["as_of"],
        type26=s26["election_type"],
        harris=float(pres["dem_margin_pct"]),
        prior=float(prior["dem_margin_pct"]), prior_year=prior["year"] + (" special" if prior["election_type"] == "special" else ""),
        prior_cand=prior["dem_candidate"], prior_opp=prior["rep_candidate"],
    ))

# ---------- alignment (verified codes) and selection
AL = ROOT / "data" / "alignment"
sel = {r["state"]: r for r in csv.DictReader(open(AL / "selection.csv", newline=""))}
scores = {r["state"]: r for r in csv.DictReader(open(AL / "scores.csv", newline=""))}
codes = {}
for r in csv.DictReader(open(AL / "alignment_final.csv", newline="")):
    ev = r["verify_evidence"] or r["evidence"]
    url = r["verify_source"] or r["source_url"]
    if url and not url.startswith("http"):
        url = ""
    codes.setdefault(r["state"], {})[r["indicator"]] = dict(
        v=r["final_value"].strip().lower(), ev=ev[:340], url=url.split(" ")[0].strip(" ;"),
        note=("" if url else r["notes"][:200]))
for d in data:
    s_ = sel[d["st"]]
    sc = scores[d["st"]]
    d.update(
        codes=codes[d["st"]],
        policy=float(sc["policy_yes"]), orgs=int(sc["orgs_yes"]), message=int(sc["message_yes"]), ig=int(sc["israel_gaza_yes"]),
        policy_unclear=int(sc["policy_unclear"]), ig_unclear=int(sc["israel_gaza_unclear"]), message_unclear=int(sc["message_unclear"]),
        endorse_date=s_["sanders_endorse_date"], endorse_stage=s_["sanders_endorse_stage"],
        rating_at=s_["rating_at_endorse"], rating_final=s_["rating_final"],
    )

# ---------- Crystal Ball rating history (reconciled from two passes): [[date, rating], ...] in order
hist = {}
for r in csv.DictReader(open(AL / "rating_history.csv", newline="")):
    hist.setdefault(r["state"], []).append([r["date"], r["rating"]])
for d in data:
    d["ratings"] = sorted(hist[d["st"]], key=lambda x: x[0])

# ---------- each candidate's own earlier statewide race, set against their party's presidential nominee in that state that year
own = {(r["state"], r["contest"]): r for r in csv.DictReader(open(ROOT / "data" / "own_prior.csv", newline=""))}
OWN = {  # state: (earlier race, label, presidential row)
    "MA": (by["MA"][("sen_prior", "2020", "regular")], "Senate 2020", own[("MA", "pres_2020")], "Biden"),
    "GA": (by["GA"][("sen_prior", "2020", "regular")], "Senate 2020", own[("GA", "pres_2020")], "Biden"),
    "NC": (own[("NC", "own_prior")], "Governor 2020", own[("NC", "pres_2020")], "Biden"),
    "OH": (own[("OH", "own_prior")], "Senate 2024", by["OH"][("pres_2024", "2024", "regular")], "Harris"),
    "NE": (own[("NE", "own_prior")], "Senate 2024", by["NE"][("pres_2024", "2024", "regular")], "Harris"),
    "AK": (own[("AK", "own_prior")], "House 2024, statewide", by["AK"][("pres_2024", "2024", "regular")], "Harris"),
}
for d in data:
    if d["st"] in OWN:
        race, label, pres_, who = OWN[d["st"]]
        d["own"] = dict(label=label, m=float(race["dem_margin_pct"]), top=float(pres_["dem_margin_pct"]), who=who,
                        opp=race["rep_candidate"])

# ---------- alignment vs. performance: correlations with permutation p and bootstrap 90% interval
def corr(u, v):
    mu, mv = st_.mean(u), st_.mean(v)
    den = (sum((p - mu) ** 2 for p in u) * sum((q - mv) ** 2 for q in v)) ** 0.5
    return sum((p - mu) * (q - mv) for p, q in zip(u, v)) / den if den else 0.0

xs = [d["harris"] for d in data]; ys = [d["m26"] for d in data]
mx, my = st_.mean(xs), st_.mean(ys)
B = sum((a - mx) * (c - my) for a, c in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs); A = my - B * mx
for d in data:
    d["_resid"] = d["m26"] - (A + B * d["harris"])
    d["_swing"] = d["m26"] - d["prior"]; d["_grp"] = "D" if d["prior"] > 0 else "R"
med = {g: st_.median([d["_swing"] for d in data if d["_grp"] == g]) for g in "DR"}
for d in data:
    d["_vp"] = d["_swing"] - med[d["_grp"]]

def test(dim, outcome, subset):
    rng = random.Random(f"{dim}-{outcome}-{len(subset)}")
    u = [float(d[dim]) for d in subset]; v = [d[outcome] for d in subset]
    r = corr(u, v)
    p = sum(abs(corr(u, rng.sample(v, len(v)))) >= abs(r) - 1e-12 for _ in range(20000)) / 20000
    bs = []
    for _ in range(5000):
        idx = [rng.randrange(len(u)) for _ in u]
        uu = [u[i] for i in idx]
        if len(set(uu)) > 1:
            bs.append(corr(uu, [v[i] for i in idx]))
    bs.sort()
    return dict(r=round(r, 2), p=round(p, 2), lo=round(bs[int(.05 * len(bs))], 2), hi=round(bs[int(.95 * len(bs)) - 1], 2), n=len(u))

others = [d for d in data if not d["sanders"]]
STATS = {}
for dim in ("policy", "ig", "message", "orgs"):
    for out, key in (("_resid", "resid"), ("_vp", "peers")):
        STATS[f"{dim}|{key}|all"] = test(dim, out, data)
        STATS[f"{dim}|{key}|others"] = test(dim, out, others)
for d in data:
    for k in ("_resid", "_swing", "_grp", "_vp"):
        d.pop(k)

html = (ROOT / "scripts" / "charts_template.html").read_text().replace("/*DATA*/[]", json.dumps(data)).replace("/*STATS*/{}", json.dumps(STATS))
out = ROOT / "charts" / "senate_2026.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html)
print(f"wrote {out.relative_to(ROOT)} with {len(data)} states")
