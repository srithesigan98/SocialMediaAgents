# Blue Hulk Poster Style Guide

Blue Hulk can turn a text draft into a poster/graphic via Canva, in addition to writing plain
text posts — useful since Facebook favors image/carousel posts much more than Threads does.

## Reference design

- **Canva design:** "High-Contrast Trading Strategy Poster" — `DAHPoIgypZ0`
- **Edit link:** https://www.canva.com/d/txDd2KbxbHKJXIJ
- **View link:** https://www.canva.com/d/90uByipmp1dGOse

This is the approved reference look for Blue Hulk posters. Open the edit link in Canva to
duplicate it manually for one-off custom edits.

**Note on brand templates:** Canva's "publish as reusable brand template" feature
(`publish-brand-template`) requires a paid Canva plan (Pro/Teams/Enterprise) and returned an
upgrade-required error on this account. Until that's available, posters are regenerated per-post
via `generate-design` using the locked style spec below rather than an autofill brand template —
functionally similar, just one extra step (no dataset autofill, so content goes in the `query`
text each time).

## Locked style spec

Reuse this spec verbatim (or near-verbatim) as the base of every `generate-design` query for a
Blue Hulk poster, with only the post-specific content swapped in:

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
- **Footer** (small text): the risk caveat / closing line, if the framework has one.

## Workflow

1. Write or select a text draft (see `../playbook/` once populated, or reuse a Hulk-style
   template adapted for Facebook's longer form).
2. Map the draft onto the slots above (top label / headline / body / footer) — most Blue Hulk
   frameworks (hook → story → lesson → CTA) compress naturally into this structure by using the
   hook as headline and the CTA as footer.
3. Call Canva's `generate-design` with `design_type: "facebook_post"` (for in-feed images) or
   `design_type: "poster"` (for a larger/shareable graphic), with a query combining the locked
   style spec above and the filled-in slots.
4. Review the generated candidates, pick one, call `create-design-from-candidate` to add it to
   the Canva account.
5. Export via `export-design` (check `get-export-formats` first) as PNG for direct upload to
   Facebook.

## Status

This file was created ahead of the full Blue Hulk playbook (creator research on Facebook trading
pages is still in progress as of this commit) so the poster-generation capability is documented
and usable immediately. The rest of `blue-hulk/` (persona, playbook, templates, config, scripts)
will be filled in once that research lands.
