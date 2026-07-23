# Blue Hulk Posting Duties

Standing operational rules for Blue Hulk's Facebook page (Striker Zones,
`FB_PAGE_ID=1020053851202106`). These govern cadence and post composition; content quality still
comes from the persona, content-playbook, and copywriting-engine.

## The three duties

1. **Post every day** — one on-brand Facebook post daily. Automated via
   `.github/workflows/blue-hulk-daily.yml` → `scripts/daily_post.py`.
2. **1 in every 4 posts is a Striker Zones post** — relates the day's trading lesson to the
   Striker Zones community and ends with a CTA to the Telegram link:
   **https://t.me/strikerzonesadmin_bot**
3. **1 in every 3 posts carries a poster** — a graphic in the locked Blue Hulk style
   (`../../design/poster-style-guide.md`) related to that post. Generated via Canva.

## Deterministic rotation (by calendar date)

The duties are keyed to the date's ordinal so they hold their exact ratios over time and never
drift, independent of each other:

- **Striker Zones day:** `date.toordinal() % 4 == 0` → exactly every 4th day (1 in 4).
- **Poster day:** `date.toordinal() % 3 == 0` → exactly every 3rd day (1 in 3).

Over a 12-day cycle (LCM of 3 and 4) the pattern is fixed. `SZ` = Striker Zones post,
`▣` = poster attached:

| Day in cycle | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Striker Zones | · | · | · | SZ | · | · | · | SZ | · | · | · | SZ |
| Poster ▣ | · | · | ▣ | · | · | ▣ | · | · | ▣ | · | · | ▣ |

Result per 12 days: 12 posts, **3 Striker Zones posts, 4 posters**, and day 12 is both — a
Striker Zones post *with* a poster, which is the ideal promo unit.

## Duty 2 — Striker Zones posts (composition rules)

Striker Zones is the operator's **own** community, so promoting it is in-scope — but it still
obeys every anti-hype guardrail (see the reconciliation note in `../config/topics.yaml`):

- **Value first, CTA last.** The post is a real trading lesson/story in Blue Hulk's normal voice;
  the Striker Zones mention and Telegram CTA come at the end, after the value has landed. Never a
  bare ad.
- **The CTA invites, it doesn't pressure.** Frame it as joining a community of traders working on
  the same discipline — e.g. *"We talk through setups like this every day inside Striker Zones —
  join us: https://t.me/strikerzonesadmin_bot"*. 
- **Banned even here:** profit promises, income claims, "signals that print money", scarcity
  ("limited spots"), guaranteed-returns language. Owning the brand doesn't lift these — they're
  what the creator research tied to the least credible (and sanctioned) accounts.
- **Facebook reach note:** posts with external links (especially `t.me`) are often
  reach-throttled by Facebook. Option: put the CTA line in the post and/or first comment. The
  automation keeps it in the post body per the duty; revisit if reach data says otherwise.

## Duty 3 — posters (execution)

The poster's content is mapped from the post via the shared slots (top label / headline / body /
footer) in `../../design/poster-style-guide.md`, in the locked dark-ground / ticker-green /
candlestick style.

**Execution constraint:** Canva poster generation runs through the Canva connector, which is
available in an assisted Blue Hulk session — **not** inside the headless GitHub Action (that job
only has Anthropic + Facebook credentials, no Canva OAuth). So poster days are produced in one of
the models below (operator's choice — see the open question at the end of the duty rollout):

1. **Assisted session duty** — the daily run happens in a Blue Hulk session; on poster days the
   Canva poster is generated + exported and posted as a photo. All three duties fully automatic
   within the session. (Recommended — it's the only path that yields true Canva posters daily.)
2. **Headless text + separate poster** — the GitHub Action posts text daily and Striker Zones on
   1-in-4; on 1-in-3 poster days the poster is generated in a quick session and the operator (or
   the script's `--poster-image`) attaches it.
3. **Headless auto-rendered poster** — a local renderer draws the locked style headlessly (not
   Canva) so the action is fully self-contained. On-brand, but not Canva.

Until the model is chosen, `daily_post.py` implements duties 1 and 2 fully and **logs poster
days** (and can attach a poster via `--poster-image PATH` when one is supplied).
