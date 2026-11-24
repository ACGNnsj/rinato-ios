# Graphics dependency audit (Task 3, draft — controller round 5)

> Source: web research below; NOT a substitute for code audit. Each candidate must be verified against actual source + license text before reuse. No binaries; no unaudited code.

## Candidates

| Candidate | Graphics path | License (to verify) | iOS/A13 fit | Verdict |
|---|---|---|---|---|
| Ryujinx.Graphics.Shader | Maxwell shader decode + translate (GLSL/SPIR-V) | MIT (verify) | C# — needs port; no MSL backend | Possible shader-frontend reference only |
| yuzu video_core + MoltenVK | NVN-like command emulation over Vulkan→Metal | GPL-3.0 — incompatible with App Store/personal sideload distribution as linked lib | License risk; audit only |
| MeloNX (iOS Switch emulator) | Unknown backend as of audit date | Unknown — verify repo + license | iOS-native precedent | Must read source before any claim |
| nxnative | Claims NVN→Metal translation for native execution | Unknown — site unreachable in prior probes | Concept reference only | Cannot claim support |
| Self-written minimal backend | Decode NVN ourselves, hand-write MSL for title shaders | Ours (no dependency) | Full control, smallest scope | Fallback if no reusable part clears audit |

## Research notes
- nxnative Explained: Running Switch Code Natively on Apple Silicon — https://www.youtube.com/watch?v=pYB9WRiXgZA
- nxnative/dm/third_party/ryujinx/README.md at main · seedds/nxnative · GitHub — https://github.com/seedds/nxnative/blob/main/dm/third_party/ryujinx/README.md
- MoltenVK Added to Two Emulators | Vulkan | Cross platform 3D Graphics — https://vulkan.org/news/auto-21326-48a2348075f77e07d7d06593806657fa
- Graphics backend for opengl and metal - Page 2 - C++ - Cocos Forums — https://forum.cocosengine.org/t/graphics-backend-for-opengl-and-metal/43208?page=2
- MeloNX — https://melonx.org
## Round 6 source checks (controller, 2026-11-25)

- Ryujinx upstream (github.com/Ryujinx/Ryujinx): GitHub API returns 404 for /license and /commits/master (verified this round via web_fetch). No upstream-auditable shader source; forks carry provenance risk, per-fork audit required before any reuse claim.
- yuzu upstream (github.com/yuzu-emu/yuzu): GitHub API likewise returns 404 Not Found (verified this round). No upstream video_core to audit.
- Consequence for Task 3: default to self-written minimal backend unless MeloNX/nxnative sources check out with clear licenses. No emulator code vendored on this basis.

## Round 7 source checks (controller, 2026-11-25, GitHub code search API)

- MeloNX candidates:
  - nurtrino/MeloNX | MIT | MeloNX fork - Switch emulator for iOS (CI build of unsigned IPA)
  - nguyenjessica-lgtm/MeloNX | MIT | Nintendo Switch on iOS. An open-source Nintendo Switch emulator for iPhone and iPad. No jailbreak required.
  - cheatroyale/MeloNX-HDD | no-license-field | A Nintendo Switch Emulator based on Ryujinx for iOS
  - lucasmrd/MeloNX-ClipDistance-Fix | MIT | MeloNX (iOS Switch emulator) with a fix for the vertex-as-compute ClipDistance shader crash; builds an unsigned IPA on GitHub Actions
  - Quancore21/Meliora | NOASSERTION | Nintendo Switch emulator for iPhone and iPad. Closed-loop Adaptive Engine (GPU-bound render scaling), memory governor, Darwin thread scheduling and adaptive frame pa
- nxnative candidates:
  - seedds/nxnative | MIT | Switch games running natively on iPhone, iPad and Mac: an NSP folder becomes an unsigned IPA (NSO rewriter, Horizon HLE host, NVN→Metal)
  - jamescastells/nxnative-gui | MIT | A macOS app for nxnative.
  - Xc1Ym/LumaNX | MIT | 璃游 LumaNX：nxnative 第三方 GUI，图形化构建 Switch 游戏，支持 macOS 运行与 iOS / iPadOS IPA 导出。A macOS GUI for nxnative: build Switch games for Mac, iPhone and iPad.
  - varyform/nx-native-wrapper | MIT | NX Play: a Mac app to build, play, install and manage Switch games with nxnative, on the Mac and on iPhone/iPad
  - LNPANDY/NX2Apple | MIT | one-click macOS app wrapping nxnative.

## Round 7 key finding: seedds/nxnative is MIT and exactly our route

- License endpoint: {"spdx":"MIT","sha":"ed93689ad6ab59c679f8f92bc05ccf50f4352adc"}; HEAD endpoint: {"spdx":null,"sha":"551228c9bbee96cf5677233e4f09e22836fd13f3"} (both verified via GitHub API this round).
- Repo self-description: NSO rewriter + Horizon HLE host + NVN-to-Metal. If source audit confirms, Task 3 backend decision should be REUSE nxnative's translator/HLE where it covers our needs, and Tasks 4-7 scope shrinks to game-specific gaps (this title's shaders, input/save) instead of a from-scratch host.
- Required before reuse: clone pinned hash, audit NSO rewriter + HLE + NVN→Metal code, recordxff commit hash in NOTICE.md, confirm no bundled ROM/keys. Game data stays local-only, never committed.

