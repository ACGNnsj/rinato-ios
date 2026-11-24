# nxnative source reuse audit (seedds/nxnative @ 551228c, MIT)

Read-only audit of the vendored-tree copy at `.scratch/nxnative-audit`. No game bytes involved.

## Verdict: reuse the route, vendor nothing yet, carry our game profile out-of-tree

- LICENSE is MIT (Copyright 2026 seedds): reuse with attribution is fine.
- `dm/games/game.py`: the profile model is clean; `DM_GAMES_DIR` out-of-tree profiles are the designed extension point, and our provisional-profile use conforms (fail-closed `KeyError` on missing keys; build-gated modules via `build_modules()` / `modules_in()`).
- `dm/games/profile_guess.py` (684 lines): marker heuristics with explicit anti-false-positive comments (UE4 build-path trap, RE Engine via.render, IL2CPP via global-metadata.dat); `--check` re-verifies every rule against hand-made profiles. Mature. Our `tools/rinato_survey.py` already mirrors its `facts_of` half.
- `dm/tools/patch_nso.py` (2025 lines): generic ARM64 rewrites (x18/TSD slots, SVC host gates, SP 16B align, exclusive acquire/release ordering, spin gates), build-ID-gated CUTS with byte assertions, function-matched MATCH_CUTS for unknown builds. POSIX-only worker pool (`signal.pthread_sigmask`, fork + SIGTERM orchestration, lines 981-1001) + Capstone 5 pin (`capstone>=5,<6`, line 22) confirm the rewrite step is a Mac/CI step, not a Windows port.
- `dm/gfx/nvn/hle_nvn.c` (4848 lines): zero UNIMPL/TODO/FIXME markers. Gaps surface as runtime `[RED]` lines instead, so completeness is verified per-game at bring-up, not by reading markers.
- Conventions (`AGENTS.md`): root-cause fixes over workarounds, per-build gating by NSO build ID, per-game values in profiles not code. Compatible with our plan; adopt the same rules for our game note.

## Consequences for Rinato

- Keep our profile + shader tables out-of-tree (done: `docs/evidence/rinato-profile/`); do not fork their tree until bring-up needs a host/behavior change.
- Rewrite + `dmsh_build` chain run on Mac/CI only. `shader_versions` stays open until then.
- At bring-up, drive by their symptom index (`docs/agents/symptoms.md`) and `[RED]` log discipline.
