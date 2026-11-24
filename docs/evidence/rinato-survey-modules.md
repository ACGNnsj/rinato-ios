# Rinato module survey (Task 3, controller 2026-11-25)

Tool: tools/rinato_survey.py (test tools/test_rinato_survey.py, 1/1 OK).
Method: module half of nxnative profile_guess facts_of, run on Task 1 ExeFS extracts.
RomFS half: NOT SURVEYED (no RomFS bytes extracted yet).

## Facts (base 1.0.0 + update 1.0.1)

- Engine: Unity 2022.3.39f1 IL2CPP. SDK: 18.3.2 (nnSdk-18_3_2, BuildTarget-64).
- Modules: main + rtld + sdk + subsdk0 (Nintendo movie module, 665 imports).
- main build IDs: base 329f58a9c6e051350c6de9ddc2bdd8e7, update 0831254e3f469d8af3eaf6e38da32e50.
- main: 944 imports, .text-dominated segments (58978008 / 16608124 / 5854000), bss 3505360.
- sdk: NVN + libz. main: libcurl + libz. subsdk0: movie.
- sysres: 16777216 (16 MB, non-zero) => virtual address memory => needs 4 GB layout keys (cf. Engage precedent).
- program ID from main.npdm: 72066871747649536.
- far: false for all modules (patch area fits after base).

## Reading

- Closest profile shape: Somnium-style (Unity IL2CPP + NVN + subsdk0 movies) but newer stack (Unity 2022.3, SDK 18).
- sysres 16 MB means the provisional profile will need mem_reserve/mem_alias/mem_stack/app_pool keys; exact heap split needs a Mac boot (heap_signals) or careful static estimate.
- Next: extract RomFS bytes (BKTR merge) for shader_split survey; then provisional profile under DM_GAMES_DIR.
