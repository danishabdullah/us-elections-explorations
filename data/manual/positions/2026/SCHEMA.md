# Alignment and selection data: coding scheme (fixed before collection)

Purpose: test two objections to "Sanders-endorsed vs. not" comparisons.
(a) Selection: did Sanders endorse in races that were harder or more competitive?
(b) Alignment: do non-endorsed candidates share Sanders's agenda, and does alignment (not the endorsement label) track performance?

## File 1: `positions_<group>.csv`: one row per (candidate, indicator)

Columns: `state, candidate, indicator, value, evidence, source_publisher, source_url, source_date, retrieved, notes`

- `value`: `yes`, `no`, or `unclear`. `no` needs evidence of the opposite position, or a candidate statement rejecting it. If you can find no statement either way after a real search, use `unclear` and say what you searched in `notes`.
- `evidence`: a short paraphrase, or a direct quote under 15 words.
- `source_date`: when the statement was made or published. The candidate's position as of the 2026 campaign counts; older statements are fine if not contradicted later (note the date).

Indicators (fixed list; code every one for every candidate):

| indicator | yes means |
|---|---|
| `sanders_endorsed` | Bernie Sanders endorsed this candidate for the 2026 Senate race (primary or general). Give the date. |
| `m4a` | Supports Medicare for All / single-payer national health insurance (not just a public option). |
| `no_corp_pac` | Has pledged not to take corporate PAC money. |
| `gnd` | Supports the Green New Deal by name. |
| `min_wage_17plus` | Supports a federal minimum wage of $17/hour or higher. |
| `end_citizens_united` | Supports overturning Citizens United (constitutional amendment or equivalent). |
| `endorsed_our_revolution` | Endorsed by Our Revolution (national or a state chapter, say which) for this race. |
| `endorsed_wfp` | Endorsed by the Working Families Party (national or state) for this race. |
| `endorsed_justice_dems` | Endorsed by Justice Democrats for this race. |
| `endorsed_pccc` | Endorsed by the Progressive Change Campaign Committee for this race. |
| `endorsed_cpc_pac` | Endorsed by the Congressional Progressive Caucus PAC for this race. |
| `cpc_member` | Is or was a member of the Congressional Progressive Caucus. Use `n/a` in `value` if never in the U.S. House. |

Pre-registered scores (computed later, not by collectors):
- policy score = count of `yes` among m4a, no_corp_pac, gnd, min_wage_17plus, end_citizens_united (0–5)
- progressive-org score = count of `yes` among the five `endorsed_*` items (0–5)

## File 2: `selection.csv`: one row per state (16)

Columns: `state, candidate, sanders_endorse_date, sanders_endorse_stage, rating_at_endorse, rating_at_endorse_source_url, rating_final, rating_final_date, rating_final_source_url, contested_primary, primary_result_note, source_notes, retrieved`

- `sanders_endorse_stage`: `primary` (before the candidate won the nomination) or `general`.
- Ratings: use one rater consistently for all 16. Prefer Sabato's Crystal Ball (centerforpolitics.org), which is free. Use the 7-point scale wording (Safe/Likely/Lean/Toss-up). `rating_at_endorse` is filled only for endorsed candidates: the rating in effect on the endorsement date. `rating_final` is the last rating before Nov 3 2026, for all 16.
- `contested_primary`: did the nominee face a serious Democratic primary? (yes/no, with source).

## Rules for everyone
- Cite a URL for every non-blank value. Wikipedia is never a source: use it only to find leads, then open and cite the source it points to.
- Prefer primary sources: the candidate's campaign site, the endorsing group's own announcement or endorsement page, Sanders's own site or official accounts, and the rater's own page. Reputable news is fine when it reports the statement directly.
- Never fill a value from memory. Write rows to the CSV as you go, not all at the end.

## File 3: `messaging_<group>.csv`: campaign message (added 2026-11-07, before collection)

Same columns as File 1. Three indicators, coded for every candidate:

| indicator | yes means |
|---|---|
| `msg_affordability` | Cost of living / affordability is a headline theme: the first or top-listed issue on the campaign site, the core of a closing message, or described as the campaign's central theme in reporting. Merely mentioning prices is not enough. |
| `msg_anti_oligarchy` | The candidate frames the race against "oligarchs", "oligarchy", "billionaires", or "the billionaire class" (concentrated wealth or power as the adversary) in their own speeches, ads, posts or site. |
| `msg_anti_corporate` | The candidate names corporations or corporate power as an adversary in their own words: e.g. corporate greed, price gouging by big companies, "corporate PACs" or monopolies as a central attack. |

