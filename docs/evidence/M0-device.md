# M0 device evidence — iPhone 11 Pro Max (A13) probe host

Date: 2026-11-25. Target: iPhone 11 Pro Max, iOS 27.2.1, arm64e, 4 GB. HEAD: aa31323.

## Verified (no device needed)

- GitHub workflow ios-probe run 45422927335: success at aa31323 (all steps green, incl. host tests, unsigned build, packaging, IPA verification, arch record, artifact upload).
- Host tests (Windows, .venv314 Python): test_rinato_ipa 9/9 OK; test_rinato_probe_log 8/8 OK; test_rinato_package 12/12 OK — 29/29 total.
- Downloaded artifact Rinato-unsigned.ipa revalidated with committed tools/rinato_ipa.py: IPA VALID, bundle dev.rinato.probe, executable Rinato, version 0.1.0, minimum iOS 17.0, architectures ['arm64'], signed False, entry_count 5.
- Probe app contains no game data, keys, or extracted assets; CI compiles only in-repo sources.

## UNKNOWN — requires physical device (never measured in this session)

| Item | Status | Reason |
|---|---|---|
| Fixed-value ARM64 function return | UNKNOWN | No device run observed |
| arm64e function-pointer / indirect-call (PAC boundary) | UNKNOWN | No device run observed |
| JIT (mmap PROT_EXEC / MAP_JIT) result + errno | UNKNOWN | Needs sideload + JIT enablement on the iPhone |
| Available-memory + bounded allocation | UNKNOWN | No device run observed |
| Metal clear color + drawable/present log | UNKNOWN | No device screenshot/log observed |
| Sideload/JIT tool versions + error text | UNKNOWN | Windows has iTunes only; pymobiledevice3 absent |

CI success is NOT M0 device success. M0 stays OPEN until a real device log is measured.

## Exact Windows device procedure (reproducible)

1. On the iPhone: enable Developer Mode (Settings > Privacy & Security), connect via USB, trust the computer.
2. On Windows: install the IPA with a sideload tool (Sideloadly/AltStore/Apple Configurator path — record exact tool + version), then enable JIT (pymobiledevice3 `pymobiledevice3 developer dvt ...` or equivalent — record exact command, version, stdout/stderr verbatim).
3. Launch Rinato probe, wait for Metal clear screen, copy the on-screen log (PROBE key=value lines) and take a screenshot of the clear color.
4. Save the log as docs/evidence/M0-device-log.txt (verbatim, unedited) and run: python tools/rinato_probe_log.py docs/evidence/M0-device-log.txt
5. The script renders MEASURED vs UNKNOWN per required key; every key not present in the log stays UNKNOWN. Attach the screenshot next to the log; the screenshot alone proves nothing without matching log lines.
