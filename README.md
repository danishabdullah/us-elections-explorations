# midterms-2026

Verified, cited election results for every U.S. Senate seat, 1976 to 2026, plus every presidential and House race
since 1976, built to put the 2026 midterms in historical context. Every value records where it came from and which
independent collection produced it.

## Quick start

```bash
uv sync
uv run midterms build      # load the committed sources, check Dataverse for newer versions, reconcile, export
uv run midterms status     # coverage for the 35 seats up in 2026
uv run pytest
```

Requires Python 3.15 and [uv](https://docs.astral.sh/uv/).

## What's in it

| Data | Source | Coverage |
|---|---|---|
| Senate results | MIT Election Data and Science Lab, *U.S. Senate statewide 1976–2024* (Harvard Dataverse, doi:10.7910/DVN/PEJ5QU) | every general and runoff, all 100 seats |
| Presidential results by state | MIT Election Lab, *U.S. President 1976–2024* (doi:10.7910/DVN/42MVDX) | every state and DC |
| House results by district | MIT Election Lab, *U.S. House 1976–2024* (doi:10.7910/DVN/IG0UN2) | every district, generals and runoffs |
| 2026 Senate results | reviewed collections in `data/manual/results/` | 16 of 35 seats so far |
| Candidates' earlier statewide races | reviewed collections | 6 candidates |
| Sabato's Crystal Ball ratings, 2026 | reviewed collections in `data/manual/ratings/` | 16 seats, full history |
| Candidate positions, 2026 | `data/manual/positions/2026/`: every collection pass, verifier re-checks, rulings and reconciled values; coding scheme and its dated revisions in `SCHEMA.md` there | 16 candidates, 23 indicators |
| Candidate facts, 2026 | `data/manual/candidates/2026.csv`: Sanders endorsement date and stage, contested primary | 16 candidates |

MIT's datasets are fetched in one go through the Dataverse API, which also supplies the latest version and each
file's MD5, checked on download. They are the primary source wherever they cover a contest. 2026 isn't in them yet:
MIT adds a cycle after states certify.

**The source files are committed** in `data/raw/dataverse.harvard.edu/`, named by dataset version, each with a
`.meta.json` recording its URL, retrieval time and SHA-256. A build works offline from them; online, it checks
Dataverse for a newer version and downloads only if one exists.

**House guestbook.** Dataverse asks for a guestbook response (name, email, institution, position) before releasing
the House file. The fetcher answers it through Dataverse's documented access API, using details you put in
`guestbook.local.json` at the repo root (git-ignored):

```json
{"name": "...", "email": "...", "institution": "...", "position": "..."}
```

Without that file the House download is skipped with a message; the committed copy is still used.

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
- The House file writes booleans as TRUE/FALSE/NA, marks runoffs with `runoff=TRUE`, and uses -1 where no votes
  were tallied (Florida doesn't print unopposed races); those contests are kept with a note and no margin.
- Odd-year specials before 2021 (e.g. Massachusetts 2010 and 2013, New Jersey 2013, Alabama 2017) aren't in MIT's
  file.

## Adding data

Reviewed collections are CSVs in `data/manual/results/<collection>.csv`; the columns are listed in
`src/midterms/sources/manual.py`. Collect each contest twice, independently, from different sources (passA, passB),
then rebuild. Disagreements show up in `contest_final.agreement` and in `midterms status`.

### Positions

Each position was collected at least twice, independently, then re-checked at the sources by a separate verifier.
The database keeps all of it: `positions` has one row per candidate, indicator and collection (`positions_A`,
`messaging_B`, `ig_stance_final`, ..., and `reconciled` for the final value); `position_evidence` holds the dated
quotes behind assessed values; `position_checks` holds each re-check (confirmed, changed or unresolved);
`rulings` holds values changed under a revised coding rule, with the reason. Old positions are kept; the coding
scheme says the latest 2025–26 position decides and older evidence stands, marked with its date, when nothing
newer exists.

## Layout

```
src/midterms/      seats, models, schema, db, fetch, reconcile, cli, sources/{medsl,manual}
data/manual/       reviewed collections (committed)
data/export/positions/ one JSON per cycle: per candidate and indicator, the final value with evidence, each pass,
                   the re-checks and any ruling (committed)
data/export/       one JSON per seat with its full history, plus president.json (committed)
data/raw/          MIT's source files and Dataverse metadata, with download records (committed)
data/export/house/ one JSON per state, House results by district (committed)
data/midterms.sqlite   the database (ignored; rebuilt by `midterms build`)
legacy/first-analysis/ the original 16-race page, its scripts and data
scripts/convert_session_data.py  how data/manual was produced from that analysis
```
