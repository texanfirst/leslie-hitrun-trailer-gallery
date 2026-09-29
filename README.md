# Trailer lineup gallery — Selma I-35 hit-and-run

**Lineup only. This does not identify the truck.**

## Live URL

**https://leslie-hitrun-gallery.vercel.app/**

## Incident (for context)

- **When:** Monday 2026-09-28, ~9:32 AM CT
- **Where:** Selma, TX — I-35
- **What Leslie is looking for:** White semi *trailer*; writing on the **rear doors** believed **small / subtle dark red / maroon / burgundy**; simple, maybe script; letter unsure
- **Eyewitness (exact):** “I’m not sure if these are the correct letters, but they were sideways.”
- **Drawing:** `assets/leslie-drawing-original.png` (ORIGINAL, unaltered). Shapes are **not** labeled as definite letters.

## How the blind lineup works (phone)

1. Open the live URL on an iPhone (portrait).
2. Optionally open **Her Drawing** to refresh memory — shapes are not letter labels.
3. Leave **Rear Doors Only** on for the eyewitness pass.
4. **Similar to Her Drawing** only reorders the search queue by a visual-similarity tag — it does **not** claim letters.
5. Tap **Start blind lineup**. One photo at a time; **company name and logo stay hidden**.
6. Tap **NO** / **MAYBE** / **FAMILIAR**.
7. After MAYBE/FAMILIAR you can **Show more like this** (same branding, still blind).
8. **NO** skips other photos with the same branding group (no reshuffle of rejected identical branding).
9. When finished, use **Review** (names revealed) and **Export report**.
10. Answers stay in this phone’s `localStorage` only.

Logo-only entries and broken images are excluded from the eyewitness lineup. Older / weak candidates remain in a low-priority pool (not deleted).

## Files

| Path | Purpose |
|------|---------|
| `index.html` | Blind lineup UI + review + admin/export |
| `companies.json` | Carriers + image metadata |
| `images/` | Public fleet photos |
| `assets/leslie-drawing-original.png` | ORIGINAL eyewitness drawing (do not alter) |
| `scripts/` | Build / expand / smoke tools |
| `CHANGELOG-LINEUP.md` | This lineup refactor notes |

## Reminder

This gallery is a **memory aid**. It is **not** evidence that any listed carrier was involved.
