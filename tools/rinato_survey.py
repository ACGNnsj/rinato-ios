#!/usr/bin/env python3
# Rinato ExeFS module survey (Task 3). Module half of nxnative profile_guess facts_of.
# MIT seedds/nxnative @ 551228c. RomFS half NOT covered (no RomFS bytes yet).
import collections
import json
import re
import struct
import sys
from pathlib import Path
NXN = Path('D:/consoles/.scratch/nxnative-audit')
sys.path.insert(0, str(NXN / 'dm' / 'tools'))
import nso
import nso_syms
SDK_VERSION = re.compile(rb'(?i)NintendoSDK_nnSdk-(?:[a-z]+_)?([0-9_]+)')
COMP_RE = re.compile(rb'NintendoSDK_(?!nnSdk)[A-Za-z0-9_]+-[0-9_]+')
MW_RE = re.compile(rb'SDK MW[+]Nintendo[+]([A-Za-z0-9_]+-[0-9_]+)')
UNITY_RE = re.compile(rb'20[12][0-9][.][0-9]+[.][0-9]+f[0-9]')
def survey_exefs(exefs):
    F = {'mods': {}, 'sdkver': set(), 'comps': set(), 'unity': set(), 'sysres': 0, 'program': None}
    for p in sorted(Path(exefs).iterdir()):
        with open(p, 'rb') as f:
            magic = f.read(4)
        if magic != b'NSO0':
            continue
        m = nso.load(Path(p).read_bytes(), str(p))
        img = bytes(m.image)
        syms = nso_syms.dynsyms(img)
        end = ((((len(img) + m.bss + 16383) & ~16383) + 16384 + 65535) & ~65535)
        mod = F['mods'][p.name] = {
            'bid': m.build_id[:16].hex(),
            'sizes': [sz for _, sz in m.segments],
            'bss': m.bss,
            'far': end > 117440512,
            'nimports': sum(1 for s, defined, _ in syms if not defined),
            'comps': sorted(set(c.decode().rsplit('-', 1)[0] for c in re.findall(COMP_RE, img))),
        }
        F['sdkver'] |= set(v.decode() for v in SDK_VERSION.findall(img))
        F['comps'] |= set(c.decode() for c in re.findall(MW_RE, img))
        if p.name == 'main':
            F['unity'] = sorted(set(v.decode() for v in UNITY_RE.findall(img)))
    npdm = Path(exefs) / 'main.npdm'
    if npdm.exists():
        d = npdm.read_bytes()
        a = d.find(b'ACI0')
        F['sysres'] = struct.unpack_from('<I', d, 20)[0] if d[:4] == b'META' else 0
        F['program'] = struct.unpack_from('<Q', d, a + 16)[0] if a >= 0 else None
    F['romfs'] = 'NOT SURVEYED (no RomFS bytes extracted yet)'
    F['sdkver'] = sorted(F['sdkver'])
    F['comps'] = sorted(F['comps'])
    return F
def main():
    out = {'base': survey_exefs(sys.argv[1]), 'update': survey_exefs(sys.argv[2])}
    print(json.dumps(out, indent=1))
if __name__ == '__main__':
    main()