## Round 8 assessment (controller, 2026-11-25)

- Source: tarball of seedds/nxnative @ 551228c fetched via gh API (local git egress blocked; full-tree audit pending re-download — first attempt truncated, background re-download running).
- Games table (dm/games/README.md, 289 rows): many Unity IL2CPP + NVN titles, but NO profile for 010008702297A000 (Rinato). Expectation: new provisional game profile via the documented DM_GAMES_DIR path, not a ready-made build.
- Reuse plan stands: audit NSO rewriter + HLE + NVN→Metal on the pinned tree, then build Rinato as a new profile. Our probe host work (Tasks 1-2) remains valid input either way.

## Round 9 process model (from docs/agents/game-patches.md, partial tree)

- New game = new profile under dm/games/<title-id>/ with patches.py keyed by NSO build ID, shader tables from shader_split.py, host rows and profile keys. docs/reference/rewriter.md not yet extracted (truncated tarball) — read on re-download.
- Patch bindings (loosest-correct wins): host > sdk > engine > game > build. Our Unity IL2CPP title will most likely need engine-binding (Unity version) + game-binding patches; build-binding only as last resort (redone every update).
- Locators fail closed (fingerprint must match exactly once or nothing changes) — compatible with our no-fake-evidence rule.

## Round 11 pipeline notes (from docs/agents/03-bringup.md + 04-graphics.md, partial tree)

- Bring-up loop: patch_nso.py (main+sdk) → dmhost → boot.sh with DM_ROMFS/DM_SAVE/DM_TEMP/DM_MSL_DIR; log markers [RED]/UNIMPL/[nvn] frame counts/memory headroom (iOS os_proc_available_memory — answers our A13 memory question empirically).
- Graphics: hle_nvn.c records NVN → replays as Metal 4 at submit (nvn_mtl.m). Shaders translated OFFLINE (Ryujinx translator → SPIR-V → spirv-cross → metallib), keyed sha256(control+code)[:16]. Unity programs supported by shader_split.py (incl. missing-type-tree second pass).
- Open audit item: where does the pinned tree source its Ryujinx translator now that upstream is gone — vendored copy or submodule? Must confirm before reuse. Our Task 4-7 plan maps onto: patch NSOs → shader_split our RomFS/main → build metallib → boot to title.

## Round 12 vendoring resolved (full tree @ 551228c, 4597 entries, gzip OK)

- Ryujinx translator is a VENDORED subset (dm/third_party/ryujinx: Ryujinx.Graphics.Shader + Common + Spv.Generator from Ryujinx 1.3.2, MIT LICENSE.txt, local nxnative: fixes documented in its README). No live upstream dependency — takedown risk closed.
- spirv-cross is a prebuilt binary BUT ships with build.sh + patch + license files (dm/gfx/tools/spirv_cross_bin/) — rebuildable, auditable; acceptable with a rebuild-from-source check before we rely on it.
- Host is C/ObjC HLE (dm/host/hle_*.c) with dm/ios packaging dir; rewriter/tools under dm/tools. Our probe host (Tasks 1-2) stays useful as the device-side harness; the heavy lifting (NSO rewrite/HLE/NVN→Metal) is reuse, not rewrite.

## Round 13 reference profile + our media shape (controller, 2026-11-25)

- Closest shipped precedent: AI: THE SOMNIUM FILES (Unity 2017.4 IL2CPP + FMOD, NVN) — plays on iPhone at 60fps, no patches.py needed, only game.tsv memory/layout settings. Same genre family as Rinato (adventure). Precedent says: Unity IL2CPP adventure titles can reach playable with config-only bring-up.
- nxnative root LICENSE confirmed MIT (Copyright 2026 seedds). dm/ios = full Swift/ObjC launcher (game menu, gamepad, CloudSaves/SaveSync) — Task 8 save-sync has a reuse candidate too.
- Rinato RomFS (from Task 1 manifest): Unity .assets + StreamingAssets custom packs (adv/bgm/data .hpb/.hph, dialogue .hdlg incl. zhcn, script .heslnk); movie-container matches in manifest: 196; pack/script matches: 21. No FMOD/CRIWARE markers seen — audio path TBD during shader/split survey, not assumed.

## Round 14 build + CI picture (controller, 2026-11-25)

- One-script pack: scripts/build_ipa_from_nsp.py (identify → nx_extract → patch_nso → shader capture/split → dmsh_build metallib → build_ipa.sh). No-profile games get surveyed + provisional profile via DM_GAMES_DIR (outside repo — our Rinato work need not fork upstream).
- Mac is the dev host (PLATFORM=mac); iOS shaders/IPA via Xcode. nxnative CI (tests.yml, xcode-27 image) runs host unit + CPU-only gfx tests; Metal-4 tests stay local (runners lack Metal 4 GPU).
- Open: whether the offline metallib build (translator + spirv-cross + xcrun metal) runs headless on CI runners — decides if our Task 7 IPA can be pure-CI or needs a real Mac for shader compilation. Our approved plan already assumed macOS CI; this is now concrete and testable.
