"""Verify package content manifest and original native pins when available."""
import json
from pathlib import Path
from evidence import sha
ROOT=Path(__file__).resolve().parent

def verify():
    m=json.loads((ROOT/'manifest.json').read_text());errors=[]
    for name,expected in m['files'].items():
        p=ROOT/name
        if not p.is_file() or sha(p.read_bytes())!=expected: errors.append(name)
    pins=json.loads((ROOT/'native-pins.json').read_text());checked=[];unavailable=[]
    for name,expected in pins.items():
        p=ROOT.parent/name
        if p.exists():
            checked.append(name)
            if sha(p.read_bytes())!=expected: errors.append('native:'+name)
        else: unavailable.append(name)
    result={'package_integrity_passed':not errors,'mismatches':errors,'native_pins_verified':checked,'native_pins_unavailable':unavailable}
    print(json.dumps(result,indent=2));return 1 if errors else 0
if __name__=='__main__':raise SystemExit(verify())
