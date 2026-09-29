#!/usr/bin/env python3
"""
Build a searchable trailer lineup gallery for Leslie hit-and-run ID.
- Seeds carriers from carriers_seed.json
- Fetches public images from Wikimedia Commons (primary) + company sites (robots-aware)
- Filters for white-ish trailers; tags lettering color hints
- Writes companies.json, images/, index.html
Rate-limited; lineup only — does not claim to identify the truck.
"""
from __future__ import annotations

import json
import os
import re
import time
import hashlib
import urllib.parse
from pathlib import Path
from typing import Any
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageStat
import io

ROOT = Path("/workspace/leslie-hitrun/trailer-gallery")
IMG_DIR = ROOT / "images"
SEED = ROOT / "scripts" / "carriers_seed.json"
UA = "LeslieHitrunGalleryBot/1.0 (research lineup; contact: local-box; respectful crawler)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "text/html,application/json,image/*"})

DELAY = 1.2  # seconds between HTTP requests
last_req = 0.0

def rate_wait():
    global last_req
    elapsed = time.time() - last_req
    if elapsed < DELAY:
        time.sleep(DELAY - elapsed)
    last_req = time.time()

def get(url: str, **kw) -> requests.Response | None:
    rate_wait()
    try:
        r = SESSION.get(url, timeout=25, **kw)
        if r.status_code == 200:
            return r
        print(f"  HTTP {r.status_code}: {url[:90]}")
    except Exception as e:
        print(f"  ERR {e}: {url[:90]}")
    return None

def robots_allowed(base: str, path: str) -> bool:
    try:
        rp = RobotFileParser()
        robots_url = urllib.parse.urljoin(base, "/robots.txt")
        rate_wait()
        r = SESSION.get(robots_url, timeout=10)
        if r.status_code != 200:
            return True  # no robots.txt => allow cautious fetch
        rp.parse(r.text.splitlines())
        return rp.can_fetch(UA, urllib.parse.urljoin(base, path))
    except Exception:
        return True

def analyze_image(data: bytes) -> dict:
    """Return whiteness score, dominant non-white hue hint, dims."""
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return {"ok": False}
    w, h = im.size
    if w < 120 or h < 80:
        return {"ok": False, "reason": "too_small"}
    # Downsample for analysis
    im_s = im.resize((min(320, w), min(240, h)), Image.Resampling.BILINEAR)
    pixels = list(im_s.getdata())
    n = len(pixels)
    whiteish = 0
    redish = 0
    orangish = 0
    bluish = 0
    greenish = 0
    dark_red = 0
    for r, g, b in pixels:
        mx = max(r, g, b)
        mn = min(r, g, b)
        sat = (mx - mn) / mx if mx else 0
        bright = (r + g + b) / 3
        if bright > 180 and sat < 0.18:
            whiteish += 1
            continue
        if bright < 40:
            continue
        # colored lettering / logos
        if r > g + 25 and r > b + 25:
            if r > 100 and g < 90 and b < 90:
                dark_red += 1
            elif r > 140 and 60 < g < 140 and b < 100:
                orangish += 1
            else:
                redish += 1
        elif b > r + 20 and b > g + 10:
            bluish += 1
        elif g > r + 20 and g > b + 10:
            greenish += 1
    white_ratio = whiteish / n
    color_counts = {
        "red": redish,
        "burgundy/dark-red": dark_red,
        "orange": orangish,
        "blue": bluish,
        "green": greenish,
    }
    lettering = max(color_counts, key=color_counts.get) if sum(color_counts.values()) > 30 else "unclear"
    if color_counts.get(lettering, 0) < 30:
        lettering = "unclear"
    # Prefer white trailers: white_ratio > 0.12 is soft keep; >0.25 strong
    keep = white_ratio >= 0.10
    return {
        "ok": True,
        "width": w,
        "height": h,
        "white_ratio": round(white_ratio, 3),
        "lettering_detected": lettering,
        "color_counts": color_counts,
        "keep_white": keep,
        "is_strong_white": white_ratio >= 0.22,
    }

def save_image(data: bytes, company_id: str, idx: int, ext: str = "jpg") -> str | None:
    name = f"{company_id}_{idx:02d}.{ext}"
    path = IMG_DIR / name
    try:
        im = Image.open(io.BytesIO(data))
        im = im.convert("RGB")
        # Cap size for gallery
        im.thumbnail((1200, 900), Image.Resampling.LANCZOS)
        im.save(path, "JPEG", quality=85)
        return name
    except Exception as e:
        print(f"  save fail: {e}")
        return None

def commons_search(query: str, limit: int = 8) -> list[dict]:
    """Search Wikimedia Commons for files."""
    api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,  # File
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 800,
    }
    r = get(api, params=params)
    if not r:
        return []
    data = r.json()
    pages = data.get("query", {}).get("pages", {})
    out = []
    for pid, page in pages.items():
        info = (page.get("imageinfo") or [None])[0]
        if not info:
            continue
        mime = info.get("mime", "")
        if not mime.startswith("image/"):
            continue
        if mime not in ("image/jpeg", "image/png", "image/webp"):
            continue
        url = info.get("thumburl") or info.get("url")
        title = page.get("title", "")
        # Skip logos-only tiny icons via size
        if info.get("size", 0) and info["size"] < 15000 and not info.get("thumburl"):
            continue
        out.append({
            "url": url,
            "full_url": info.get("url"),
            "title": title,
            "source": "wikimedia_commons",
            "page_url": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
        })
    return out

def scrape_company_page(website: str, company_id: str) -> list[dict]:
    """Fetch homepage + a few likely fleet paths; extract trailer-ish image URLs."""
    if not website or not website.startswith("http"):
        return []
    parsed = urllib.parse.urlparse(website)
    base = f"{parsed.scheme}://{parsed.netloc}"
    paths = ["/", "/about", "/about-us", "/fleet", "/equipment", "/services", "/company"]
    found = []
    seen = set()
    for path in paths:
        if not robots_allowed(base, path):
            print(f"  robots disallow {path}")
            continue
        url = urllib.parse.urljoin(base, path)
        r = get(url)
        if not r:
            continue
        ctype = r.headers.get("content-type", "")
        if "html" not in ctype:
            continue
        soup = BeautifulSoup(r.text, "lxml")
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
            if not src or src.startswith("data:"):
                continue
            full = urllib.parse.urljoin(url, src)
            if full in seen:
                continue
            seen.add(full)
            alt = (img.get("alt") or "") + " " + (img.get("title") or "")
            blob = (full + " " + alt).lower()
            # Heuristic: likely trailer/truck fleet photo
            keywords = ["trailer", "truck", "fleet", "semi", "dry van", "freight", "rig", "transport"]
            if any(k in blob for k in keywords) or any(k in path for k in ["fleet", "equipment"]):
                if any(full.lower().endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp")) or "image" in full.lower() or "/wp-content/" in full or "cdn" in full:
                    found.append({"url": full, "title": alt.strip() or path, "source": "company_site", "page_url": url})
        if len(found) >= 6:
            break
    return found[:8]

def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    carriers = json.load(open(SEED))
    # Fix/skip bad URLs
    results = []
    total_kept = 0
    total_fetched = 0

    for i, c in enumerate(carriers):
        cid = c["id"]
        name = c["name"]
        print(f"[{i+1}/{len(carriers)}] {name}")
        images_meta = []
        candidates = []

        # Wikimedia searches
        queries = [
            f'"{name.split("(")[0].strip()}" trailer truck',
            f"{name.split()[0]} Transportation semi trailer",
            f"{cid} truck trailer",
        ]
        # Special cases for better commons hits
        special = {
            "swift": ["Swift Transportation trailer", "Swift Transportation truck"],
            "werner": ["Werner Enterprises truck", "Werner trailer"],
            "jbhunt": ["J.B. Hunt trailer", "JB Hunt truck"],
            "schneider": ["Schneider National truck", "Schneider trailer"],
            "odfl": ["Old Dominion Freight Line trailer"],
            "fedexfreight": ["FedEx Freight trailer"],
            "walmart": ["Walmart truck trailer"],
            "amazon": ["Amazon semi trailer truck"],
            "penske": ["Penske truck"],
            "ryder": ["Ryder truck trailer"],
            "estes": ["Estes Express trailer"],
            "saia": ["Saia truck trailer"],
            "landstar": ["Landstar truck"],
            "crengland": ["C.R. England truck"],
            "prime": ["Prime Inc truck trailer"],
            "knight": ["Knight Transportation truck"],
            "uhaul": ["U-Haul truck"],
            "cocacola": ["Coca-Cola truck trailer"],
            "pepsico": ["Pepsi truck trailer", "Frito-Lay truck"],
            "sysco": ["Sysco truck"],
            "usfoods": ["US Foods truck"],
        }
        qlist = special.get(cid, queries[:2])
        for q in qlist:
            candidates.extend(commons_search(q, limit=6))
            if len(candidates) >= 10:
                break

        # Company site (limited)
        try:
            site_imgs = scrape_company_page(c.get("website", ""), cid)
            candidates.extend(site_imgs)
        except Exception as e:
            print(f"  site scrape err: {e}")

        # Dedup by url
        seen_u = set()
        uniq = []
        for cand in candidates:
            u = cand["url"]
            if u in seen_u:
                continue
            seen_u.add(u)
            uniq.append(cand)

        img_idx = 0
        for cand in uniq[:12]:
            r = get(cand["url"])
            if not r:
                continue
            total_fetched += 1
            data = r.content
            if len(data) < 4000:
                continue
            analysis = analyze_image(data)
            if not analysis.get("ok"):
                continue
            # Drop clearly non-white
            if not analysis.get("keep_white"):
                print(f"  drop non-white ({analysis.get('white_ratio')}): {cand['url'][:70]}")
                continue
            fname = save_image(data, cid, img_idx)
            if not fname:
                continue
            img_idx += 1
            total_kept += 1
            detected = analysis["lettering_detected"]
            # Prefer seed hint when detection unclear
            lettering_note = c.get("lettering_hint", "")
            if detected != "unclear":
                lettering_final = detected
            else:
                lettering_final = lettering_note or "unclear"
            images_meta.append({
                "file": fname,
                "source": cand.get("source"),
                "source_url": cand.get("page_url") or cand.get("url"),
                "image_url": cand.get("url"),
                "title": cand.get("title", ""),
                "white_ratio": analysis["white_ratio"],
                "lettering_detected": detected,
                "lettering_note": lettering_final,
                "is_strong_white": analysis.get("is_strong_white", False),
                "burgundy_candidate": (
                    "burgundy" in (lettering_final or "").lower()
                    or "dark-red" in (lettering_final or "").lower()
                    or detected == "burgundy/dark-red"
                    or (c.get("lettering_hint") or "").lower() in ("red", "red/burgundy", "burgundy")
                    and analysis.get("is_strong_white")
                ),
            })

        # Door text search terms: company name tokens
        door_text = [name]
        for part in re.split(r"[\s/().]+", name):
            if len(part) > 2:
                door_text.append(part)
        if c.get("lettering_hint"):
            door_text.append(c["lettering_hint"])

        results.append({
            "id": cid,
            "name": name,
            "website": c.get("website"),
            "region": c.get("region"),
            "notes": c.get("notes"),
            "lettering_hint": c.get("lettering_hint"),
            "priority": c.get("priority"),
            "door_text_keywords": list(dict.fromkeys(door_text)),
            "image_count": len(images_meta),
            "images": images_meta,
            "has_burgundy_hint": any(
                "burgundy" in (c.get("lettering_hint") or "").lower()
                or "red" == (c.get("lettering_hint") or "").lower()
                or (c.get("lettering_hint") or "").startswith("red")
                for _ in [0]
            ) and c.get("priority") == "high",
        })
        print(f"  kept {len(images_meta)} images")

    out = {
        "incident": {
            "date": "2026-09-28",
            "approx_time": "9:32 AM CT",
            "location": "Selma, TX — I-35",
            "description": "White semi trailer; rear-door writing believed burgundy/dark red. Lineup only — not an identification.",
        },
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "company_count": len(results),
        "image_count": total_kept,
        "companies": results,
    }
    json.dump(out, open(ROOT / "companies.json", "w"), indent=2)
    print(f"\nDONE: {len(results)} companies, {total_kept} images kept (fetched {total_fetched})")
    return out

if __name__ == "__main__":
    main()
