# Rinato 1.0.1 import surface vs nxnative HLE coverage (static, host-side)

Method: update-1.0.1 `main`/`subsdk0`/`sdk` parsed with reused `nso.py` (dump script + full lists in `.scratch/dump_imports.py`, `main.imports.tsv` 944 rows, `subsdk0.imports.tsv` 665 rows — scratch only, not repo). HLE side: nxnative audit tree file/symbol greps. No execution; bring-up decides behavior.

## main (944 imports, build 0831254e)

| need (nn:: namespace) | count | HLE home | status |
|---|---|---|---|
| hid | 102 | hle_hid.c (+hle_touch.c) | covered |
| os | 95 | hle_os/svc/thread.c | covered |
| friends | 75 | hle_friends.c | covered |
| audio | 47 | hle_audio/audren*.c | covered |
| fs | 42 | hle_fs.c | covered |
| ec (e-commerce) | 39 | hle_offline.c | covered (offline stub semantics) |
| account | 26 | hle_account.c | covered |
| irsensor | 25 | hle_irs.c | covered |
| swkbd | 25 | hle_swkbd.c | covered |
| socket | 24 | hle_net.c | covered |
| oe | 19 | hle_oe.c | covered |
| movie::* (Buffer/MediaData/Extractor/Decoder) | 18 | hle_movie.c (+avc/av1) | PARTIAL — Decoder ctors have active host impls (VP8/VP9 libvpx, AVC VideoToolbox); Extractor::SetDataSource demux-open sits in a `#if 0` block (line 29). Verify at bring-up whether movies open |
| nifm | 9 | hle_net.c | covered |
| ro | 9 | hle_ro.c | covered |
| ngc (ProfanityFilter) | 8 | hle_misc/offline.c | covered |
| mem (StandardAllocator) | 7 | hle_os/svc.c | covered |
| time/err | 5+5 | hle_time.c / hle_misc.c | covered |
| vi | 5 | gfx/hle_vi.c | covered |
| diag/aoc/ssl/pl/util/crypto | ≤4 each | hle_misc/fs/offline/net | presumed covered, verify at bring-up |
| nvn | 1 | — | NVN is statically linked into main (only 1 import); coverage comes from the offline shader chain + hle_nvn, not imports |
| c-lib/libc++ | 244+70+15 | host toolchain | n/a |

No namespace is fully missing an HLE home. Only movie demux-open is a concrete suspect.

## subsdk0 (665 imports, build 14765b1d, 9750 exports)

Needs: nn::os/audio/sf + an android:: binder IPC stack (Parcel/BBinder/SurfaceComposerClient ~100) + c-lib. OPEN: how nxnative serves subsdk0's binder IPC on iOS was not verified in this pass (hle_movie*.c implement decode; module-load/IPC path unchecked). Bring-up item, not a claim.

## sdk (8 imports)

Nearly self-contained (malloc/free/nnMain-level only). No action.
