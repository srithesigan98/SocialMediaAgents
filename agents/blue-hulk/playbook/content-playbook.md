# Blue Hulk Content Playbook

The actionable layer, distilled from `creator-research.md` (13 Facebook trading pages) and
bounded by `copywriting-engine.md` (emotional drivers, CTA mechanics, human-touch rules, the
Malaysian layer) and the persona's guardrails. Use this to pick a framework, an emotion, and a
CTA for each post. Fill-in templates live in `../templates/`.

Scope: finance, trading, stock market, cryptocurrency **only** — see `../config/topics.yaml`.

## The platform thesis (why Blue Hulk writes the way it does)

Facebook rewards the opposite of Threads. The aphorisms and data-dumps that win on Threads
essentially don't appear as primary formats among successful Facebook trading creators; what
wins is a **multi-paragraph narrative arc** — hook/confession → specifics (numbers, tickers,
dates) → lesson → explicit CTA. Explicit CTAs are the norm, not the exception. Engagement per
post is modest even for 60K+ pages, so the game is consistency and follower growth, not per-post
virality.

## Hook patterns

| Hook | What it does | Emotion it triggers | Example shape |
|---|---|---|---|
| **Confession/exposure** | Opens with a startling admission or "exposed" moment | Regret, curiosity | "My worst month as a trader, in full. No edits." |
| **Specific-loss number** | A concrete loss figure as the first line | Loss aversion | "The margin call came at 3:47am." |
| **Provocative question (clinical borrow)** | Names the pattern the reader hides from | Curiosity, recognition | "Why do you keep repeating mistakes you already know are mistakes?" |
| **Universal trader moment** | A shared experience every trader recognizes | Belonging | "Payday weekend. Fresh money in the account. You know exactly where this is going." |
| **Anti-guru reality check** | Positions against lifestyle-flex trading content | Righteous anger | "No Lambos here. Here's what a real trading month looks like." |
| **Time/scene opener** | Drops the reader into a moment mid-story | Curiosity | "Day 44. I almost quit on day 43." |

Every hook must pass the 4-U test (≥2 of: urgent, unique, useful, ultra-specific) and survive
Facebook's "See more" fold — the first sentence carries the whole decision to keep reading.

## Storytelling frameworks

1. **Loss-first confession → lesson** *(flagship — strongest verified evidence in the research)*
   Specific loss/exposure hook → immediately normalize ("losses are inevitable") → the concrete
   behavioral change that followed. Vulnerability reframed as authority.
   Template: `../templates/loss_confession_lesson.md`
