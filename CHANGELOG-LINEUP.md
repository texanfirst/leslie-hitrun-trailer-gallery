# CHANGELOG — Blind lineup refactor (2026-09-29 12:13 CDT)

Live: **https://leslie-hitrun-gallery.vercel.app/**  
Repo: https://github.com/texanfirst/leslie-hitrun-trailer-gallery  
Incident: Mon 2026-09-28 ~9:32 AM CT, Selma TX / I-35  
Eyewitness (exact): “I’m not sure if these are the correct letters, but they were sideways.”

## Final-response checklist (10)

### 1. Blind one-photo lineup (NO / MAYBE / FAMILIAR)
Implemented in `index.html`. Eyewitness sees one photo at a time with large thumb-friendly buttons. Company **name and logo are hidden** during ID.

### 2. Her Drawing modal + ORIGINAL evidence
`assets/leslie-drawing-original.png` shipped unaltered (ORIGINAL). Modal quotes the exact eyewitness statement. Shapes are **not** labeled as definite letters. `companies.json` → `evidence.drawing` / `evidence.after` (AFTER empty).

### 3. Rear Doors Only + Similar to Her Drawing (org only)
Default **Rear Doors Only** for the eyewitness pass. **Similar to Her Drawing** only reorders the queue via `similar_to_drawing` tags (28 carriers tagged) — not letter claims.

### 4. Show more like this + no reshuffle of rejected branding
After MAYBE/FAMILIAR, optional **Show more like this** injects more photos from the same `branding_group` (still blind). **NO** marks that branding group rejected and removes remaining same-brand queue items.

### 5. Review screen + export report + admin
Review reveals names for MAYBE/FAMILIAR. Export copies a plaintext report. Admin screen lists pools/metadata/evidence and full export. Persistence: `localStorage` key `leslie-hitrun-lineup-v2`.

### 6. Carrier expansion (before → after)
| Metric | Before | After |
|--------|-------:|------:|
| Companies | 75 | **115** |
| Trailer photos (excl. logos) | 154 | **161** |
| Verified rear photos | 4 | **5** |
| Logos | 75 | **75** |
| Logo / metadata-only pool | 13 | **53** |
| SA / I-35 / Laredo / Texas corridor tags | (partial) | **43** |
| `similar_to_drawing` tags | (M-chip era) | **28** |
| Low-priority pool (kept, not deleted) | — | **70** |

New carriers include H-E-B, CFI, Gulf Winds, Laredo/SA pools, Target/Costco/private fleets, Nussbaum, Freymiller, Navajo, Hogan, Red Classic, Transportes Castores, and other I-35 / border names (many metadata-first pending public rear photos).

### 7. Verified rear doors in eyewitness lineup
Logo-only and broken images excluded. Current verified rears (5):

- `schneider` → `images/schneider_05.jpg`
- `knight` → `images/knight_04.jpg`
- `marten` → `images/marten_01.jpg`
- `rlcarriers` → `images/rlcarriers_01.jpg`
- `crengland` → `images/crengland_01.jpg`

Schneider rear is a true rear-door shot (orange fleet — useful elimination, not a white-trailer match).

### 8. Safety language + iPhone portrait UX
Start/review/export keep **lineup only — not an ID** wording. Viewport-fit, safe-area padding, large tap targets, sticky minimal top bar, no auto-keyboard on load.

### 9. Smoke test
`scripts/smoke_lineup.py` checks HTML invariants, ORIGINAL drawing asset, exact quote, carrier expansion floor, rear files on disk, logo exclusion, and lineup_eligible rules — **OK**.

### 10. Known gaps (honest)
- Public Commons/Openverse still rarely publish usable **white trailer + subtle burgundy/script rear-door** shots for the burgundy shortlist (Swift, Werner, Roehl, U.S. Xpress, CRST, Crete, Heartland, Paschall, Stevens, Central Freight, FFE, Millis, etc.).
- Many new SA/Laredo carriers are **metadata-only** until free rear sources appear.
- Only **5** verified rears in the blind pass today; after rear-only completion the UI offers continuing with other angles (clearly labeled, names still hidden).
- Do not treat `similar_to_drawing` or legacy M notes as letter identification.
- Rate limits (HTTP 429) capped further Commons scraping this pass; expand later with longer delays.

## Requirements map (Rick 1–18)

1. Blind one-photo-at-a-time lineup — **done**  
2. NO / MAYBE / FAMILIAR — **done**  
3. Hide company name/logo during ID — **done**  
4. Her Drawing modal — **done**  
5. Rear Doors Only — **done**  
6. Similar to Her Drawing as search organization only — **done**  
7. Show more like this — **done**  
8. Review screen — **done**  
9. Don’t reshuffle rejected identical branding — **done**  
10. Expand SA / I-35 / Laredo carriers — **done** (75→115; photos still thin)  
11. Metadata fields (`branding_group`, `pool`, `corridor`, `lettering_style`, `similar_to_drawing`, `lineup_eligible`, …) — **done**  
12. Evidence notes ORIGINAL vs AFTER — **done**  
13. Admin view — **done**  
14. Export report — **done**  
15. Safety language — **done**  
16. iPhone portrait UX — **done**  
17. localStorage persistence — **done**  
18. Test (`smoke_lineup.py`) — **done**

## Method notes
- Did **not** rebuild from scratch; preserved prior `companies.json` / `images/` / logos / docs.
- Demoted M-as-dominant UI chip; legacy shortlist kept in `LESLIE-M-NOTES.md` + optional tags.
- Scraping: Wikimedia Commons + Openverse, rate-limited User-Agent, no fabricated URLs; rear claimed only with rear-titled / verified shots.
