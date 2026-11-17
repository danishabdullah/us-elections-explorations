"""Merge the verified collection passes into data/results.csv + data/sources.csv.

Primary row per contest:
  pres_2024  -> pass A (state official / certificate); checked against FEC (pass B)
  sen_prior  -> pass A (state official);               checked against FEC (pass B)
  sen_2026   -> official state feed (pass A) for NC, MN, NE, SC;
                AP feed (pass B) elsewhere; checked against DDHQ (pass C) and the other pass.
Every row's source_ids / checked_by point at rows in sources.csv.
Run: python3 scripts/build_final.py   (from the session folder)
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
OFFICIAL_2026 = {"NC", "MN", "NE", "SC"}

# Notes rewritten where a pass's note relied on a source we could not re-open, or on no source.
NOTE_OVERRIDES = {
    ("ME", "sen_2026"): (
        "First-choice counts; ranked-choice race but no RCV tabulation published, so final-round cells blank. "
        "Total = Jackson + Collins + six write-ins listed by AP (sum 707,000). DDHQ showed a slightly larger count "
        "(709,755 = DDHQ total 718,125 minus its 8,370 'Blank Votes' line). Jackson was not the primary winner: Graham Platner won "
        "the June primary, announced his exit July 8 and withdrew July 10, 2026; a party convention nominated Jackson "
        "on July 25, 2026 (566 of 571 delegates), per NPR (via WYSU) and ABC7. "
        "Maine SOS had not posted general-election results at retrieval."
    ),
    ("SC", "sen_2026"): (
        "Official SC Election Commission unofficial results, 2312/2312 precincts. Total = Andrews + Graham + "
        "Kasie Whitener (LIB) 23,583 + Mark Hackett (CON) 16,806 + write-ins 4,898. Republican spelled "
        "'Darline Graham' on the state's ballot listing. Per SC Public Radio (Aug 11 2026) she was appointed by "
        "Gov. Henry McMaster to complete the term of her late brother, Sen. Lindsey Graham; regular (Class II) election."
    ),
}


def read(p):
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh))


def key(r):
    return (r["state"], r["contest"], r["year"], r["election_type"])


def split_other(s):
    """'URL (desc); URL (desc)' -> [(url, desc)]"""
    out = []
    for part in re.split(r";\s*(?=https?://)", s or ""):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"(https?://\S+)\s*(.*)", part)
        if m:
            out.append((m.group(1), m.group(2).strip().strip("()")))
    return out


def margin(r):
    d, rp, t = int(r["dem_votes"]), int(r["rep_votes"]), int(r["total_votes"])
    return 100 * (d - rp) / t


class Sources:
    def __init__(self):
        self.rows, self.by_url = [], {}

    def add(self, url, publisher, desc, retrieved, used_for):
        if url in self.by_url:
            s = self.by_url[url]
            if used_for not in s["used_for"]:
                s["used_for"] += "; " + used_for
            return s["id"]
        sid = f"S{len(self.rows) + 1:03d}"
        s = dict(id=sid, publisher=publisher, description=desc, url=url,
                 retrieved=retrieved, used_for=used_for)
        self.rows.append(s)
        self.by_url[url] = s
        return sid


def main():
    A = {key(r): r for f in ("pres_2024", "sen_prior", "sen_2026") for r in read(D / "passA" / f"{f}.csv")}
    B = {key(r): r for f in ("pres_2024", "sen_prior", "sen_2026") for r in read(D / "passB" / f"{f}.csv")}
    C = {key(r): r for r in read(D / "passC" / "sen_2026.csv")}
    src = Sources()
    npr = src.add("https://wysu.org/npr-national-news/2026-07-25/democrats-in-maine-formally-nominate-troy-jackson-as-their-new-candidate-for-u-s-senate",
                  "NPR (via WYSU)", "Democrats in Maine formally nominate Troy Jackson as their new candidate for U.S. Senate (Jul 25 2026)",
                  "2026-11-07", "ME sen_2026: Jackson nominated by convention Jul 25 2026, 566 of 571 delegates")
    abc7 = src.add("https://abc7ny.com/post/maine-senate-candidates-democrats-choose-troy-jackson-new-nominee-face-susan-collins-graham-platner-withdraws/19574928/",
                   "ABC7 (AP)", "Maine Democrats choose Troy Jackson as new Senate nominee after Graham Platner withdraws",
                   "2026-11-07", "ME sen_2026: Platner withdrew Jul 10 2026")
    wgcu = src.add("https://www.wgcu.org/2026-08-11/in-south-carolina-sen-darline-graham-advances-to-a-gop-special-primary-runoff-for-u-s-senate",
                   "South Carolina Public Radio (via WGCU)", "Sen. Darline Graham advances to GOP special primary runoff (Aug 11 2026)",
                   "2026-11-07", "SC sen_2026: Darline Graham appointed to late brother's seat")
    DROP_OTHER = {"themainemonitor.org", "apnews.com/projects/elections-2026/south-carolina"}

    out = []
    order = ["sen_2026", "sen_prior", "pres_2024"]
    for k in sorted(A, key=lambda k: (order.index(k[1]), k[0], k[2])):
        state, contest = k[0], k[1]
        if contest == "sen_2026" and state not in OFFICIAL_2026:
            prim, checks = B[k], [("A", A[k]), ("C", C[k])]
        elif contest == "sen_2026":
            prim, checks = A[k], [("B", B[k]), ("C", C[k])]
        else:
            prim, checks = A[k], [("B", B[k])]

        tag = f"{state} {contest} {k[2]}"
        ids = [src.add(prim["source_url"], prim["source_name"], prim["source_name"],
                       prim.get("retrieved", ""), f"{tag}: vote counts")]
        for url, desc in split_other(prim.get("other_sources")):
            if any(d in url for d in DROP_OTHER):
                continue
            ids.append(src.add(url, url.split("/")[2], desc, prim.get("retrieved", ""), f"{tag}: {desc[:120]}"))
        if k[:2] == ("ME", "sen_2026"):
            ids += [npr, abc7]
        if k[:2] == ("SC", "sen_2026"):
            ids.append(wgcu)

        check_ids, check_notes = [], []
        pm = margin(prim)
        for _, c in checks:
            if c["source_url"] == prim["source_url"]:
                check_notes.append("second independent read of the same source agreed")
                continue
            cid = src.add(c["source_url"], c["source_name"], c["source_name"],
                          c.get("retrieved", "") or "2026-11-07", f"{tag}: cross-check")
            check_ids.append(cid)
            same = all(c[f] == prim[f] for f in ("dem_votes", "rep_votes", "total_votes"))
            if same:
                check_notes.append(f"{cid} identical counts")
            elif not c["total_votes"]:
                check_notes.append(
                    f"{cid} D {int(c['dem_votes']):,} / R {int(c['rep_votes']):,} / total not given "
                    f"({c.get('as_of') or c['status']})")
            else:
                check_notes.append(
                    f"{cid} D {int(c['dem_votes']):,} / R {int(c['rep_votes']):,} / total "
                    f"{int(c['total_votes']):,} (margin {margin(c):+.2f} vs {pm:+.2f}; {c.get('as_of') or c['status']})")

        notes = NOTE_OVERRIDES.get(k[:2], prim.get("notes", ""))
        out.append(dict(
            state=state, contest=contest, year=k[2], election_type=k[3],
            dem_candidate=prim["dem_candidate"], dem_party=prim["dem_party"], dem_votes=prim["dem_votes"],
            rep_candidate=prim["rep_candidate"], rep_votes=prim["rep_votes"], total_votes=prim["total_votes"],
            dem_margin_pct=f"{pm:.2f}",
            dem_votes_final_round=prim["dem_votes_final_round"], rep_votes_final_round=prim["rep_votes_final_round"],
            status=prim["status"], as_of=prim["as_of"],
            source_ids=";".join(dict.fromkeys(ids)), checked_by=";".join(check_ids),
            check_result=" | ".join(check_notes), notes=notes))

    with open(D / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    with open(D / "sources.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(src.rows[0]))
        w.writeheader()
        w.writerows(src.rows)
    print(f"{len(out)} result rows, {len(src.rows)} sources")


if __name__ == "__main__":
    main()
