# Toolchain portability notes (Task 3, controller 2026-11-25)

- dmsh_xlate (vendored Ryujinx translator) BUILDS on Windows (dotnet 11 SDK, net10.0, 0 warnings/errors).
  Full offline chain still needs Mac/CI (spirv-cross binary + xcrun metal). XLATE env override exists for
  stepping only the translator.
- patch_nso.py runs on Windows until find_x18_words: in_parallel uses signal.pthread_sigmask (POSIX-only)
  -> rewrite step belongs on Mac/CI per the approved plan, not on the Windows box.
- Fail-closed evidence: the Unity-2018 ThreadedStreamBuffer function patch was SKIPPED on our Unity-2022.3
  main (0 matching functions in all 4 variants) — fingerprint mismatch changes nothing. Exactly the
  behavior the no-fake-evidence rule needs.
- WSL route: WSL python3 exists but has no pip and no passwordless sudo; not pursued (needs user admin).
