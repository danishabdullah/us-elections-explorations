# Election results CSV schema

One row per (state, contest). Comma-separated, header row, quote fields containing commas.

| column | meaning |
|---|---|
| state | two-letter code |
| contest | `pres_2024`, `sen_2026`, or `sen_prior` (an earlier general election for the SAME Senate seat) |
| year | election year (e.g. 2020) |
| election_type | `regular`, `special`, `runoff` |
| dem_candidate | Democratic nominee, or the main anti-Republican candidate if there is no Democrat (e.g. an independent) |
| dem_party | `D` or `I` (or what the ballot says, e.g. `D-nominated independent`) |
| dem_votes | integer, no commas |
| rep_candidate | Republican nominee |
| rep_votes | integer, no commas |
| total_votes | all votes counted for that office (all candidates incl. write-ins); exclude blank/over votes |
| dem_votes_final_round | ranked-choice states only (ME, AK): final-round votes, else blank |
| rep_votes_final_round | ranked-choice states only, else blank |
| status | `certified`, `unofficial`, or `incomplete` |
| as_of | for unofficial/incomplete counts: timestamp or "% expected vote counted"; else blank |
| source_name | e.g. "Michigan Secretary of State" or "FEC Federal Elections 2020" |
| source_url | the exact page/PDF the numbers came from |
| retrieved | date/time (UTC if possible) you read the numbers from source_url |
| other_sources | `;`-separated URLs of any other page used for ANY value in the row (e.g. a nominee's name or spelling), each with a few words on what it supported |
| notes | anything unusual (RCV, no Democrat on ballot, nominee differs from expected, etc.). Every factual claim in notes must come from a cited source — no claims from memory. |

Citation rule: every value in a row must trace to a URL in `source_url` or `other_sources`. Wikipedia is never a source: if you find a fact there, open the source it cites, confirm it there, and cite that.

Vote counts are first-round / first-choice counts. Never estimate: leave a cell blank and explain in `notes` if you can't find it.
