# Rinato A13 Metal 4 device probe — 2026-11-27

## Verdict

The current nxnative NVN backend cannot render on the tested iPhone 11 Pro Max. The real A13 device rejects `MTL4CommandQueue` creation. This is a hard backend capability failure, not a BC decoder failure or an OOM.

## Tested configuration

- Device: PdaTX, iPhone12,5 (iPhone 11 Pro Max), Apple A13 GPU
- OS: iOS 27.2.1 (24B156), USB
- Upstream: seedds/nxnative `2f959ede5f1e08f10fe214e2e61933a051bdd515`
- Metal 4 creation probe: commit `55b852ef971ed267e3f89e3a293083ce43fc20a2`
- CI standalone-binary run: `45923403719`, workflow commit `23733068122c1893ba9df8d7b1a994b490a78f75`
- Unsigned DmIOS: 114,117,920 bytes, SHA-256 `6382bec91c3fbe6b4b94c57f1ac757d5a7b5b225dff6377960a9402db003ae6a`
- Signed DmIOS: 114,793,760 bytes, SHA-256 `6348d55c4636313cc6ae968e2dbfe1352914ac8903ea7425cac096f1f47ad838`
- Installation completed successfully; game launched as PID 3688 with `DM_LAUNCHER=0`.

## Device evidence

House Arrest retrieved `Documents/log.txt` after launch:

- Line 45: `device GPU Apple A13 GPU has no BC texture formats: using CPU BC decompression`
- Line 94: `[nvn-mtl] [RED] Metal 4 family bit is absent on Apple A13 GPU; probing the Metal 4 objects directly`
- Line 95: `[nvn-mtl] FATAL the Metal device Apple A13 GPU has no Metal 4 (failed to create the MTL4CommandQueue: Device does not support Metal 4.), which the NVN layer needs; a virtual Mac's paravirtualized GPU has none`
- Line 109 backtrace reaches `__mtl_init_block_invoke`, `mtl_pool_add`, and `h_nvnMemoryPoolInitialize`.
- Line 121 reports a footprint of only 0.04 GB.

Reaching the queue-creation branch proves both residency-set creations returned objects. The subsequent queue creation returned nil with the quoted device error and the frontend aborted. The captured 23:21 screen was the iOS home screen, not a game frame.

Local full evidence (not committed): `D:/consoles/.scratch/rinato-a13-ci/host-log.txt` and `game-screen.png`.

## Scope and next routes

BC texture upload was never reached, so this run says nothing about CPU BC decode throughput, gameplay memory, title/story progression, or saves. The existing classic-Metal branch is explicitly capture-only and presents nothing; it is not a playable fallback.

1. Run a fresh device probe on an iPhone 12 or later with a Metal 4-capable OS.
2. Alternatively, implement a real classic-Metal NVN backend (command submission, residency, synchronization, argument binding, and presentation). That is a substantial backend project, not a small A13 compatibility patch.

No ROM, game bytes, signing private key, or provisioning secret is included here.
