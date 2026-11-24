# Rinato nxnative survey (Task 3, controller 2026-11-25)

Toolchain: nxnative @ 551228c, nx_extract built on Windows (dotnet 11 SDK, net10.0, 0 errors),
run read-only against local XCI+NSP; outputs in D:/consoles/.scratch/rinato-survey[-101] (NOT in repo).
Cross-check: all four module build IDs match tools/rinato_survey.py output exactly.

## 1.0.1 merged profile keys (profile_guess.py)

- modules: main subsdk0 sdk (main: 944 imports / 52 exports; subsdk0 movie: 665 imports).
- main build 0831254e3f469d8af3eaf6e38da32e50; sdk f118ae1c2e7728471aaf1a0d58484968; subsdk0 14765b1d77b12d8654ea87a61c65e2b1.
- SDK 18, sysres 16 MB => 5 GB layout: mem_reserve 0x140000000, mem_alias 0x118000000,
  mem_stack 0x10000000, app_pool 0xCD500000, sys_resource 0x1000000.
- GLSLC outputs in main: 11. Embedded GLSL sources: 0. SPIR-V files: 0.
- RomFS: 128 files, 2038.4 MB (manifest only so far).

## Reading

- Unity 2022.3 IL2CPP + NVN + movie module, same shape as Somnium precedent but newer stack.
- GLSLC outputs (11) with no embedded sources: runtime-compiled shaders likely; shader capture
  needs a Mac boot (SEEN_SHADERS path) or the RomFS split may still find Unity Shader objects.
- Full RomFS extraction running in background for shader_split survey.

## Next

- shader_split.py over extracted RomFS + 1.0.1 main => shader inventory (Task 5 input).
- Provisional profile under DM_GAMES_DIR (outside repo) once shaders are inventoried.
