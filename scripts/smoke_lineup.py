#!/usr/bin/env python3
"""Smoke-test blind lineup data + index.html invariants."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
errors=[]

html=(ROOT/'index.html').read_text()
for needle in ['NO','MAYBE','FAMILIAR','Her Drawing','Rear Doors Only',
               'Similar to Her Drawing','Show more like this','Admin',
               'Lineup only','leslie-drawing-original.png',
               "I'm not sure if these are the correct letters, but they were sideways.",
               'localStorage','blind']:
    # allow curly apostrophe variant in HTML
    if needle.startswith("I'm"):
        if "I'm not sure if these are the correct letters" not in html and "I’m not sure if these are the correct letters" not in html:
            errors.append(f'missing quote in html')
        continue
    if needle not in html:
        errors.append(f'missing in index.html: {needle}')

# Drawing must not label shapes as definite letters in UI chrome
if re.search(r'letter\s*[MEW]\b|this is an M|definitely an M', html, re.I):
    errors.append('UI appears to label drawing shapes as definite letters')

data=json.loads((ROOT/'companies.json').read_text())
cos=data['companies']
if len(cos)<100: errors.append(f'expected expanded carriers >=100, got {len(cos)}')
rears=[]
for c in cos:
    for im in c.get('images') or []:
        p=ROOT/'images'/im['file']
        if not p.exists():
            errors.append(f'missing file {im["file"]}')
            continue
        if im.get('view')=='logo' and not im.get('lineup_exclude', True):
            # logos should be excluded from lineup
            if not im.get('lineup_exclude'):
                errors.append(f'logo not excluded: {im["file"]}')
        if im.get('view')=='rear':
            rears.append((c['id'], im['file']))
if len(rears)<4: errors.append(f'too few rears: {len(rears)}')

ev=data.get('evidence',{}).get('drawing',{})
if ev.get('kind')!='ORIGINAL': errors.append('drawing evidence not ORIGINAL')
if 'sideways' not in (ev.get('eyewitness_statement_exact') or ''):
    errors.append('missing exact eyewitness statement in evidence')
draw=ROOT/'assets'/'leslie-drawing-original.png'
if not draw.exists(): errors.append('missing original drawing asset')

# Logo-only must not be lineup_eligible without rear
for c in cos:
    if c.get('lineup_eligible') and not any(i.get('view')=='rear' for i in c.get('images') or []):
        errors.append(f'lineup_eligible without rear: {c["id"]}')

print('companies', len(cos))
print('rears', len(rears), rears)
print('similar_to_drawing', sum(1 for c in cos if c.get('similar_to_drawing')))
if errors:
    print('FAIL')
    for e in errors: print(' -', e)
    sys.exit(1)
print('OK')
