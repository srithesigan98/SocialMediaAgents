---
workflow: hyperframes (explainer)
flow: automation
storyboard: yes
message: "Know what MRTA and MLTA really do — and who gets paid — before you sign"
angle: myths-vs-facts
length: ~60s (55–65s)
destination: Instagram Reels + Threads (Senang Homes)
aspect: 9:16 (1080x1920)
language: en
audience: Malaysian home buyers taking a home loan
voice: HeyGen (user chose sign-in; Kokoro is the offline fallback)
captions: styled, word-timed, burned in
sound: quiet music bed ducked under VO + light cue on each myth -> fact reveal
---

## Intent
User: "for mrta mlta can you create an animated video with voiceover in detailed explanation".
Chose: myths vs facts (the format from their reel-ideas screenshot), about 60 seconds, storyboard first,
automation, captions on, music bed + reveal sounds, HeyGen voice.

## Constraints (standing)
- Brand: Senang Homes magazine theme — forest #142E2B, ivory #F3F0E7, peach #FFAA78, terracotta #B94321,
  orange #F87947, beige #E5DED0; Outfit (headlines) + Gelasio italic (second phrase). Fonts in
  agents/hulk/scripts/fonts/.
- Drawn illustrations about MRTA/MLTA — never property photos (user: "not the property").
- Every video gets a themed cover/thumbnail (frame 0 + Instagram cover_url).
- Claims: Malaysian market, general — no insurer names, no premium rates, no legal promises. Every myth/fact
  passes the adversarial fact-check (workflow mrta-mlta-factcheck) before the storyboard. The RM500K /
  30 years / 3% example is labelled as an illustration.
- Post only after the user approves the final render. Caption ends with "Comment MRTA" + the WhatsApp CTA line.
