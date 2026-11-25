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
    for name in names:
        n, img, applied, deferred, kinds = load_module(os.path.join(d, name))
        mods[name] = {'bid': n.build_id, 'image_size': len(img),
            'image_sha256': hashlib.sha256(img).hexdigest(),
            'nrelocs': len(n.relocs), 'relocs_applied': applied,
            'relocs_deferred': deferred,
            'reloc_types': {str(k): v for k, v in kinds.items()},
            'nimports': len(n.imports()), 'nexports': len(n.exports())}
        for s in n.exports():
            exports.setdefault(s[0], name)
    all_imports = set()
    for name in names:
        n = Nso(os.path.join(d, name))
        all_imports.update(i[0] for i in n.imports())
    unresolved = sorted(all_imports - set(exports))
    print(json.dumps({'modules': mods, 'binding': {'unresolved': unresolved}}, indent=1))

if __name__ == '__main__':
    main()

