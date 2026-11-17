# midterms-2026

Verified, cited election results for every U.S. Senate seat, 1976 to 2026, built to put the 2026 midterms in
historical context. Every value records where it came from and which independent collection produced it.

## Quick start

```bash
uv sync
uv run midterms build      # download (cached), load, reconcile, export
uv run midterms status     # coverage for the 35 seats up in 2026
uv run pytest
```

Requires Python 3.15 and [uv](https://docs.astral.sh/uv/).

## What's in it

| Data | Source | Coverage |
|---|---|---|
| Senate results | MIT Election Data and Science Lab, *U.S. Senate statewide 1976–2024* (Harvard Dataverse, doi:10.7910/DVN/PEJ5QU) | every general and runoff, all 100 seats |
| Presidential results by state | MIT Election Lab, *U.S. President 1976–2024* (doi:10.7910/DVN/42MVDX) | every state and DC |
| 2026 Senate results | reviewed collections in `data/manual/results/` | 16 of 35 seats so far |
| Candidates' earlier statewide races | reviewed collections | 6 candidates |
| Sabato's Crystal Ball ratings, 2026 | reviewed collections in `data/manual/ratings/` | 16 seats, full history |
| Candidate positions, 2026 | `data/manual/positions/` (coding scheme in `SCHEMA.md` there) | 16 candidates |

MIT's datasets are fetched in one go through the Dataverse API, which also supplies the latest version and each
file's MD5, checked on download. They are the primary source wherever they cover a contest. 2026 isn't in them yet:
MIT adds a cycle after states certify.

**House results are not downloaded.** Dataverse puts that file behind a guestbook, a form for a person to fill in,
so the fetcher stops there. Download `1976-2024-house.tab` by hand if you need it.

## Design

- **Seats, not states.** `seats.py` defines the 100 seats (state × class I/II/III). Every Senate contest is tied to
  the seat it filled. The calendar decides most of them: class I is up when `year % 6 == 2`, class II at `4`, class
  III at `0`, and a special fills whichever of the state's seats isn't regularly up. Specials the calendar can't
  place are pinned in `data/special_seats.json`, each with the vacancy it filled; the build refuses to load if one is
  missing.
- **Observations are never overwritten.** `results` and `totals` keep every collection's numbers as recorded.
  `reconcile.py` writes one row per contest to `contest_final`: the primary collection's numbers, the collections
  it was compared with, and whether they agree, with every difference spelled out in `notes`.
- **Primary source.** MIT's data when it has the contest, unless MIT marks it unofficial and a reviewed pass has
  certified counts (MIT's January 2021 Georgia runoffs predate certification). Otherwise the choice in
  `data/manual/primary.json`, then passA, passB, passC.
- **One definition of the total.** All valid votes for the office: candidates, write-ins and scattering. Blank,
  over- and under-votes are kept as rows (`party_simplified = 'NONVOTE'`) but left out. MIT's own `totalvotes`
  sometimes includes them; it's kept in the total's notes.
- **Margin.** (Democrat − Republican) ÷ total. Where no Democrat ran, the Democratic side is the leading
  non-Republican (e.g. an independent the party backed). Same-party generals (California and Washington top-two)
  have no margin.
- **Polite fetching.** `fetch.py` honors robots.txt, spaces requests per host, caches every download with its URL,
  time and SHA-256, and raises `Blocked` on 401/403/405/407/429/451, bot checks and guestbooks. Blocks are recorded,
  never worked around; only network errors and 5xx responses are retried.

### Fixes applied to MIT's data

- `stage` comes in five spellings (`gen`, `GEN`, `pre`, `runoff`, `GEN RUNOFF`); `pre` is a Georgia general that
  went to a runoff.
- Jan 2021 Georgia runoffs carry year 2021; they are placed in the 2020 cycle.
- Party labels: `party_detailed` beginning with DEMOCRAT or REPUBLICAN is relabelled by rule; the few rows with no
  label at all are fixed in `data/medsl_fixes.json`.
- Louisiana 2002 lists the November primary and December runoff as one contest; it is flagged in notes.
- Odd-year specials before 2021 (e.g. Massachusetts 2010 and 2013, New Jersey 2013, Alabama 2017) aren't in MIT's
  file.

## Adding data

Reviewed collections are CSVs in `data/manual/results/<collection>.csv`; the columns are listed in
`src/midterms/sources/manual.py`. Collect each contest twice, independently, from different sources (passA, passB),
then rebuild. Disagreements show up in `contest_final.agreement` and in `midterms status`.

## Layout

```
src/midterms/      seats, models, schema, db, fetch, reconcile, cli, sources/{medsl,manual}
data/manual/       reviewed collections (committed)
data/export/       one JSON per seat with its full history, plus president.json (committed)
data/raw/          cached downloads (ignored)
data/midterms.sqlite   the database (ignored; rebuilt by `midterms build`)
legacy/first-analysis/ the original 16-race page, its scripts and data
scripts/convert_session_data.py  how data/manual was produced from that analysis
```
