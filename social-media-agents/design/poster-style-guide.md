# Shared Poster Style Guide — Hulk & Blue Hulk

Both agents can turn a text draft into a poster/graphic via Canva. Facebook (Blue Hulk) favors
image posts heavily; on Threads (Hulk) an image post is the exception rather than the rule — used
when a post's content genuinely benefits from a visual (a list worth screenshotting, a quotable
principle, a chart-adjacent idea), not on every post.

## Reference design

- **Canva design:** "High-Contrast Trading Strategy Poster" — `DAHPoIgypZ0`
- **Edit link:** https://www.canva.com/d/txDd2KbxbHKJXIJ
- **View link:** https://www.canva.com/d/90uByipmp1dGOse

This is the approved reference look for all agent posters. Open the edit link in Canva to
duplicate it manually for one-off custom edits.

**Note on brand templates:** Canva's "publish as reusable brand template" feature
(`publish-brand-template`) requires a paid Canva plan (Pro/Teams/Enterprise) and returned an
upgrade-required error on this account. Until that's available, posters are regenerated per-post
via `generate-design` using the locked style spec below rather than an autofill brand template —
functionally similar, just one extra step (no dataset autofill, so content goes in the `query`
text each time).

## Locked style spec

Reuse this spec verbatim (or near-verbatim) as the base of every `generate-design` query, with
only the post-specific content swapped in:

> A bold, high-contrast trading/finance poster. Dark background (near-black or deep charcoal), a
> single accent color (electric green or amber, like a stock-ticker up-color), a minimal
> candlestick chart line as a subtle background element. Large bold sans-serif headline text.
> Confident, terse, trader-journal aesthetic — no stock photos of people, no cheesy clipart, just
> typography and a subtle chart line.

Content-specific slots to fill in per post:
- **Top label** (small text): a one-line context tag, e.g. "BTC — testing resistance, 3rd time
  this month."
- **Headline** (large text): the hook line from the draft.
- **Body lines** (medium text, 1-3 short lines): the core point(s) of the post.
- **Footer** (small text): the risk caveat / CTA / closing line, if the framework has one.

## Per-agent usage

### Blue Hulk (Facebook)
- Posters are a routine companion to posts. Use `design_type: "facebook_post"` for in-feed
  images, `"poster"` for larger/shareable graphics.
- Most Blue Hulk frameworks (hook → story → lesson → CTA) compress into the slots by using the
  hook as headline and the CTA as footer.

### Hulk (Threads)
- Posters are **selective** — attach one when the post is a listicle, a standalone
  aphorism/principle worth screenshotting, or a historical-proof reveal (dense numbers present
  better as a graphic). Skip it for terse calls and sentiment checks, where plain text reads
  more native (per the creator research: charts/screenshots read native on trading feeds; slick
  graphics on every post do not).
- Use `design_type: "instagram_post"` (1080×1350 portrait — displays well on Threads) or a
  square variant.
- Posting with an image: `scripts/post_to_threads.py --image-url <public-url>` — the Threads
  Graph API takes a public image URL (`media_type: IMAGE`), so export the poster from Canva as
  PNG and host it somewhere reachable (or use the Canva export URL while it's valid).

## Workflow (both agents)

1. Write or select a text draft.
2. Decide whether the post warrants a poster (routine for Blue Hulk; selective for Hulk).
3. Map the draft onto the slots above (top label / headline / body / footer).
4. Call Canva's `generate-design` with the locked style spec + filled-in slots and the
   platform-appropriate `design_type`.
5. Review candidates, pick one, call `create-design-from-candidate` to save it.
6. Export via `export-design` (check `get-export-formats` first) as PNG.
7. Publish: upload to Facebook directly (Blue Hulk), or pass the hosted image URL to
   `post_to_threads.py --image-url` (Hulk).
