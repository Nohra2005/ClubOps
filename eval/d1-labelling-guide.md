# D1 labelling guide (answer key for `capture`)

D1 is the answer key that `capture` is graded against. It is written **before** capture exists (D-16), using the same definition of know-how that capture will use (D-19). The labelled file contains real club data, so it stays in the git-ignored `data/private/d1/`; only its hash goes into `eval/FROZEN.md`.

## Files (in `data/private/d1/`, never committed)

| File | What it is |
|---|---|
| `d1-episodes-cabinet.md` | The episodes to read, redacted (D-09, D-36), lines numbered `L1`, `L2`… per episode |
| `d1-labels.csv` | Your answer key, one row per know-how item |
| `d1-selection.json` | Why each episode was picked (stratum, size, media share) |

## What counts as know-how (D-19)

Label something only if a future cabinet would want to know it **next year**. One row per distinct piece of know-how.

| `kind` | Means | Example shape |
|---|---|---|
| `procedure` | How to get something done, in steps | "To book X: fill form Y, then email Z, at least N days before" |
| `rule` | An AUB requirement or restriction | "Event X needs approval Y before it can be announced" |
| `gotcha` | A trap: trigger, consequence, how to avoid | "Gate G opens at 7 AM, so an earlier meeting point there fails" |
| `lesson` | Something that worked or failed, and what to do next time | "Event type T worked without sponsors" |
| `decision` | A choice the club made **with its reason** | "Option A rather than B, because…" |
| `relationship` | A sponsor, vendor, office or club and what they offer | "Café C gives runners a discount after runs" |
| `rhythm` | Something that happens at the same time each year | "Registration R opens in month M" |
| `obligation` | Something owed to someone on a schedule | "Report P is due after each event" |
| `identity` | What the club is: mission, tone, signature events | "Our signature event is E" |

**Not know-how:** one-off logistics ("leaving in 5 min"), social chat, jokes, anything true only that day, and things a careful reader can't get from the text.

## Columns

| Column | Fill with |
|---|---|
| `episode_id` | Already filled, e.g. `cab-043` |
| `item_no` | 1, 2, 3… within the episode |
| `kind` | One of the nine above, or `none` if the episode has no know-how (one row) |
| `scope` | `aub` if it is true for every club (an OSA rule), `club` if only for the Running Club |
| `title` | Short name, ≤ 120 characters. Reuse the **same title** when the same fact appears in another episode |
| `statement` | The know-how in plain English, one or two sentences (D-22) |
| `lines` | Supporting lines, e.g. `L3-L7` or `L2,L9` |
| `quote` | The shortest supporting words, in the original language (English, French, Arabizi, Arabic) |
| `low_evidence` | `y` if it depends on an omitted voice note, image or file (D-18), otherwise blank |
| `notes` | Anything uncertain |

## Rules for labelling

1. **Only what the text supports.** Use what you know to *read* Arabizi, French and shorthand, not to *add* facts that are not in the episode. If you know something more, put it in `notes`.
2. **Same fact twice → label it twice** with the same title. Capture should merge repeats (D-20); the matching title lets us check it did.
3. **Contradictions:** label both statements and write `contradicts <title>` in `notes`.
4. **No names of who said what** in `statement` (D-09). Names of offices and contacts are fine ("Tala at OSA").
5. **Stop after 5 episodes** and send them for a calibration check before doing the rest.

## After labelling

1. Hash the CSV and record it in `eval/FROZEN.md` with the date (frozen before any capture code is written).
2. Hold out ~30% of episodes, chosen at random with a recorded seed, for the final report only.
3. One cabinet member labels 30 excerpts independently; agreement between the two of you is reported (D-16).
