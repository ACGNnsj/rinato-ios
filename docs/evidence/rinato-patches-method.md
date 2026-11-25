# Rinato patches method: why there is no patches.py yet

## Format (upstream, verified in tree)

- Per-game dm/games/<id>/patches.py: CUTS keyed by 32-hex NSO build ID with (offset, orig_hex, new_hex, reason) byte assertions; MATCH_CUTS function-matched rules that survive updates; BINDING generality doc. Example: Ghost Trick frame-limiter spin cut, cross-checked against FPSLocker config.
- SDK-wide: dm/tools/sdk_patches.py. Engine-wide: dm/tools/engine_patches.py (e.g. Unity ThreadedStreamBuffer handshake; applied to builds with no CUTS).
- Loader (patch_nso.load_patches) globs DM_GAMES_DIR/*/patches.py: a missing file is skipped (AAIC/Monster Train 2 ship none). No skeleton needed.
- Upstream inconsistency: patch_nso splits DM_GAMES_DIR on os.pathsep (correct) while game.py uses split colon (breaks Windows drive paths; see reuse audit).

## Precedent finding

Every Unity 2022.3 IL2CPP+NVN+subsdk0 profile in tree (AAIC 2022.3.17f1, Monster Train 2 2022.3.54f1, both iPhone-playable) ships NO patches.py: generic rewriter passes cover Unity 2022 patterns. Our three build IDs (main 0831254e, sdk f118ae1c, subsdk0 14765b1d) are registered nowhere in sdk/engine patches.

## Derivation method (for bring-up, Task 5)

Cuts come only from observed behavior, never invented: bring-up RED/frame-pacing marker -> locate loop in rewritten main -> byte-asserted CUTS keyed by that build ID (check community FPSLocker config as cross-evidence) -> MATCH_CUTS only when the pattern must survive updates.

## Decision

No patches.py for Rinato until bring-up names a cut. Skeleton deliberately omitted (loader tolerates absence; empty file adds nothing that fail-closed does not already guarantee).
