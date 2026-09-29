#!/usr/bin/env python3
"""Enrich companies.json for blind lineup + expand SA/I-35/Laredo carriers."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/workspace/leslie-hitrun/trailer-gallery")
JSON_PATH = ROOT / "companies.json"

# Companies that visually/reputationally may have subtle/simple/script rear marks
# (organization only — NOT letter identification)
SIMILAR_DRAWING_IDS = {
    "millis", "mesillavalley", "maytrucking", "pam", "paschall", "stevens",
    "crengland", "ffe", "centralfreight", "heartland", "roehl", "knight",
    "heb", "brownintegrated", "papertransport", "anderson", "lonestar",
    "pridetransport", "epes", "boydbros", "westernflyer", "nussbaum",
    "cfi", "freymiller", "navajo", "hogan", "redclassic", "gulfwinds",
}

# Demote former M-dominant shortlist to optional similar_to_drawing only
OLD_M_IDS = {"millis","mesillavalley","maytrucking","pam","mercer","maverick","marten","melton","millertrans"}

NEW_CARRIERS = [
  {"id":"heb","name":"H-E-B","website":"https://www.heb.com","region":"texas","corridor":"sa_i35",
   "notes":"San Antonio–based private fleet; white trailers common on I-35 / SA metro","lettering_hint":"red/black",
   "priority":"high","branding_group":"heb","lettering_style":"simple"},
  {"id":"target","name":"Target (private fleet)","website":"https://corporate.target.com","region":"private","corridor":"national",
   "notes":"White/red Target trailers; common on I-35","lettering_hint":"red","priority":"medium","branding_group":"target","lettering_style":"block"},
  {"id":"costco","name":"Costco (private fleet)","website":"https://www.costco.com","region":"private","corridor":"national",
   "notes":"White Costco trailers","lettering_hint":"red/black","priority":"medium","branding_group":"costco","lettering_style":"block"},
  {"id":"homedepot","name":"The Home Depot (private fleet)","website":"https://www.homedepot.com","region":"private","corridor":"national",
   "notes":"Orange branding dominant — often eliminate on color","lettering_hint":"orange","priority":"low","branding_group":"homedepot","lettering_style":"block"},
  {"id":"lowes","name":"Lowe's (private fleet)","website":"https://www.lowes.com","region":"private","corridor":"national",
   "notes":"Blue branding dominant — often eliminate on color","lettering_hint":"blue","priority":"low","branding_group":"lowes","lettering_style":"block"},
  {"id":"dollargeneral","name":"Dollar General (private fleet)","website":"https://www.dollargeneral.com","region":"private","corridor":"national",
   "notes":"Yellow/black branding often","lettering_hint":"yellow/black","priority":"low","branding_group":"dollargeneral","lettering_style":"block"},
  {"id":"cfi","name":"CFI (Contract Freighters Inc.)","website":"https://www.cfidrive.com","region":"national","corridor":"i35",
   "notes":"Joplin-based; heavy I-35 corridor dry van","lettering_hint":"red/black","priority":"high","branding_group":"cfi","lettering_style":"simple"},
  {"id":"westernexpress","name":"Western Express","website":"https://www.westernexp.com","region":"national","corridor":"national",
   "notes":"Nashville; white dry vans nationwide","lettering_hint":"red/black","priority":"medium","branding_group":"westernexpress","lettering_style":"block"},
  {"id":"nussbaum","name":"Nussbaum Transportation","website":"https://www.nussbaum.com","region":"regional","corridor":"national",
   "notes":"White trailers; Illinois-based regional/national","lettering_hint":"red","priority":"medium","branding_group":"nussbaum","lettering_style":"simple"},
  {"id":"decker","name":"Decker Truck Line","website":"https://www.deckertrucks.com","region":"regional","corridor":"national",
   "notes":"Iowa; dry van / refrigerated","lettering_hint":"red/black","priority":"medium","branding_group":"decker","lettering_style":"block"},
  {"id":"freymiller","name":"Freymiller","website":"https://www.freymiller.com","region":"national","corridor":"i35",
   "notes":"Oklahoma City; temperature-controlled; I-35 corridor","lettering_hint":"red/blue","priority":"medium","branding_group":"freymiller","lettering_style":"simple"},
  {"id":"navajo","name":"Navajo Express","website":"https://www.navajoexpress.com","region":"national","corridor":"national",
   "notes":"Denver; refrigerated / dry","lettering_hint":"red/black","priority":"medium","branding_group":"navajo","lettering_style":"block"},
  {"id":"hogan","name":"Hogan Transportation","website":"https://www.hogan1.com","region":"national","corridor":"i35",
   "notes":"St. Louis; dry van common on central corridors","lettering_hint":"red/black","priority":"medium","branding_group":"hogan","lettering_style":"block"},
  {"id":"interstate","name":"Interstate Distributor Co.","website":"https://www.intd.com","region":"national","corridor":"national",
   "notes":"Tacoma; dedicated / dry van","lettering_hint":"blue/red","priority":"low","branding_group":"interstate","lettering_style":"block"},
  {"id":"challenger","name":"Challenger Motor Freight","website":"https://www.challenger.com","region":"national","corridor":"national",
   "notes":"Canadian carrier operating into US","lettering_hint":"red/black","priority":"low","branding_group":"challenger","lettering_style":"block"},
  {"id":"bison","name":"Bison Transport","website":"https://www.bisontransport.com","region":"national","corridor":"national",
   "notes":"Canadian; cross-border dry van","lettering_hint":"red/black","priority":"low","branding_group":"bison","lettering_style":"block"},
  {"id":"cowan","name":"Cowan Systems","website":"https://www.cowan.fr","region":"regional","corridor":"national",
   "notes":"Baltimore regional / dedicated","lettering_hint":"red","priority":"low","branding_group":"cowan","lettering_style":"block"},
  {"id":"wilsonlogistics","name":"Wilson Logistics","website":"https://www.wilsonlogistics.com","region":"regional","corridor":"national",
   "notes":"Oregon; dry van","lettering_hint":"green/black","priority":"low","branding_group":"wilsonlogistics","lettering_style":"block"},
  {"id":"armstrong","name":"Armstrong Transport Group","website":"https://www.armstrongtransport.com","region":"broker","corridor":"national",
   "notes":"Broker — equipment varies; low ID value","lettering_hint":"unknown","priority":"low","branding_group":"armstrong","lettering_style":"unknown"},
  {"id":"redclassic","name":"Red Classic","website":"https://www.redclassic.com","region":"regional","corridor":"i35",
   "notes":"Charlotte; refrigerated; southeast/central","lettering_hint":"red","priority":"medium","branding_group":"redclassic","lettering_style":"simple"},
  {"id":"gulfwinds","name":"Gulf Winds International","website":"https://www.gulfwinds.com","region":"texas","corridor":"laredo",
   "notes":"Houston / border freight; TX–Mexico corridor","lettering_hint":"blue/red","priority":"high","branding_group":"gulfwinds","lettering_style":"simple"},
  {"id":"alamotransport","name":"Alamo Transportation (TX regional)","website":"https://www.google.com/search?q=Alamo+Transportation+Texas+trucking",
   "region":"texas","corridor":"sa_i35","notes":"SA-area regional name pool — verify branding before relying","lettering_hint":"unknown","priority":"medium","branding_group":"alamotransport","lettering_style":"unknown"},
  {"id":"borderfreight","name":"Border freight / Laredo pool (generic)","website":"https://www.google.com/search?q=Laredo+TX+trucking+companies+white+trailer",
   "region":"texas","corridor":"laredo","notes":"Placeholder pool for Laredo white dry vans with small rear marks — photos TBD","lettering_hint":"burgundy/dark-red possible","priority":"medium","branding_group":"borderfreight","lettering_style":"simple"},
  {"id":"transportescastores","name":"Transportes Castores","website":"https://www.castores.com.mx","region":"regional","corridor":"laredo",
   "notes":"Major MX carrier; Laredo/border crossings common","lettering_hint":"red/yellow","priority":"medium","branding_group":"castores","lettering_style":"block"},
  {"id":"ceva","name":"CEVA Logistics","website":"https://www.cevalogistics.com","region":"national","corridor":"national",
   "notes":"3PL; varied equipment","lettering_hint":"red/black","priority":"low","branding_group":"ceva","lettering_style":"block"},
  {"id":"dbschenker","name":"DB Schenker","website":"https://www.dbschenker.com","region":"national","corridor":"national",
   "notes":"Global 3PL; white trailers with Schenker marks","lettering_hint":"magenta/pink","priority":"low","branding_group":"dbschenker","lettering_style":"block"},
  {"id":"dhlsupply","name":"DHL Supply Chain","website":"https://www.dhl.com","region":"national","corridor":"national",
   "notes":"Yellow/red DHL branding often distinctive","lettering_hint":"yellow/red","priority":"low","branding_group":"dhl","lettering_style":"block"},
  {"id":"martinsystems","name":"Martin Transportation Systems","website":"https://www.martinstrans.com","region":"regional","corridor":"national",
   "notes":"Michigan; automotive / dry van","lettering_hint":"red/black","priority":"low","branding_group":"martinsystems","lettering_style":"block"},
  {"id":"tysonfoods","name":"Tyson Foods (private fleet)","website":"https://www.tysonfoods.com","region":"private","corridor":"i35",
   "notes":"Refrigerated food fleet; I-35 relevant","lettering_hint":"red/black","priority":"medium","branding_group":"tyson","lettering_style":"block"},
  {"id":"cargill","name":"Cargill (private fleet)","website":"https://www.cargill.com","region":"private","corridor":"national",
   "notes":"Private fleet; varied trailers","lettering_hint":"black/green","priority":"low","branding_group":"cargill","lettering_style":"block"},
  {"id":"kehe","name":"KeHE Distributors","website":"https://www.kehe.com","region":"private","corridor":"national",
   "notes":"Grocery distributor trailers","lettering_hint":"blue/green","priority":"low","branding_group":"kehe","lettering_style":"block"},
  {"id":"centraltransport","name":"Central Transport (LTL)","website":"https://www.centraltransport.com","region":"national","corridor":"national",
   "notes":"LTL; not Central Freight Lines (TX) — different company","lettering_hint":"green/black","priority":"low","branding_group":"centraltransport","lettering_style":"block"},
  {"id":"dotfoods","name":"Dot Transportation / Dot Foods","website":"https://www.dotfoods.com","region":"private","corridor":"national",
   "notes":"Foodservice redistributor fleet","lettering_hint":"red/black","priority":"medium","branding_group":"dotfoods","lettering_style":"block"},
  {"id":"shaffer","name":"Shaffer Trucking","website":"https://www.shaffertrucking.com","region":"regional","corridor":"national",
   "notes":"Refrigerated; part of Crete family historically","lettering_hint":"red","priority":"medium","branding_group":"crete_family","lettering_style":"block"},
  {"id":"hunttransport","name":"Hunt Transportation","website":"https://www.hunttransportation.com","region":"regional","corridor":"national",
   "notes":"Flatbed-heavy — weak dry-van rear-door fit","lettering_hint":"red/black","priority":"low","branding_group":"hunttransport","lettering_style":"block"},
  {"id":"rivercitytx","name":"River City / SA metro carriers pool","website":"https://www.google.com/search?q=San+Antonio+TX+trucking+companies+dry+van",
   "region":"texas","corridor":"sa_i35","notes":"SA metro dry-van pool for further photo collection","lettering_hint":"unknown","priority":"medium","branding_group":"rivercitytx","lettering_style":"unknown"},
  {"id":"i35corridor","name":"I-35 corridor regional pool","website":"https://www.google.com/search?q=I-35+Texas+trucking+white+trailer+burgundy",
   "region":"texas","corridor":"i35","notes":"Catch-all for additional I-35 white trailers with subtle dark-red rear marks","lettering_hint":"burgundy/dark-red possible","priority":"medium","branding_group":"i35corridor","lettering_style":"simple"},
  {"id":"laredoline","name":"Laredo line-haul carriers pool","website":"https://www.google.com/search?q=Laredo+TX+line+haul+truck+trailer",
   "region":"texas","corridor":"laredo","notes":"Laredo line-haul white dry vans — photos TBD from public sources","lettering_hint":"unknown","priority":"medium","branding_group":"laredoline","lettering_style":"simple"},
  {"id":"sgt","name":"SGT / Southwest freight (TX–MX)","website":"https://www.google.com/search?q=Southwest+freight+Laredo+trucking",
   "region":"texas","corridor":"laredo","notes":"Border Southwest freight names — verify before treating as ID","lettering_hint":"unknown","priority":"low","branding_group":"sgt","lettering_style":"unknown"},
  {"id":"whataburgerdist","name":"Whataburger distribution (private)","website":"https://www.whataburger.com","region":"texas","corridor":"sa_i35",
   "notes":"TX brand; distribution trailers may appear locally","lettering_hint":"orange/white","priority":"low","branding_group":"whataburger","lettering_style":"block"},
]

CORRIDOR_MAP = {
  "centralfreight":"texas","ffe":"texas","lonestar":"texas","brownintegrated":"texas",
  "mesillavalley":"laredo","millis":"i35","maytrucking":"i35","heb":"sa_i35",
  "swift":"i35","werner":"i35","knight":"i35","jbhunt":"i35","schneider":"i35",
  "usxpress":"i35","crete":"i35","roehl":"i35","crst":"i35","heartland":"i35",
  "walmart":"i35","amazon":"i35","sysco":"i35","pepsico":"i35","cocacola":"i35",
  "penske":"i35","ryder":"i35","saia":"i35","estes":"i35","odfl":"i35",
}

def branding_for(c):
    return c.get("branding_group") or c["id"]

def lettering_style_for(c):
    hint = (c.get("lettering_hint") or "").lower()
    if "script" in hint: return "script"
    if any(x in hint for x in ("burgundy","dark-red","maroon")): return "simple"
    if "red" in hint: return "block"
    return c.get("lettering_style") or "unknown"

def pool_for(c):
    # logo-only / no trailer photos → low_priority pool (kept, not deleted)
    imgs = c.get("images") or []
    trailers = [i for i in imgs if i.get("view") != "logo"]
    if not trailers:
        return "low_priority"
    if c.get("priority") == "low" and not any(i.get("view")=="rear" for i in trailers):
        return "low_priority"
    return "lineup"

def main():
    data = json.loads(JSON_PATH.read_text())
    companies = data["companies"]
    by_id = {c["id"]: c for c in companies}
    before = len(companies)

    for c in companies:
        cid = c["id"]
        c["branding_group"] = branding_for(c)
        c["lettering_style"] = lettering_style_for(c)
        c["corridor"] = c.get("corridor") or CORRIDOR_MAP.get(cid) or (
            "texas" if c.get("region")=="texas" else
            "national" if c.get("region") in ("national","private","leasing","rental") else
            c.get("region") or "national"
        )
        c["similar_to_drawing"] = bool(c.get("similar_to_drawing") or cid in SIMILAR_DRAWING_IDS)
        # Demote M-as-dominant: keep flag for admin history but don't require it
        if "leslie_m_candidate" in c:
            c["legacy_m_shortlist"] = bool(c.get("leslie_m_candidate"))
        c["pool"] = pool_for(c)
        c["lineup_eligible"] = c["pool"] == "lineup" and any(
            i.get("view") == "rear" for i in (c.get("images") or [])
        )
        # Evidence notes structure
        c.setdefault("evidence_notes", [])
        # Ensure door keywords
        c.setdefault("door_text_keywords", [c["name"], c["id"]])

        # Image-level metadata
        for im in c.get("images") or []:
            im.setdefault("branding_group", c["branding_group"])
            im.setdefault("broken", False)
            im.setdefault("lineup_exclude", im.get("view") == "logo")
            if im.get("view") == "logo":
                im["lineup_exclude"] = True

    added = 0
    for nc in NEW_CARRIERS:
        if nc["id"] in by_id:
            # merge corridor / similar flags onto existing
            ex = by_id[nc["id"]]
            ex["corridor"] = nc.get("corridor", ex.get("corridor"))
            ex["branding_group"] = nc.get("branding_group", ex.get("branding_group"))
            ex["lettering_style"] = nc.get("lettering_style", ex.get("lettering_style"))
            if nc["id"] in SIMILAR_DRAWING_IDS:
                ex["similar_to_drawing"] = True
            continue
        nc = dict(nc)
        nc["door_text_keywords"] = [nc["name"], nc["id"], nc.get("lettering_hint","")]
        nc["image_count"] = 0
        nc["images"] = []
        nc["has_burgundy_hint"] = bool(re_burg(nc.get("lettering_hint","")))
        nc["leslie_m_candidate"] = False
        nc["legacy_m_shortlist"] = False
        nc["rear_image_count"] = 0
        nc["has_logo"] = False
        nc["similar_to_drawing"] = nc["id"] in SIMILAR_DRAWING_IDS
        nc["pool"] = "low_priority"
        nc["lineup_eligible"] = False
        nc["evidence_notes"] = [{
            "kind": "ORIGINAL",
            "text": "Carrier added in lineup expansion (metadata only; photos pending public rear sources).",
            "at": datetime.now(ZoneInfo("America/Chicago")).isoformat(timespec="seconds"),
        }]
        companies.append(nc)
        by_id[nc["id"]] = nc
        added += 1

    # Global evidence notes for the drawing
    data["evidence"] = {
        "drawing": {
            "file": "assets/leslie-drawing-original.png",
            "kind": "ORIGINAL",
            "note": "Unaltered iMessage screenshot from Leslie (momma). Do not alter pixels.",
            "eyewitness_statement_exact": "I'm not sure if these are the correct letters, but they were sideways.",
            "shapes_policy": "Do NOT label drawing shapes as definite letters. Use only as visual similarity reference.",
            "context": "iMessage Screenshot 2026-09-28 at 12.33.29 PM after Selma/I-35 hit-and-run Mon 2026-09-28 ~9:32 AM CT. White trailer; rear marking small/subtle dark red/maroon/burgundy; simple maybe script; company name possible; letter unsure (not force M).",
        },
        "after": []
    }

    rear_count = sum(1 for c in companies for i in c.get("images") or [] if i.get("view")=="rear")
    logo_count = sum(1 for c in companies for i in c.get("images") or [] if i.get("view")=="logo")
    trailer_count = sum(1 for c in companies for i in c.get("images") or [] if i.get("view")!="logo")
    lineup_photos = sum(1 for c in companies for i in c.get("images") or []
                        if i.get("view")=="rear" and not i.get("broken") and not i.get("lineup_exclude"))

    data["companies"] = companies
    data["company_count"] = len(companies)
    data["image_count"] = trailer_count
    data["rear_image_count"] = rear_count
    data["logo_count"] = logo_count
    data["lineup_photo_count"] = lineup_photos
    data["generated_at"] = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M:%S %Z")
    data["rebuild"] = "blind_lineup_v1"
    data["incident"] = {
        "date": "2026-09-28",
        "approx_time": "9:32 AM CT",
        "location": "Selma, TX — I-35",
        "description": "White semi trailer; rear-door writing believed small/subtle burgundy/dark red/maroon; simple maybe script. Lineup only — not an identification.",
        "eyewitness_statement_exact": "I'm not sure if these are the correct letters, but they were sideways.",
    }

    JSON_PATH.write_text(json.dumps(data, indent=2) + "\n")
    print(f"before={before} after={len(companies)} added={added} rear={rear_count} lineup_photos={lineup_photos}")

def re_burg(s):
    s = (s or "").lower()
    return any(x in s for x in ("burgundy","dark-red","maroon","red"))

if __name__ == "__main__":
    main()
