# M0 device evidence — iPhone 11 Pro Max (A13) probe host

Date: 2026-11-25. Target: iPhone 11 Pro Max, iOS 27.2.1, arm64e, 4 GB. HEAD: aa31323.

## Verified (no device needed)

- GitHub workflow ios-probe run 45422927335: success at aa31323 (all steps green, incl. host tests, unsigned build, packaging, IPA verification, arch record, artifact upload).
- Host tests (Windows, .venv314 Python): test_rinato_ipa 9/9 OK; test_rinato_probe_log 8/8 OK; test_rinato_package 12/12 OK — 29/29 total.
- Downloaded artifact Rinato-unsigned.ipa revalidated with committed tools/rinato_ipa.py: IPA VALID, bundle dev.rinato.probe, executable Rinato, version 0.1.0, minimum iOS 17.0, architectures ['arm64'], signed False, entry_count 5.
- Probe app contains no game data, keys, or extracted assets; CI compiles only in-repo sources.

## Partially measured on device (2026-11-25 crash log); remainder UNKNOWN

| Item | Status | Reason |
|---|---|---|
| Fixed-value ARM64 function return | UNKNOWN | Ran before crash; lines in on-device probe.log, not yet retrieved |
| arm64e function-pointer / indirect-call (PAC boundary) | UNKNOWN | Ran before crash; lines in on-device probe.log, not yet retrieved |
| JIT (mmap PROT_EXEC / MAP_JIT) | MEASURED FAILED (2026-11-25 .ips) | Kernel SIGKILL, CODESIGNING Invalid Page, no JIT enablement attached |
| Available-memory + bounded allocation | UNKNOWN | Ran after JIT in old order (lost in crash); moved before JIT, needs rerun |
| Metal clear color + drawable/present log | UNKNOWN | viewDidLoad ran before crash but renderer start never reached; needs rerun |
| Sideload tool (user) + versions | MEASURED (partial) | Personal cert dev.rinato.probe.ZBCXKM6BPD; exact tool/version unrecorded |

CI success is NOT M0 device success. M0 stays OPEN until probe.log + JIT-enabled rerun are measured.

## Device run 2026-11-25 01:28 (user-provided Rinato-2026-11-25-012855.ips, 19,052 bytes, read verbatim)

- Device confirmed: iPhone12,5 (11 Pro Max), iOS 27.2.1 (24B156), developerMode=1, personal cert dev.rinato.probe.ZBCXKM6BPD, arm64 binary launched in foreground, lived ~1.5 s.
- JIT: MEASURED FAILED. Main-thread crash in +[NativeProbe probeJit:]: EXC_BAD_ACCESS/SIGKILL, KERN_PROTECTION_FAILURE at 0x10420c000, termination CODESIGNING Invalid Page, ktriage "Failed to fault in a page with execute permissions". No debugger/JIT streamer was attached — expected outcome, not a probe bug. The in-app fault guard cannot catch SIGKILL.
- Fixed-value/PAC: ran before the crash; results sit in on-device Documents/probe.log (ProbeLog persists every line to file). Retrieve via Apple Devices/iTunes File Sharing → Rinato → probe.log.
- Hardening in this commit: probeJit moved last in runAllWithLog so a codesigning kill cannot pre-empt memory/documents probes.
- Still needed for M0 go/no-go: (1) probe.log from this run; (2) rerun with JIT enabled (SideJITServer/StikJIT/pymobiledevice3 debugserver) for the JIT row and Metal screenshot.

## Exact Windows device procedure (reproducible)

1. On the iPhone: enable Developer Mode (Settings > Privacy & Security), connect via USB, trust the computer.
2. On Windows: install the IPA with a sideload tool (Sideloadly/AltStore/Apple Configurator path — record exact tool + version), then enable JIT (pymobiledevice3 `pymobiledevice3 developer dvt ...` or equivalent — record exact command, version, stdout/stderr verbatim).
3. Launch Rinato probe, wait for Metal clear screen, copy the on-screen log (PROBE key=value lines) and take a screenshot of the clear color.
4. Save the log as docs/evidence/M0-device-log.txt (verbatim, unedited) and run: python tools/rinato_probe_log.py docs/evidence/M0-device-log.txt
5. The script renders MEASURED vs UNKNOWN per required key; every key not present in the log stays UNKNOWN. Attach the screenshot next to the log; the screenshot alone proves (truncated line in original) nothing without matching log lines.
## Delivered probe.log (v1 IPA run, 2026-11-25) — PARTIAL

User delivered probe.log (22 lines, session 2026-11-25 00:26:30 UTC). v1 order: fixed/PAC ran, JIT killed, memory+metal never ran.

Raw (verbatim): metal_device=Apple A13 GPU; metal_family_apple7/8=no; abi=arm64; ptrauth_compile=0; hw=iPhone12,5 arm64e; os 27.2.1 (24B156); fixed_value 0x5a17c0de match yes; pac_sign unsupported (arm64 slice, not arm64e); pac_indirect/return ok match yes; jit_mmap=ok then killed (no streamer; matches crash-log CODESIGNING Invalid Page in probeJit).

tools/rinato_probe_log.py verdict: MEASURED = abi, ptrauth_compile, fixed_value, pac_indirect, jit_mmap, metal_device. UNKNOWN = mem_available, mem_alloc, metal_drawable, metal_presents.

M0 verdict: PARTIAL PASS, not go/no-go. Memory + Metal presentation + full JIT row need the v2 IPA run (JIT last; streamer for the JIT row).
## v2 run (screenshot) — M0 GO (2026-11-25)

User screenshot IMG_4863.PNG (session 11:04:18 UTC, v2 IPA): memory + Metal rows present. File-Sharing original installed as docs/evidence/M0-device-log-v2.txt (session 12:17:20 UTC; replaces screenshot transcription). It also ends pre-JIT with no jit lines: JIT section never logged = killed at entry without streamer, as expected; screenshot archived as docs/evidence/M0-screenshot-v2.jpg (teal = the Metal clear color, first frame on screen).

Scorer: 9/10 MEASURED (all except jit_mmap, which v1 already gave as ok). Combined v1+v2: every required key measured at least once. mem: physical 3931062272 (~3.66GiB), available 2192308576 (~2.04GiB), 256MB test alloc ok, documents writable. Metal: drawable 1242x2688, presents=1, clear color on screen.

M0 verdict: GO. Gate opens for Tasks 3+. Carried: (1) JIT execution needs a streamer run (mmap proven); (2) Mac heap check for the 5GB VA layout.


