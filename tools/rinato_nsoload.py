import json, struct, sys, hashlib
sys.path.insert(0, 'D:/consoles/ns/hayarigami-recomp/tools')
from nso import Nso, R_AARCH64_RELATIVE

def load_module(path):
    n = Nso(path)
    img = bytearray(n.image)
    applied = deferred = 0
    kinds = {}
    for off, typ, sym, add in n.relocs:
        kinds[typ] = kinds.get(typ, 0) + 1
        if typ == R_AARCH64_RELATIVE:
            assert 0 <= off <= len(img) - 8, (path, off)
            struct.pack_into('<Q', img, off, add & 0xFFFFFFFFFFFFFFFF)
            applied += 1
        else:
            deferred += 1
    return n, bytes(img), applied, deferred, kinds

def main():
    import os
    d = sys.argv[1]
    names = ['main', 'subsdk0', 'sdk']
    mods = {}
    exports = {}
    nsos = {}
    for name in names:
        n, img, applied, deferred, kinds = load_module(os.path.join(d, name))
        mods[name] = {'bid': n.build_id, 'image_size': len(img),
            'image_sha256': hashlib.sha256(img).hexdigest(),
            'nrelocs': len(n.relocs), 'relocs_applied': applied,
            'relocs_deferred': deferred,
            'reloc_types': {str(k): v for k, v in kinds.items()},
            'nimports': len(n.imports()), 'nexports': len(n.exports())}
        nsos[name] = n
        for s in n.exports():
            exports.setdefault(s[0], (name, s[3]))
    all_imports = set()
    for name in names:
        n = Nso(os.path.join(d, name))
        all_imports.update(i[0] for i in n.imports())
    unresolved = sorted(all_imports - set(k for k in exports))
    link_resolved = link_unresolved = 0
    link_missing = set()
    for name in names:
        n = nsos[name]
        for off, typ, sym, add in n.relocs:
            if typ == R_AARCH64_RELATIVE or sym == 0 or sym >= len(n.syms):
                continue
            if n.syms[sym][0] in exports:
                link_resolved += 1
            else:
                link_unresolved += 1
                link_missing.add(n.syms[sym][0])
    link = {'deferred': sum(m['relocs_deferred'] for m in mods.values()),
        'resolved': link_resolved, 'unresolved_count': link_unresolved,
        'unresolved': sorted(link_missing)}
    print(json.dumps({'modules': mods, 'binding': {'unresolved': unresolved}, 'link': link}, indent=1))

if __name__ == '__main__':
    main()

