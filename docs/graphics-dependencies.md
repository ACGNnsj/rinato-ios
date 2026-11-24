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
