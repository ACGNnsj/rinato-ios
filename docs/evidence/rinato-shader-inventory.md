# Rinato shader inventory (Task 3/5, controller 2026-11-25)

Tool: nxnative shader_split.py on merged 1.0.1 (RomFS 128 files + main), provisional profile
(DM_GAMES_DIR scratch, keys: modules/mem/sys_resource + /Data/=data + note). Read-only.

## Counts

- 786 shaders: vertex 372, pixel 376, geometry 1, compute 37.
- Sources: 775 from Unity containers (incl. unity default resources compute), 11 GLSLC outputs in main
  (matches profile_guess GLSLC count exactly).
- 3 vertex shaders paired with a cover of 2 pixel shaders (single-stage programs noted by the tool).

## Reading

- Full Unity Shader object coverage from RomFS; no missing-container evidence in this pass.
- Geometry: 1 — passthrough-style risk is minimal but must be confirmed at translate time.
- Next: offline translate (vendored Ryujinx translator + spirv-cross + metal) via dmsh_build;
  shader_versions value still open (profiles use per-SDK constants; ours TBD at build).
