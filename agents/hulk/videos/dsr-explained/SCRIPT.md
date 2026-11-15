# Narration (locked for TTS: Kokoro af_heart) — "Why banks reject home loans: your DSR"

Illustration used throughout (made-up numbers, labelled "Illustration" on screen):
net income RM5,000; car loan RM800 + PTPTN RM200 + new home loan RM2,000 = RM3,000 -> 60%;
a card counted at RM500 -> RM3,500 -> 70%; without the card and the car loan -> RM2,200 -> 44%.
Hedges are required ("usually", "may", "some", "each bank") — don't strengthen them. No bank names, no live
rates, no DSR cap figure (BNM sets no single cap; banks set their own).

| id | beat | line | source |
|---|---|---|---|
| vo01 | hook | Your salary looks fine. So why did the bank say no? Usually, it's one number: your DSR. | DSR is a core affordability test in BNM's Policy Document on Responsible Financing (bnm.gov.my, "Measures to Promote Responsible Financing Practices"); "usually" because CCRIS/CTOS record, income documents, valuation etc. can also cause rejection (EdgeProp "DSR vs CCRIS"; PropertyGenie loan-rejection guide) |
| vo02 | formula | Debt service ratio. Add up your monthly debts, then divide by your net income, after EPF and tax. | BNM defines DSR as total monthly bank and non-bank debt obligations / monthly income net of statutory deductions (tax, EPF) (BNM responsible financing measures; BNM FSR box "Looking Beyond DSR") |
| vo03 | stack | Illustration: RM5,000 net a month. Car loan, RM800. PTPTN, RM200. The new home loan, RM2,000. | Illustration; banks include the new loan's instalment and non-bank debts such as PTPTN (BNM: "all debt obligations", bank and non-bank; StashAway MY, RinggitPlus DSR guides) |
| vo04 | 60% | That's RM3,000 in debts. Divide by RM5,000: 60% of your income. | Illustration: 3,000 / 5,000 = 60% |
| vo05 | card | A credit card you pay in full may still count. Here, RM500 more: now 70%. | Many banks count a share of the card limit rather than the balance, methods vary by bank (StashAway MY, PropertyHunter 2020: some use 1%, others more) — hence "may"; RM500 is an illustration, no % rule stated. 3,500 / 5,000 = 70% |
| vo06 | limit | Each bank sets its own limit, and may also check what's left after your debts. | BNM: banks have flexibility to set the appropriate DSR (FMT / NST, June 2018); BNM requires assessing income left after deductions and obligations, banks may use net-disposable-income checks (BNM FSR 2024 H1 box; StashAway) |
| vo07 | lower it | To bring it down, cancel cards you don't use, and clear small loans before you apply. | Fewer commitments -> lower DSR (general arithmetic; CIMB / RinggitPlus DSR guides). "Cancel" applies only to cards counted by limit |
| vo08 | rebuild | Cancel that card, clear the car loan, and the same home is 44%. | Illustration: (200 + 2,000) / 5,000 = 44% |
| vo09 | close | Comment "DSR", and we'll work out your number before you view. | — |

Dropped in the skeptic pass: any "banks cap DSR at 60/70%" figure (not a BNM rule, guides disagree), a fixed
"5% of card limit" rule (bank-specific; one guide says minimum payment, another 1%), "PTPTN always counts
even when deferred" (single unverified source), "longer tenure lowers DSR" (true but stretched the script).

Voice check: Parakeet and Whisper model downloads (huggingface.co) were blocked in the build session, so word
timings come from tools/align.py (energy pauses + espeak phoneme weights over the exact script text). Every
line's espeak phonemes were checked by hand: "D S R" = /diː ɛs ɑːɹ/, "P T P T N" = /piː tiː piː tiː ɛn/,
"E P F" = /iː piː ɛf/; captions show DSR / PTPTN / EPF and RM amounts.

Post caption must also carry: "Illustration only. Each bank assesses differently; this isn't a loan approval."
