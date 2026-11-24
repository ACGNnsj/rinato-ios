# Rinato provisional profile inputs (derived metadata only)

- game.tsv: provisional DM_GAMES_DIR profile (identity + mem layout + shader groups).
- shader_map.tsv / shader_facts.tsv: shader_split.py outputs (keys, stages, sources, paths).
- CONTAINS NO GAME BYTES: split .bins (shader code) stay in scratch, never committed.
- OPEN: shader_versions value (per-SDK constant for dmsh_build; determined at chain build on CI).
- Source runs: docs/evidence/rinato-survey-nxnative.md, rinato-shader-inventory.md.