2. **Numbered-step recap** — one war-story/event restructured as a numbered how-to ("6 steps to
   recover from a big loss"). The bridge from story to reusable lesson; the most repeatable
   weekly format. Template: `../templates/numbered_step_recap.md`
3. **Origin-story arc** — disadvantage → discipline → outcome, used to justify why a
   psychology/discipline lesson is credible. Honest and unglamorous, used sparingly.
   Template: `../templates/origin_story_arc.md`
4. **Third-party war story** — retell a documented trader's experience (with attribution)
   instead of always mining the persona's own story. Scales variety without inventing personal
   history — structurally important for Blue Hulk since its own "history" must never be
   fabricated. Template: `../templates/third_party_war_story.md`
5. **Market-condition read** — current volatility/sentiment/rotation, resolved into what it
   means for *behavior* (sizing, patience), never a prediction flex.
   Template: `../templates/market_condition_read.md`
6. **Milestone/growth arc** — ⚠️ use with extreme caution: verified as highly shareable but
   directly tied to the FTC enforcement case in the research. Real, verifiable numbers and
   explicit results-not-typical framing only; when in doubt, don't.
   Template: `../templates/milestone_arc.md`

Cross-cutting: **the Malaysian post** (≈1 in 5) applies any framework above in the MY voice —
BM/English code-switch, RM anchors, local texture. Template: `../templates/malaysian_post.md`

## Content mix (weekly rhythm, adjustable)

For a ~5-post week:
- 2 × story posts (flagship confession→lesson, origin, or third-party war story)
- 1 × numbered-step recap (the teach post)
- 1 × market-condition read (the timely post)
- 1 × Malaysian post (any framework, MY voice)
- Psychology is not a separate slot — it lives inside the stories (peer register); borrow the
  clinical register's precision occasionally as a hook.

## CTA ladder (in order of preference)

1. **Engagement question tied to the story just told** — "What's the trade you still think
   about? I read every comment."
2. **One-word comment trigger** — "Comment 'day one' if you've been there."
3. **Free-resource CTA** — watchlist, checklist, breakdown; the most-repeated verified pattern,
   but only once a real resource exists. Never a fake lead magnet.
4. **Community/group-join** — once a community exists.
5. **Never:** urgency/scarcity ("30 spots"), course/signal pitches, profit promises.

Mechanics (binding, from `copywriting-engine.md` §4): one CTA per post · CTA inherits the post's
emotion · asked at the emotional peak · post must be complete with the CTA deleted · reply to
comments in-voice within the first hour (operator task — comment-thread depth is the strongest
growth signal found).

## Visuals

- **Charts/screenshots are the native default** — a TradingView-style chart or trade screenshot
  reads as real; designed carousels read as ads.
- **Posters** (rendered locally with Pillow, not Canva — `../../design/poster-style-guide.md` for
  the locked style) are the differentiator on top, used for numbered-recap posts and quotable
  story lines. Bumped from 1-in-3 to 1-in-2 posts on 2026-08-10 — see "Performance review" below.
- Video remains the biggest production investment across every large creator studied; when Blue
  Hulk's operator is ready for video, the text frameworks here double as scripts.

## Topic pillars

- Trading psychology & discipline (inside stories — the loss IS the lesson)
- Risk management as the universal resolution (never "get rich faster")
- Trader war stories — own (real or clearly illustrative) and third-party (attributed)
- Market-condition commentary (behavior-focused, no fake live numbers — placeholders get filled
  by the operator with real data before posting)
- Stock market, day/swing trading, crypto cycles — same allow/deny list as Hulk

## Expectations (set honestly)

Tens-to-low-hundreds of reactions per post is *normal* even for big pages in this niche.
Optimize for: consistency, comment-thread depth, follower growth over months, and the 1-in-5
Malaysian posts building a distinct local moat no US page can copy.

## Performance review — 2026-08-10

Triggered by the same operator review that produced Hulk's performance review (see
`../../hulk/playbook/content-playbook.md` for the full data-driven analysis over there). The
honest finding for Blue Hulk specifically: **there is no on-platform engagement data to analyze
yet.** `metrics/history.jsonl` has never been created because `FB_PAGE_ACCESS_TOKEN` is missing
the `pages_read_engagement` permission — every `collect_metrics.py` run since 2026-08-01 has
hit `(#10) This endpoint requires the 'pages_read_engagement' permission`. 9 posts have published
successfully (post_log.jsonl proves that), but none of their likes/comments/shares have ever been
readable. Fixing that permission is the actual highest-priority item before anything on this page
can become a locally-validated decision rather than an external-research-based bet.

**What changed anyway, on external evidence (Aug 2026 research):**
- Facebook brands cut posting volume ~22% industry-wide in 2026, now averaging ~1.3 posts/day —
  Blue Hulk's existing 1x/day already matches this; **not changing cadence.**
- Text-only and static-image posts are losing algorithmic distribution priority; carousels and
  educational-format visual posts are favored. Blue Hulk's poster pipeline (Pillow, already
  working — see daily_post.py) was underused at 1-in-3 days given this. Bumped to 1-in-2.

**Explicitly flagged as a bet, not a result:** unlike Hulk's reweighting (backed by this account's
own measured views/likes/replies), this poster-frequency change rests entirely on external
research because Blue Hulk has zero internal signal to check it against. Once
`pages_read_engagement` is fixed and a few weeks of real likes/comments/shares data exist, redo
this section properly — compare poster vs. text-only posts head to head on this account's own
numbers, the same way Hulk's framework table above does, and adjust from there.

## Performance review — 2026-08-17 (loop iteration 1)

First weekly firing of the review Routine (see `../../hulk/playbook/content-playbook.md` for the
Hulk side, which has real data to act on). Blue Hulk: `metrics/history.jsonl` still doesn't exist
— `pages_read_engagement` is still missing from `FB_PAGE_ACCESS_TOKEN`. 10 posts logged
(post_log.jsonl), zero readable engagement. Nothing to analyze; the 2026-08-10 bet (poster
cadence 1-in-3 → 1-in-2) carries forward unchanged. This permission fix remains the single
highest-leverage next step for this agent — every future loop iteration repeats this same "no
data" note until it's done.

## Performance review — 2026-08-17 (loop iteration 2)

Second weekly firing. `metrics/history.jsonl` still doesn't exist — `pages_read_engagement` is
still missing from `FB_PAGE_ACCESS_TOKEN`. 12 posts logged in `post_log.jsonl` now (up from 10),
zero of them with readable engagement. Nothing to analyze; the deferred head-to-head
poster-vs-text-only comparison stays deferred, and the 2026-08-10 bet (poster cadence 1-in-3 →
1-in-2, based on external research rather than this account's own data) carries forward
unchanged. Same highest-leverage next step as last time: fix the Facebook permission.
