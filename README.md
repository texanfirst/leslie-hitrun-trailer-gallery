# Trailer lineup gallery — Selma I-35 hit-and-run

**Lineup only. This does not identify the truck.**

## Incident (for context)

- **When:** Monday 2026-09-28, ~9:32 AM CT  
- **Where:** Selma, TX — I-35  
- **What Leslie is looking for:** White semi *trailer*; writing on the **rear doors** believed **burgundy / dark red**

## Open the gallery

On this box:

```bash
# From a browser that can reach the box files, open:
/workspace/leslie-hitrun/trailer-gallery/index.html
```

Or serve locally:

```bash
cd /workspace/leslie-hitrun/trailer-gallery
python3 -m http.server 8765
# then open http://127.0.0.1:8765/
```

Files:

| Path | Purpose |
|------|---------|
| `index.html` | Searchable gallery UI |
| `companies.json` | Seeded carriers + image metadata |
| `images/` | Downloaded public trailer/fleet photos |
| `scripts/` | Seed list + scraper (for rebuilds) |

## How Leslie should flip through and eliminate

1. **Open `index.html`.** Default filters show **high-priority** carriers with **burgundy/red lettering hints** (common white dry vans on I-35).
2. **Search box:** type company name or words that might be on the door (`SWIFT`, `Werner`, `CRST`, `England`, etc.).
3. **Look at rear/side photos** — click a thumbnail to enlarge. Ask:
   - Is the trailer **white** (or mostly white)?
   - Is the **rear-door lettering** burgundy / dark red (vs orange, green, blue, black)?
   - Does the **word shape / logo** match what she remembers (even roughly)?
4. **Eliminate** carriers that are clearly wrong (wrong color scheme, wrong logo style, not a dry van, etc.) with **Eliminate (not a match)**. Choices stay in the browser (`localStorage`).
5. Mark uncertain ones **Maybe / keep looking**.
6. When filters feel too narrow, set priority to **All** and lettering to **Any** — some fleets use white trailers with customer brands.
7. **Companies with 0 photos** still appear with a note and website link — eliminate by known branding if the door text couldn’t be that name.
8. **Anything she keeps as “maybe”** is a tip for police / insurance, not a conclusion. Share: date/time/place, direction of travel, white trailer, burgundy/dark-red rear lettering, and any partial words she remembers.

### Quick visual checklist

| Keep looking if… | Eliminate if… |
|------------------|---------------|
| White (or very light) dry van / reefer | Orange, green, purple, yellow primary trailer |
| Large dark red / burgundy block letters on rear doors | Only blue/black logos, or no rear lettering like she saw |
| Name length / word count could match memory | Clearly different brand she would have recognized |

## What was built (method)

- Seeded **75** dry-van / I-35-relevant carriers (nationals + Texas/regional + some private fleets).
- Pulled **public** images from Wikimedia Commons and carrier websites.
- Checked `robots.txt`, used a polite User-Agent, and rate-limited requests.
- Kept images that looked **white-ish**; tagged lettering color when detectable; dropped clearly non-white frames.
- **Burgundy candidate** flags combine seed lettering hints + simple color analysis — they are **hints**, not proof.

## Rebuild / refresh

```bash
source /workspace/leslie-hitrun/.venv/bin/activate
python /workspace/leslie-hitrun/trailer-gallery/scripts/build_gallery.py
```

## Reminder

This gallery is a **memory aid**. It is **not** evidence that any listed carrier was involved.
