#!/usr/bin/env python3
"""Top up carriers that got 0 images; slower Commons-only queries."""
import json, time, io, urllib.parse
from pathlib import Path
import requests
from PIL import Image

ROOT = Path("/workspace/leslie-hitrun/trailer-gallery")
IMG_DIR = ROOT / "images"
UA = "LeslieHitrunGalleryBot/1.0 (research lineup; respectful crawler)"
S = requests.Session()
S.headers.update({"User-Agent": UA})
DELAY = 3.0
last = 0.0

def wait():
    global last
    e = time.time() - last
    if e < DELAY: time.sleep(DELAY - e)
    last = time.time()

def get(url, **kw):
    wait()
    try:
        r = S.get(url, timeout=30, **kw)
        return r if r.status_code == 200 else None
    except Exception as e:
        print("err", e)
        return None

QUERIES = {
    "pam": ["P.A.M. Transport truck", "PAM Transport trailer Arkansas"],
    "averitt": ["Averitt Express truck trailer", "Averitt Express semi"],
    "melton": ["Melton Truck Lines flatbed", "Melton Truck Lines trailer"],
    "hirschbach": ["Hirschbach Motor Lines truck", "Hirschbach reefer"],
    "dart": ["Dart Transit Company trailer", "Dart Transit truck Minnesota"],
    "mercer": ["Mercer Transportation truck Louisville", "Mercer Trans trailer"],
    "roadrunner": ["Roadrunner Transportation Systems truck", "Roadrunner LTL trailer"],
    "pittohio": ["PITT OHIO truck trailer", "Pitt Ohio Express"],
    "lonestar": ["Lone Star Transportation flatbed Texas", "LoneStar Transportation truck"],
    "bennett": ["Bennett Motor Express truck", "Bennett Motor Express trailer"],
}

def commons(q, limit=8):
    api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action":"query","format":"json","generator":"search","gsrsearch":q,
        "gsrnamespace":6,"gsrlimit":limit,"prop":"imageinfo",
        "iiprop":"url|size|mime","iiurlwidth":800,
    }
    r = get(api, params=params)
    if not r: return []
    pages = r.json().get("query",{}).get("pages",{})
    out=[]
    for p in pages.values():
        info=(p.get("imageinfo") or [None])[0]
        if not info: continue
        if not (info.get("mime") or "").startswith("image/"): continue
        url=info.get("thumburl") or info.get("url")
        out.append({"url":url,"title":p.get("title",""),
                    "page_url":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(p.get("title","").replace(" ","_")),
                    "source":"wikimedia_commons"})
    return out

def analyze(data):
    try: im=Image.open(io.BytesIO(data)).convert("RGB")
    except: return None
    w,h=im.size
    if w<120 or h<80: return None
    ims=im.resize((min(320,w),min(240,h)))
    pix=list(ims.getdata())
    n=len(pix); white=0
    for r,g,b in pix:
        mx=max(r,g,b); mn=min(r,g,b)
        sat=(mx-mn)/mx if mx else 0
        bright=(r+g+b)/3
        if bright>180 and sat<0.18: white+=1
    wr=white/n
    return wr

def save(data, cid, idx):
    name=f"{cid}_{idx:02d}.jpg"
    im=Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((1200,900), Image.Resampling.LANCZOS)
    im.save(IMG_DIR/name, "JPEG", quality=85)
    return name

data=json.load(open(ROOT/"companies.json"))
byid={c["id"]:c for c in data["companies"]}
added=0
for cid, qs in QUERIES.items():
    c=byid.get(cid)
    if not c or c["image_count"]>0: continue
    print("topup", cid)
    cands=[]; seen=set()
    for q in qs:
        for cand in commons(q):
            if cand["url"] in seen: continue
            seen.add(cand["url"]); cands.append(cand)
    idx=0
    for cand in cands[:10]:
        r=get(cand["url"])
        if not r or len(r.content)<4000: continue
        wr=analyze(r.content)
        if wr is None or wr<0.08: 
            print(f"  drop {wr}")
            continue
        # slightly looser for topup
        fname=save(r.content, cid, idx)
        c["images"].append({
            "file":fname,"source":cand["source"],"source_url":cand["page_url"],
            "image_url":cand["url"],"title":cand["title"],"white_ratio":round(wr,3),
            "lettering_detected":"unclear","lettering_note":c.get("lettering_hint") or "unclear",
            "is_strong_white":wr>=0.22,"burgundy_candidate":"red" in (c.get("lettering_hint") or ""),
        })
        idx+=1; added+=1
    c["image_count"]=len(c["images"])
    print(f"  now {c['image_count']}")

data["image_count"]=sum(c["image_count"] for c in data["companies"])
data["company_count"]=len(data["companies"])
json.dump(data, open(ROOT/"companies.json","w"), indent=2)
print("added", added, "total images", data["image_count"])
