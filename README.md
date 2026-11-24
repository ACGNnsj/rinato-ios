# Rinato native iOS — reproducible game-data inventory

This repository contains tooling and metadata only. Do not commit game payloads,
keys, combined packages, or extracted copyrighted content. `game-data/` and
`secrets/` are ignored.

## Requirements

- Python 3.10+ with `cryptography`
- User-owned base APP XCI (1.0.0), update UPD NSP (1.0.1), and `prod.keys`
- APP and UPD are processed separately; combined XCIs are not supported

## Extract and create the manifest

Run from the repository root, substituting local paths:

```sh
python tools/rinato_package.py extract \
  --app /path/to/APP-1.0.0.xci \
  --update /path/to/UPD-1.0.1.nsp \
  --keys /path/to/prod.keys \
  --data game-data \
  --manifest docs/evidence/rinato-1.0.1-manifest.json
```

The output directory must be new. The tool verifies ExeFS FS headers, hash
tables and every data block, extracts every APP/UPD ExeFS file, merges the base
RomFS with the update's BKTR tables, extracts the complete 1.0.1 RomFS tree,
and records SHA-256 and sizes. It does **not** verify RSA signatures.

The committed JSON identifies original packages, all ExeFS files, the merged
RomFS image and every RomFS file. Its `locations` section indexes
`global-metadata.dat`, Unity assets, UniNAS/libunas, shaders and media. The
1.0.1 RomFS contains `Plugins/libunas.nro`, not `libunas.nrs`; this difference
and any absent loose-file categories are recorded explicitly rather than
inferred. Packaged Unity asset contents are not indexed. The manifest contains
no absolute local paths, key material, or copyrighted payloads.

## Independent verification

Use a fresh extraction for reproducibility, then compare its generated manifest
with the committed one. To recompute every package and output hash in an
existing extraction:

```sh
python tools/rinato_package.py verify \
  --app /path/to/APP-1.0.0.xci \
  --update /path/to/UPD-1.0.1.nsp \
  --data game-data \
  --manifest docs/evidence/rinato-1.0.1-manifest.json
```

Verification rejects missing, truncated, modified, unlisted, or path-traversing
entries. Run the standard-library tests with:

```sh
python tools/test_rinato_package.py
```

See [NOTICE.md](NOTICE.md) for reused-code provenance and licensing.
