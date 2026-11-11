# SPEC — MRTA vs MLTA: four myths (storyline A, "The loan letter")

GOAL:    the viewer knows MRTA mainly pays the bank, MRTA cover shrinks while MLTA stays level, fire
         insurance doesn't cover the loan, and MRTA isn't required by law — then comments "MRTA".
OUTPUT:  HyperFrames, 1080 x 1920, 30 fps. Instagram Reels + Threads.
TIME:    60.0 s x 30 = 1800 frames. Voice is the clock (Kokoro af_heart, 8 lines, 51.6 s of speech).
         Lines start at 0.30 / 7.10 / 14.50 / 19.90 / 28.70 / 34.80 / 42.50 / 50.20 s.
LOOK:    ground forest #142E2B, flat, no gradient. Ink on paper forest #142E2B; ink on ground ivory #F3F0E7.
         Accent terracotta #B94321 only for the MYTH stamp + strike-through; peach #FFAA78 for the sticky
         note + the one fact word per shot + MLTA; orange #F87947 only on the end-card CTA.
         Display Outfit SemiBold 84 px, -1% tracking; second phrase Gelasio Medium Italic 88 px, peach
         (the brand's own two-part headline). Label Outfit Medium 24 px, +16% tracking, peach.
         Letter body Outfit Regular 30 px / values Outfit SemiBold 32 px. Note: Caveat 600 56 px.
         Medium: one sheet of offer-letter paper (ivory, 860 x 700 px, rotated -1.5 deg, shadow 0 24 px
         48 px rgba(0,0,0,0.35)), a peach sticky note (360 x 290 px, rotated +4 deg, shadow 0 10 px 18 px
         rgba(0,0,0,0.25)), a rubber stamp (8 px terracotta border, multiply, 85% ink), a yellow
         highlighter (#FFD84D at 55%, multiply). No grain, no vignette.
OBJECTS: the offer letter (letterhead rule, 4 labelled rows: Loan amount RM500,000 / Tenure 30 years /
         Mortgage cover MRTA or MLTA / Benefit payable to ____); the sticky note with the myth in
         handwriting; the MYTH stamp; a fire/houseowner policy card (red-orange header strip, house glyph);
         a shield badge (forest, ivory check); the payout split bar (bank forest / leftover peach); the
         cover chart (MLTA level line peach, MRTA reducing curve forest, RM500K / 30 years axes, label
         "Illustration: RM500K, 30 years, 3% p.a.").
LAYOUT:  status zone 0-168 empty. Headline 200-390. Letter 430-1130. Captions 1190-1310 (centred, 900 px
         max). Below 1330 decoration only. Nothing readable right of x = 960 (action rail).
MOTION:  arrivals expo.out 0.5 s; stamp lands scale 1.35 -> 1, rotate -18 -> -12 deg, 0.18 s power4.out
         + 2 px shake for 3 frames; strike-through draws left to right 0.25 s power2.inOut; handwriting
         note pins in from y -40 px, 0.4 s back.out(1.3); highlighter sweeps 0.35 s power2.inOut; chart
         lines draw (stroke-dashoffset) 0.9 s power2.inOut; exits 0.25 s power3.in. Words stagger 70 ms.
         The letter never moves between S1 and S7 (one frame that rebuilds); S8 the letter slides down
         out of frame 0.6 s power3.in.
SHOTS:   S1 0.0-7.1  hook. Frame 0 = thumbnail: headline "4 MRTA myths" / "most buyers believe", the
                     letter, note "MRTA pays my family" already pinned. "who … pay?" (2.86-3.74) the
                     "Benefit payable to" blank gets a highlighter + "?" (3.4). Sound: bed enters.
         S2 7.1-14.5 MYTH stamp on "Myth" (7.5); strike on "In fact" (10.2); blank fills "THE BANK"
                     on "bank" (11.9); "to reduce or clear your loan" in italic under it (12.5).
         S3 14.5-19.9 MLTA row lights (14.7); split bar draws: bank part (15.7), leftover peach on
                     "goes to you" (17.4), label "you / nominee" (18.4). Label "Illustration".
         S4 19.9-28.7 new note "My cover stays the same" pins (19.9); stamp (20.3); strike (22.2); chart
                     replaces the rows: MRTA curve draws on "shrinks" (24.1), schedule ticks (24.7),
                     MLTA level line on "MLTA" (26.4), "stays level" label (27.6).
         S5 28.7-34.8 note "Fire insurance protects my loan" (28.7); stamp (29.1); fire policy card slides
                     over the letter's left half on "Fire insurance" (29.5); strike (31.7); "Building ✓"
                     (32.9); "Loan ✗" (33.5).
         S6 34.8-42.5 card slides off; shield badge on the loan row: "death / TPD" (35.1-37.1);
                     "MRTA" (38.1) and "MLTA" (39.4) chips; loan bar fills "some" then "all" (40.7-41.1).
         S7 42.5-50.2 note "MRTA is required by law" (42.5); stamp (42.9); strike + margin "not law" on
                     "It isn't" (45.9); conditions clause "Borrower to obtain mortgage cover" highlighted
                     on "bank … condition" (47.0-48.9).
         S8 50.2-60.0 letter exits down; four stamped notes fan in; "Takaful: MRTT · MLTT" (51.9-53.0);
                     CTA "Comment MRTA" (54.2); Senang Homes logo carried in (55.8); hold 2.5 s+.
BANNED:  dark void with floating bits; glow/neon/particles; gradients; everything centred; every
         element fading and sliding up; titles moving after they land; numbered "01/04" labels;
         three cards in a row; the logo docked in a corner; the narration repeated word for word on
         screen; insurer names, rates, any claim stronger than SCRIPT.md.
QA:      0.0 (thumbnail reads with sound off), 5.5, 13.9, 19.5, 28.3, 34.4, 42.0, 49.6, 58.5 —
         each: text inside 168-1330, captions not overlapping the letter, one accent per shot.
