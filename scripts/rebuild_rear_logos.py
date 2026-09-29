#!/usr/bin/env python3
"""Fast two-phase rear+logo rebuild. PYTHONUNBUFFERED recommended."""
from __future__ import annotations
import json, io, re, time, sys, urllib.parse
from pathlib import Path
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/workspace/leslie-hitrun/trailer-gallery")
IMG_DIR = ROOT / "images"
JSON_PATH = ROOT / "companies.json"
UA = "LeslieHitrunGalleryBot/1.0 (research lineup; contact: local-box; respectful crawler)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "text/html,application/json,image/*"})
DELAY = 1.15
last_req = 0.0

LESLIE_M_IDS = ["millis","mesillavalley","maytrucking","pam","mercer","maverick","marten","melton"]
HIGH_BURGUNDY_IDS = ["swift","knight","werner","roehl","usxpress","crst","crete","heartland","paschall","stevens","centralfreight","ffe"]

REAR_TITLE_RE = re.compile(r"\b(rear|reardoor|rear-door|back of|barn door|swing door|cargo door|trailer door|doors? closed|aft|back door)\b", re.I)
SIDE_TITLE_RE = re.compile(r"\b(side view|profile|highway|passing|cab |tractor|front view|three.?quarter|3/4|driver.?side|passenger.?side)\b", re.I)
LOGO_TITLE_RE = re.compile(r"\b(logo|wordmark|brand mark|emblem|favicon|lineup mark)\b", re.I)
NON_TRAILER_RE = re.compile(r"\b(whiteboard|office|application button|heatmap|lightning|railway journal|federal register|\.pdf|shovel|log truck 1938|aerial of distribution)\b", re.I)

def log(*a):
    print(*a, flush=True)

def rate_wait(m=1.0):
    global last_req
    need = DELAY * m
    e = time.time() - last_req
    if e < need: time.sleep(need - e)
    last_req = time.time()

def get(url, params=None, retries=2):
    for attempt in range(retries+1):
        rate_wait(1.0 + attempt*0.4)
        try:
            r = SESSION.get(url, params=params, timeout=28)
            if r.status_code == 200: return r
            if r.status_code == 429:
                log(f"  429 sleep ({url[:60]})")
                time.sleep(7 + attempt*4)
                continue
            log(f"  HTTP {r.status_code}: {url[:80]}")
            return None
        except Exception as e:
            log(f"  ERR {e}")
            time.sleep(1.5)
    return None

def robots_allowed(base, path):
    try:
        rp = RobotFileParser()
        rate_wait(0.4)
        r = SESSION.get(urllib.parse.urljoin(base, "/robots.txt"), timeout=8)
        if r.status_code != 200: return True
        rp.parse(r.text.splitlines())
        return rp.can_fetch(UA, urllib.parse.urljoin(base, path))
    except Exception:
        return True

def analyze_colors(data):
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return {"ok": False}
    w, h = im.size
    if w < 80 or h < 60: return {"ok": False}
    im_s = im.resize((min(320, w), min(240, h)), Image.Resampling.BILINEAR)
    pixels = list(im_s.getdata())
    n = len(pixels)
    whiteish = redish = orangish = bluish = greenish = dark_red = 0
    for r,g,b in pixels:
        mx, mn = max(r,g,b), min(r,g,b)
        sat = (mx-mn)/mx if mx else 0
        bright = (r+g+b)/3
        if bright > 180 and sat < 0.18:
            whiteish += 1; continue
        if bright < 40: continue
        if r > g+25 and r > b+25:
            if r > 100 and g < 90 and b < 90: dark_red += 1
            elif r > 140 and 60 < g < 140 and b < 100: orangish += 1
            else: redish += 1
        elif b > r+20 and b > g+10: bluish += 1
        elif g > r+20 and g > b+10: greenish += 1
    white_ratio = whiteish/n
    cc = {"red":redish,"burgundy/dark-red":dark_red,"orange":orangish,"blue":bluish,"green":greenish}
    lettering = max(cc, key=cc.get) if sum(cc.values())>30 else "unclear"
    if cc.get(lettering,0) < 30: lettering = "unclear"
    return {"ok":True,"width":w,"height":h,"white_ratio":round(white_ratio,3),
            "lettering_detected":lettering,"is_strong_white":white_ratio>=0.22,"keep_white":white_ratio>=0.08}

def cv_rear_score(path):
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return {"score":0.0,"guess":"other","white_ratio":0,"aspect":1}
    w,h = im.size
    aspect = w/max(h,1)
    im2 = im.resize((160,120), Image.Resampling.BILINEAR)
    pixels = list(im2.getdata())
    grid = [[(pixels[y*160+x][0]+pixels[y*160+x][1]+pixels[y*160+x][2])/3 for x in range(160)] for y in range(120)]
    white = sum(1 for r,g,b in pixels if (r+g+b)/3>170 and max(r,g,b)-min(r,g,b)<40)
    white_ratio = white/len(pixels)
    cx=80
    mid = sum(sum(grid[y][cx-2:cx+2]) for y in range(20,100))/(80*4)
    left = sum(sum(grid[y][cx-18:cx-10]) for y in range(20,100))/(80*8)
    right = sum(sum(grid[y][cx+10:cx+18]) for y in range(20,100))/(80*8)
    seam = max(0.0, (left+right)/2 - mid)
    bottom = sum(sum(grid[y]) for y in range(100,120))/(20*160)
    score = white_ratio*2.2 + (seam/35.0) - max(0, aspect-1.55)*0.55
    if bottom < 90 and white_ratio > 0.25: score += 0.25
    guess = "other"
    if score >= 1.15 and white_ratio >= 0.18 and aspect < 1.85: guess = "rear"
    elif aspect >= 1.7 or (white_ratio > 0.12 and aspect > 1.4): guess = "side"
    return {"score":round(score,3),"white_ratio":round(white_ratio,3),"seam":round(seam,1),
            "aspect":round(aspect,2),"guess":guess}

def classify_view(meta, path=None):
    title = (meta.get("title") or "") + " " + (meta.get("file") or "")
    src = meta.get("source") or ""
    f = meta.get("file") or ""
    if meta.get("view")=="logo" or LOGO_TITLE_RE.search(title) or f.endswith("_logo.png") or "_logo." in f:
        return "logo"
    if NON_TRAILER_RE.search(title) and not REAR_TITLE_RE.search(title):
        return "other"
    if REAR_TITLE_RE.search(title): return "rear"
    if SIDE_TITLE_RE.search(title): return "side"
    if path and path.exists():
        cv = cv_rear_score(path)
        if cv["guess"]=="rear" and cv["score"]>=1.2: return "rear"
        if cv["guess"]=="side": return "side"
        if cv["score"]>=1.0 and cv["white_ratio"]>=0.25 and cv["aspect"]<1.5: return "rear"
    return "side" if src=="company_site" else "other"

def save_jpeg(data, company_id, idx):
    name = f"{company_id}_{idx:02d}.jpg"
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((1200,900), Image.Resampling.LANCZOS)
        im.save(IMG_DIR/name, "JPEG", quality=85)
        return name
    except Exception as e:
        log(f"  save fail: {e}"); return None

def save_logo_bytes(data, company_id):
    name = f"{company_id}_logo.png"
    try:
        im = Image.open(io.BytesIO(data))
        if im.mode not in ("RGB","RGBA"): im = im.convert("RGBA")
        im.thumbnail((400,400), Image.Resampling.LANCZOS)
        if im.mode == "RGBA":
            bg = Image.new("RGBA", im.size, (255,255,255,255))
            bg.paste(im, mask=im.split()[-1]); im = bg.convert("RGB")
        else:
            im = im.convert("RGB")
        im.save(IMG_DIR/name, "PNG")
        return name
    except Exception as e:
        log(f"  logo save fail: {e}"); return None

def make_text_logo(company_id, name, hint=""):
    fname = f"{company_id}_logo.png"
    hint_l = (hint or "").lower()
    if "burgundy" in hint_l or hint_l=="red" or hint_l.startswith("red"): accent=(139,35,55)
    elif "orange" in hint_l: accent=(210,100,30)
    elif "blue" in hint_l: accent=(40,80,160)
    elif "green" in hint_l: accent=(40,120,70)
    else: accent=(196,92,74)
    words = re.findall(r"[A-Za-z0-9.]+", name)
    label = (" ".join(words[:2]) if len(words)>=2 and len(words[0])<=3 else (words[0] if words else company_id)).upper()
    if len(label)>14: label=label[:12]+"…"
    W,H=360,160
    im = Image.new("RGB",(W,H),(255,255,255))
    draw = ImageDraw.Draw(im)
    draw.rectangle([0,0,W-1,H-1], outline=accent, width=6)
    draw.rectangle([10,10,W-11,H-11], outline=accent, width=2)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font = small = ImageFont.load_default()
    bbox = draw.textbbox((0,0), label, font=font)
    tw,th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((W-tw)/2,(H-th)/2-8), label, fill=accent, font=font)
    sb = draw.textbbox((0,0), "lineup mark", font=small)
    draw.text(((W-(sb[2]-sb[0]))/2, H-36), "lineup mark", fill=(120,120,120), font=small)
    im.save(IMG_DIR/fname, "PNG")
    return fname

def logo_meta(company, fname, source, url=""):
    return {
        "file": fname, "source": source, "source_url": company.get("website") or url,
        "image_url": url, "title": f"{company['name']} logo", "view": "logo",
        "white_ratio": 1.0, "lettering_detected": "n/a",
        "lettering_note": company.get("lettering_hint") or "",
        "is_strong_white": True, "burgundy_candidate": False,
    }

def ensure_logo(company):
    cid = company["id"]
    path = IMG_DIR / f"{cid}_logo.png"
    website = company.get("website") or ""
    domain = urllib.parse.urlparse(website).netloc.replace("www.","") if website else ""
    # Prefer existing good logo
    if path.exists() and path.stat().st_size > 2000:
        return logo_meta(company, path.name, "existing")
    # Try commons logo (only for priority — caller decides)
    # Favicon
    if domain:
        r = get(f"https://www.google.com/s2/favicons?domain={domain}&sz=128")
        if r and len(r.content) > 200:
            fname = save_logo_bytes(r.content, cid)
            if fname and (IMG_DIR/fname).stat().st_size > 400:
                return logo_meta(company, fname, "google_favicon", r.url)
    fname = make_text_logo(cid, company["name"], company.get("lettering_hint") or "")
    return logo_meta(company, fname, "generated_mark")

def commons_logo(company):
    name = company["name"]
    api = "https://commons.wikimedia.org/w/api.php"
    for q in [f'"{name}" logo', f"{name.split()[0]} logo svg"]:
        r = get(api, params={"action":"query","format":"json","generator":"search","gsrsearch":q,
                             "gsrnamespace":6,"gsrlimit":4,"prop":"imageinfo","iiprop":"url|size|mime","iiurlwidth":400})
        if not r: continue
        for page in r.json().get("query",{}).get("pages",{}).values():
            info = (page.get("imageinfo") or [None])[0]
            if not info: continue
            title = page.get("title","")
            if "logo" not in title.lower() and info.get("mime")!="image/svg+xml": continue
            url = info.get("thumburl") or info.get("url")
            rr = get(url)
            if not rr: continue
            fname = save_logo_bytes(rr.content, company["id"])
            if fname:
                return logo_meta(company, fname, "wikimedia_commons", url)
        time.sleep(0.2)
    return None

def openverse_search(query, limit=8):
    r = get("https://api.openverse.org/v1/images/", params={"q":query,"page_size":min(limit,15),"mature":"false"})
    if not r: return []
    out=[]
    for res in r.json().get("results",[]):
        url=res.get("url")
        if not url: continue
        out.append({"url":url,"title":res.get("title") or "","source":f"openverse/{res.get('source') or 'cc'}",
                    "page_url":res.get("foreign_landing_url") or url,"license":(res.get("license") or "").lower()})
    return out

def commons_search(query, limit=5):
    api="https://commons.wikimedia.org/w/api.php"
    r=get(api, params={"action":"query","format":"json","generator":"search","gsrsearch":query,
                       "gsrnamespace":6,"gsrlimit":limit,"prop":"imageinfo","iiprop":"url|size|mime","iiurlwidth":900})
    if not r: return []
    out=[]
    for page in r.json().get("query",{}).get("pages",{}).values():
        info=(page.get("imageinfo") or [None])[0]
        if not info: continue
        if info.get("mime") not in ("image/jpeg","image/png","image/webp"): continue
        title=page.get("title","")
        out.append({"url":info.get("thumburl") or info.get("url"),"title":title,"source":"wikimedia_commons",
                    "page_url":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_"))})
    return out

def scrape_site(website):
    if not website or not website.startswith("http"): return []
    parsed=urllib.parse.urlparse(website)
    base=f"{parsed.scheme}://{parsed.netloc}"
    found=[]; seen=set()
    for path in ["/", "/fleet", "/equipment", "/about", "/about-us"]:
        if not robots_allowed(base, path): continue
        r=get(urllib.parse.urljoin(base, path))
        if not r or "html" not in r.headers.get("content-type",""): continue
        soup=BeautifulSoup(r.text,"lxml")
        for img in soup.find_all("img"):
            src=img.get("src") or img.get("data-src") or ""
            if not src or src.startswith("data:"): continue
            full=urllib.parse.urljoin(urllib.parse.urljoin(base,path), src)
            if full in seen: continue
            seen.add(full)
            alt=((img.get("alt") or "")+" "+(img.get("title") or "")).strip()
            blob=(full+" "+alt+" "+path).lower()
            rearish=any(k in blob for k in ("rear","door","doors","back-of","tail"))
            trailerish=any(k in blob for k in ("trailer","truck","fleet","semi","van","freight"))
            if rearish or trailerish:
                found.append({"url":full,"title":alt or path,"source":"company_site",
                              "page_url":urllib.parse.urljoin(base,path),
                              "view":"rear" if rearish else "side"})
        if len(found)>=8: break
    return found[:10]

REAR_Q = {
    "swift": ["Swift Transportation trailer", "Swift truck trailer rear"],
    "werner": ["Werner Enterprises trailer", "Werner truck trailer"],
    "knight": ["Knight Transportation trailer", "Knight truck trailer"],
    "roehl": ["Roehl Transport trailer", "Roehl truck"],
    "usxpress": ["US Xpress trailer", "U.S. Xpress truck"],
    "crst": ["CRST trailer truck", "CRST Transportation"],
    "crete": ["Crete Carrier trailer", "Crete truck trailer"],
    "heartland": ["Heartland Express trailer", "Heartland Express truck"],
    "stevens": ["Stevens Transport trailer", "Stevens Transport truck"],
    "paschall": ["Paschall Truck Lines trailer", "Paschall truck"],
    "centralfreight": ["Central Freight Lines trailer", "Central Freight truck"],
    "ffe": ["Frozen Food Express trailer", "FFE truck trailer"],
    "millis": ["Millis Transfer truck", "Millis Transfer trailer"],
    "mesillavalley": ["Mesilla Valley Transportation trailer", "MVT truck trailer"],
    "maytrucking": ["May Trucking trailer", "May Trucking Company truck"],
    "pam": ["PAM Transport trailer", "P.A.M. Transport truck"],
    "mercer": ["Mercer Transportation trailer", "Mercer truck trailer"],
    "maverick": ["Maverick Transportation truck", "Maverick trailer"],
    "marten": ["Marten Transport trailer", "Marten Transport truck"],
    "melton": ["Melton Truck Lines", "Melton truck trailer"],
}

def next_idx(cid, files):
    n=0
    while f"{cid}_{n:02d}.jpg" in files: n+=1
    return n

def phase1_classify_and_logos(companies):
    log("=== PHASE 1: classify existing + logos ===")
    out=[]
    for i,c in enumerate(companies):
        cid=c["id"]
        log(f"[{i+1}/{len(companies)}] classify/logo {cid}")
        images=[]
        for im in c.get("images") or []:
            f=im.get("file"); path=IMG_DIR/f if f else None
            if not path or not path.exists(): continue
            view=classify_view(im, path)
            im=dict(im); im["view"]=view
            if view=="side": im["side_only_note"]="side only — not rear"
            else: im.pop("side_only_note", None)
            title=im.get("title") or ""
            if view=="other" and NON_TRAILER_RE.search(title):
                log(f"  drop junk {f}")
                path.unlink(missing_ok=True)
                continue
            if view=="logo": continue  # logos handled separately
            images.append(im)
        # Priority commons logo attempt
        logo=None
        if cid in LESLIE_M_IDS or cid in HIGH_BURGUNDY_IDS:
            logo=commons_logo(c)
        if not logo:
            logo=ensure_logo(c)
        log(f"  logo={logo['source']} file={logo['file']}")

        rear=[x for x in images if x["view"]=="rear"]
        side=[x for x in images if x["view"]=="side"]
        other=[x for x in images if x["view"] not in ("rear","side","logo")]
        if rear:
            side=side[:2]
            for s in side: s["side_only_note"]="side only — not rear"
            other=[]
        else:
            for s in side: s["side_only_note"]="side only — not rear"
            side=side[:4]; other=other[:1]
        final=[logo]+rear+side+other
        # dedup
        seen=set(); dedup=[]
        for im in final:
            if im["file"] in seen: continue
            seen.add(im["file"]); dedup.append(im)
            if not im.get("side_only_note"): im.pop("side_only_note", None)
        c=dict(c)
        c["images"]=dedup
        c["image_count"]=sum(1 for im in dedup if im.get("view")!="logo")
        c["rear_image_count"]=sum(1 for im in dedup if im.get("view")=="rear")
        c["has_logo"]=True
        c["has_burgundy_hint"]=bool(c.get("has_burgundy_hint") or "red" in (c.get("lettering_hint") or "").lower() or "burgundy" in (c.get("lettering_hint") or "").lower())
        out.append(c)
    return out

def phase2_scrape_rear(companies):
    log("=== PHASE 2: scrape rear for Leslie M + burgundy ===")
    by_id={c["id"]:c for c in companies}
    priority=LESLIE_M_IDS + HIGH_BURGUNDY_IDS
    for i,cid in enumerate(priority):
        c=by_id.get(cid)
        if not c: continue
        log(f"[{i+1}/{len(priority)}] scrape rear {cid}")
        existing=set(p.name for p in IMG_DIR.glob(f"{cid}_*"))
        have_rear=sum(1 for im in c["images"] if im.get("view")=="rear")
        if have_rear>=2:
            log(f"  already {have_rear} rear — skip scrape")
            continue
        cands=[]
        for q in REAR_Q.get(cid, [f"{c['name']} trailer", f"{c['name']} truck"])[:2]:
            cands.extend(openverse_search(q, limit=8))
            cands.extend(commons_search(q, limit=4))
        try:
            cands.extend(scrape_site(c.get("website") or ""))
        except Exception as e:
            log(f"  site err {e}")
        # prefer rear-titled
        seen_u=set(im.get("image_url") for im in c["images"] if im.get("image_url"))
        uniq=[]
        for cand in cands:
            u=cand.get("url")
            if not u or u in seen_u: continue
            seen_u.add(u); uniq.append(cand)
        uniq.sort(key=lambda x: (0 if REAR_TITLE_RE.search(x.get("title") or "") or x.get("view")=="rear" else 1))
        idx=next_idx(cid, existing)
        added=0
        target=3 if have_rear==0 else 2
        new_imgs=list(c["images"])
        for cand in uniq:
            if added>=target: break
            r=get(cand["url"])
            if not r or len(r.content)<3000: continue
            analysis=analyze_colors(r.content)
            if not analysis.get("ok"): continue
            # permissive if rear title
            is_rear_title=bool(REAR_TITLE_RE.search(cand.get("title") or "") or cand.get("view")=="rear")
            if not is_rear_title and not analysis.get("keep_white"): continue
            fname=save_jpeg(r.content, cid, idx)
            if not fname: continue
            existing.add(fname)
            path=IMG_DIR/fname
            view=cand.get("view") or classify_view({"title":cand.get("title"),"file":fname,"source":cand.get("source")}, path)
            if view=="logo": view="other"
            detected=analysis["lettering_detected"]
            note=c.get("lettering_hint") or ""
            lettering_final=detected if detected!="unclear" else (note or "unclear")
            meta={
                "file":fname,"source":cand.get("source"),"source_url":cand.get("page_url") or cand["url"],
                "image_url":cand["url"],"title":cand.get("title") or "","view":view,
                "white_ratio":analysis["white_ratio"],"lettering_detected":detected,
                "lettering_note":lettering_final,"is_strong_white":analysis.get("is_strong_white",False),
                "burgundy_candidate":(
                    "burgundy" in lettering_final.lower() or "dark-red" in lettering_final.lower()
                    or detected=="burgundy/dark-red"
                    or ((c.get("lettering_hint") or "").lower() in ("red","red/burgundy","burgundy") and analysis.get("is_strong_white"))
                ),
            }
            if view=="side": meta["side_only_note"]="side only — not rear"
            if cand.get("license"): meta["license"]=cand["license"]
            new_imgs.append(meta)
            idx+=1; added+=1
            log(f"  + {fname} view={view} :: {(cand.get('title') or '')[:55]}")
        # re-pack
        logo=[im for im in new_imgs if im.get("view")=="logo"][:1]
        rear=[im for im in new_imgs if im.get("view")=="rear"]
        side=[im for im in new_imgs if im.get("view")=="side"]
        other=[im for im in new_imgs if im.get("view") not in ("rear","side","logo")]
        if rear:
            side=side[:2]; other=[]
        else:
            side=side[:4]; other=other[:1]
        for s in side: s["side_only_note"]="side only — not rear"
        final=[]; seen=set()
        for im in logo+rear+side+other:
            if im["file"] in seen: continue
            seen.add(im["file"])
            if not im.get("side_only_note"): im.pop("side_only_note", None)
            final.append(im)
        c["images"]=final
        c["image_count"]=sum(1 for im in final if im.get("view")!="logo")
        c["rear_image_count"]=sum(1 for im in final if im.get("view")=="rear")
        c["has_logo"]=bool(logo)
        by_id[cid]=c
    return [by_id[c["id"]] for c in companies]

def write_summary(companies):
    with_rear=[c for c in companies if c.get("rear_image_count",0)>=1]
    logo_only=[c for c in companies if c.get("has_logo") and c.get("image_count",0)==0]
    missing=[c for c in companies if not c.get("has_logo") and c.get("image_count",0)==0]
    side_only=[c for c in companies if c.get("image_count",0)>0 and c.get("rear_image_count",0)==0]
    summary={
        "companies_with_rear": len(with_rear),
        "logo_only": len(logo_only),
        "side_only_no_rear": len(side_only),
        "still_missing": len(missing),
        "total_logos": sum(1 for c in companies if c.get("has_logo")),
        "total_trailer_images": sum(c.get("image_count",0) for c in companies),
        "total_rear_images": sum(c.get("rear_image_count",0) for c in companies),
        "rear_ids":[c["id"] for c in with_rear],
        "logo_only_ids":[c["id"] for c in logo_only],
        "missing_ids":[c["id"] for c in missing],
        "side_only_ids":[c["id"] for c in side_only],
        "leslie_m_rear":{cid: by_rear_count(companies,cid) for cid in LESLIE_M_IDS},
        "burgundy_rear":{cid: by_rear_count(companies,cid) for cid in HIGH_BURGUNDY_IDS},
    }
    json.dump(summary, open(ROOT/"scripts"/"rear_rebuild_summary.json","w"), indent=2)
    return summary

def by_rear_count(companies, cid):
    for c in companies:
        if c["id"]==cid: return c.get("rear_image_count",0)
    return 0

def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    data=json.load(open(JSON_PATH))
    companies=data["companies"]
    companies=phase1_classify_and_logos(companies)
    # checkpoint
    _write(data, companies)
    log("phase1 checkpoint written")
    companies=phase2_scrape_rear(companies)
    _write(data, companies)
    summary=write_summary(companies)
    log("==== SUMMARY ====")
    log(json.dumps(summary, indent=2))
    return summary

def _write(data, companies):
    total_imgs=sum(c["image_count"] for c in companies)
    total_rear=sum(c.get("rear_image_count",0) for c in companies)
    total_logos=sum(1 for c in companies if c.get("has_logo"))
    out={
        "incident": data.get("incident"),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "rebuild": "rear_and_logos",
        "company_count": len(companies),
        "image_count": total_imgs,
        "rear_image_count": total_rear,
        "logo_count": total_logos,
        "companies": companies,
    }
    json.dump(out, open(JSON_PATH,"w"), indent=2)

if __name__=="__main__":
    main()