- `no` means the candidate's main messaging was demonstrably elsewhere (cite their headline themes); `unclear` means you couldn't find enough.
- Evidence must be the candidate's own words (site, ad, speech, post) or reporting that quotes or describes them directly. Quotes under 15 words.

Pre-registered: message score = count of `yes` among the three (0–3). Populist-agenda index = policy score + message score (0–8).

## File 4: `israel_gaza_<group>.csv`: Israel / Gaza positions (added 2026-11-07, before collection)

Same columns as File 1. Coded for every candidate. The aim is to measure distance from Sanders's own stance (he led the Senate resolutions to block arms sales to Israel), not to judge the positions.

| indicator | yes means |
|---|---|
| `ceasefire_call` | Publicly called for a ceasefire in Gaza (give the earliest date found). |
| `condition_aid` | Supports conditioning, restricting or blocking U.S. military aid or arms sales to Israel. For sitting senators, their votes on Sanders's joint resolutions of disapproval (Nov 2024, Apr 2025, Jul 2025) decide this: record the votes in `evidence`. |
| `genocide_term` | Has described Israel's conduct in Gaza as genocide in their own words. |
| `aipac_reject` | Publicly pledged or stated they won't accept AIPAC or AIPAC-affiliated PAC money/support. |
| `aipac_backed` | Context, not scored: endorsed by AIPAC or supported by AIPAC / United Democracy Project spending in the 2026 cycle (FEC independent-expenditure records or AIPAC's own endorsement list). |

- `no` needs evidence of the opposite position (e.g. a statement opposing conditions, a vote against the resolutions, a stated rejection of the term). Otherwise `unclear`.
- Pre-registered: Israel/Gaza score = count of `yes` among ceasefire_call, condition_aid, genocide_term, aipac_reject (0–4). `aipac_backed` is reported alongside but not scored.

## Verification conventions (added after collection of Files 1–2, applied uniformly)
- Endorsement indicators: `no` = the candidate is absent from the group's own published 2026 endorsement list, checked in full (all pages / "view more"), and no news report of an endorsement exists. Record the list URL. This is the standard for all `endorsed_*` items and `sanders_endorsed`.
- Policy `no` requires the candidate's own stated alternative or rejection made in or after 2023 (e.g. "public option instead of Medicare for All"), or a vote against. Older-only or third-party claims (opposition research, partisan sites) → `unclear`.
- Policy `yes` requires the candidate's own words or a vote/cosponsorship; opposition claims alone never make a `yes`.

## Messaging: uniform decision rules for verification (fixed 2026-11-07 after collectors applied different bars)
- `msg_affordability` = yes if ANY of: (1) cost of living is the top-listed issue on the campaign site; (2) nonpartisan reporting describes it as the candidate's central, main, or closing theme; (3) the candidate's own closing ads or closing speeches centered on it. Otherwise `no` if their headline themes were demonstrably elsewhere and none of (1)–(3) holds; `unclear` if not enough evidence.
- `msg_anti_oligarchy` = yes if, in the 2025–26 campaign, the candidate in their own words (site, ad, speech, debate, post, or reputable reporting quoting them directly) framed billionaires / oligarchs / the billionaire class as an adversary or as the side the opponent or system serves. A tax-policy plank alone ("repeal tax breaks for billionaires") does not qualify. One clear instance suffices.
- `msg_anti_corporate` = yes if, in the 2025–26 campaign, the candidate in their own words named corporations, corporate greed, price gouging, monopolies, or corporate PACs as an adversary. Ads run by outside groups don't count.

## Israel/Gaza: uniform decision rules for verification (fixed 2026-11-07, after collection, before verification)
- Own words: the candidate's own statement, post, ad, site, vote, or an on-record statement by their campaign spokesperson. Reporting that the candidate "calls it X" without quoting them or their campaign → `unclear`.
- `condition_aid` for senators with votes on the Sanders resolutions of disapproval: `yes` if they voted Yea on at least one; `no` if Nay on all. Always record the tally (e.g. "Yea 3 of 7") in `evidence`; the page will show the tally, not just yes/no. For House members, a recorded vote for or against restricting/conditioning arms to Israel decides it the same way.
- `ceasefire_call` = yes only for a call for a ceasefire (temporary or permanent) while fighting was ongoing, in own words or a letter they signed. Hoping an existing ceasefire holds → `unclear`.
- `genocide_term` = no if they rejected the term in own words; yes if they used it in own words (incl. campaign site text); otherwise `unclear`.
- `aipac_reject` = yes for an explicit statement that they won't take / don't take AIPAC or UDP money or support (own words). Refusing all super PAC money counts only if they said so in a way that covers UDP.
- `aipac_backed` (context): yes if AIPAC endorsed them for this race or UDP filed independent expenditures supporting them (FEC); `no` if FEC shows no UDP support and no endorsement report exists; note opposition spending separately.

## Clarification (applied uniformly at verification)
- `end_citizens_united` = yes when the candidate states the goal of overturning/reversing the decision itself (by amendment or legislation). Mitigating its effects only ("reverse the impact", disclosure, super PAC limits) → `unclear`.

## Revision: Israel aid position (2026-11-07, after verification, at the author's direction)
- `condition_aid` is decided by the candidate's **latest clear 2025–26 campaign position** (own words, pledge, or a named on-record campaign spokesperson). Positions evolve; the 2026 campaign promise is what voters were offered.
- Congressional votes (Sanders resolutions of disapproval; House votes on restricting arms) are shown as context with the full tally. They decide the value only when the candidate made no clear 2025–26 statement, and then the most recent vote counts.
- When a 2025–26 statement and an older vote conflict, the statement decides and the page shows both.

## Revision: graded health-care and minimum-wage items (2026-11-07, after collection, at the author's direction)
Why: `m4a` and `min_wage_17plus` measured agreement with Sanders's exact bills, not direction, and most candidates were "unclear" because they named no single-payer stance or no wage figure. They are replaced in the policy score by two graded items (the old codes stay in alignment_final.csv for reference).

| indicator | values |
|---|---|
| `health_level` | `m4a` = supports Medicare for All / single-payer; `public_option` = supports a public option, Medicare buy-in, or lowering the Medicare age, but not single-payer; `neither` = own words defending the current system or rejecting both; `unclear` = nothing found. |
| `min_wage_level` | `17plus` = supports a federal minimum wage of $17/hour or more (any figure ≥ $17); `raise` = supports raising the federal minimum wage with a lower figure, or with no figure, or by indexing to inflation; `no` = own words opposing a federal increase; `unclear` = nothing found. Record the figure in `figure` when one is given. |

- Latest clear position wins; prefer 2025–26 campaign statements, accept 2023+; older statements only if nothing newer exists (note the date).
- Own words, site, vote/cosponsorship, or a named campaign spokesperson. Opposition research never decides.
- Score: `m4a` / `17plus` = 1; `public_option` / `raise` = 0.5; else 0. Policy score = health + wage + no_corp_pac + end_citizens_united (0–4).

## Revision: `ceasefire_call` (2026-11-07, after verification, at the author's direction)
The verification rule tested for the word "ceasefire" and required the call to predate the Oct 2025 ceasefire. That misread stronger demands: "End the genocide in Gaza" calls for the war to stop in stronger terms than "ceasefire".
- New definition: `ceasefire_call` = yes if, in own words, the candidate called for Israel's military campaign in Gaza to stop: a ceasefire, an end to the war, or an end to the genocide. No timing requirement.
- Hoping an existing ceasefire holds, or describing others' ceasefire efforts, is still `unclear`: it is not a demand.
- Recoded under this rule (rulings.csv): ME Jackson (site heading "End the genocide in Gaza") and MN Flanagan (site: peace "requires a lasting ceasefire"). No other candidate's evidence changes value.

## Revision: new item `condemned_conduct` (2026-11-07, at the author's direction)
Why: the four Israel/Gaza items test specific demands and terms. They miss candidates who condemned how Israel waged the war without using those terms (e.g. Talarico, MSNBC Oct 2025: "God is screaming at all of us in Gaza", condemning Netanyahu's use of hunger as a weapon).

| indicator | yes means |
|---|---|
| `condemned_conduct` | In own words (or a named campaign spokesperson), condemned Israel's conduct of the war in Gaza: e.g. civilian killing, starvation or blocking aid, "disproportionate", "collective punishment", violating international law. Condemning Hamas alone, or general sympathy for "all innocent lives", is not enough. `no` = own words defending Israel's conduct as justified or proportionate; else `unclear`. |

- 2023–26 statements count; latest clear position wins. Scored in the Israel/Gaza score (now 0–5).
- At the same pass, every candidate's `ceasefire_call` is re-searched under the revised definition above (a demand that the campaign stop, in any words), since the original search looked for the word "ceasefire".

## Redo: Israel/Gaza stance as an assessed position (2026-11-07, at the author's direction; supersedes File 4 scoring)
Why: the item-by-item coding (ceasefire / condition aid / genocide / AIPAC, plus condemned_conduct) tested for specific words and timing, and misread candidates whose positions were clear in substance (e.g. Jackson's "End the genocide in Gaza", Talarico's "collective punishment"). The Israel/Gaza dimension is now one assessed stance per candidate, judged from the whole public record, measured as distance from Sanders's own position (he led the Senate resolutions to block arms sales to Israel and calls Israel's conduct genocide).

Stance levels (pick the one that best describes the candidate's overall 2025–26 campaign position; wording doesn't matter, substance does):
- **4 — With Sanders or beyond:** wants to stop or block offensive arms/military aid to Israel (or all of it) AND characterizes Israel's conduct as genocide, ethnic cleansing, or an atrocity that must end, or equivalent.
- **3 — Restrict arms, sharp condemnation:** supports blocking/conditioning offensive weapons or aid, and condemns Israel's conduct in strong terms (civilian killing, starvation, collective punishment, war crimes), but stops short of level 4.
- **2 — Critical, no arms limits (or only case-by-case):** clearly criticizes Netanyahu's government or the conduct of the war, pushes humanitarian aid / a ceasefire / two states, but doesn't support restricting arms, or only case by case.
- **1 — Mainstream supportive with concern:** backs Israel and its military aid, with expressions of concern for civilians, hostages-and-ceasefire deals, two-state support.
- **0 — Unconditional support:** defends Israel's conduct as justified; opposes any conditions on aid.
- **unknown:** no meaningful public record on the issue.

Rules:
- Judge the whole record; the latest 2025–26 campaign position outweighs older statements; votes (with tallies) and AIPAC/UDP support are evidence and context, not decisive by themselves.
- Own words, campaign site, votes, or a named campaign spokesperson count. Opposition research and advocacy-group characterizations are leads, not evidence.
- Each assessment must give a 2–4 sentence rationale and cite the 2–4 statements it rests on (URL, date, quote under 15 words).
- Two assessors rate independently; disagreements are resolved at the sources and the resolution recorded.
- Score: Israel/Gaza = stance level (0–4); unknown counts as 0 in the score and is shown as unknown on the page. The old item codes stay in alignment_final.csv for reference.

## Revision: recency for health and wage (2026-11-07, at the author's direction)
A position from 2019–2022 says little about a 2026 campaign. For `health_level` and `min_wage_level`, only 2025–26 evidence (campaign statements, debates, questionnaires, 119th-Congress cosponsorships or votes) decides the value. If none exists after a targeted search, the value is `unclear` and the last known position is shown as context, with its date.

## Revision: latest position governs every item (2026-11-07, at the author's direction)
Views evolve, and on Gaza many politicians moved substantially in 2025–26, Sanders included. For every scored item, the latest clear position counts and only 2025–26 evidence decides a value; older evidence is shown as history. The Israel/Gaza reference point is Sanders's own latest position (2025–26): he votes to block offensive arms sales and describes Israel's conduct in Gaza as genocide.

## Correction to the two recency revisions above (2026-11-07, at the author's direction)
`unclear` is only for no information at all. The latest available position counts; if a targeted search finds nothing from 2025–26, the older position stands, flagged on the page with its date ("as of 2020"). Newer evidence always replaces older; older evidence stays in the dataset as history.

## Withdrawn: health-care ACA level (2026-11-07)
A `protect_expand_aca` level with a 0.25 score was added and withdrawn the same day at the author's direction: it was an invented scale. Candidates' 2025-26 health positions are recorded as stated; the agreed categories stand.
