#!/usr/bin/env python3
"""Inspect an unsigned iOS .ipa and reject anything that is not a real app bundle.

Used by the M0 CI job and by hand on Windows. It checks the payload layout that
Xcode produces, decodes the Mach-O header to prove the binary is arm64, and
refuses archives that smuggle game data, keys or package images.
"""
import plistlib
import struct
import sys
import zipfile
from pathlib import Path

PAYLOAD_PREFIX = "Payload/"
MH_MAGIC_64 = 0xFEEDFACF
MH_MAGIC = 0xFEEDFACE
FAT_MAGIC = 0xCAFEBABE
FAT_MAGIC_64 = 0xCAFEBABF
CPU_ARCH_ABI64 = 0x01000000
CPU_TYPE_X86 = 7
CPU_TYPE_ARM = 12
CPU_TYPE_ARM64 = CPU_ARCH_ABI64 | CPU_TYPE_ARM
CPU_TYPE_X86_64 = CPU_ARCH_ABI64 | CPU_TYPE_X86

CPU_NAMES = {
    CPU_TYPE_ARM64: "arm64",
    CPU_TYPE_ARM: "arm",
    CPU_TYPE_X86_64: "x86_64",
    CPU_TYPE_X86: "i386",
}

# Any entry that would carry copyrighted game payloads or key material.
FORBIDDEN_SUFFIXES = (".nsp", ".xci", ".nso", ".nca", ".nro", ".xcz", ".kip")
FORBIDDEN_PREFIXES = ("romfs/", "game-data", "keys/")
FORBIDDEN_NAMES = ("prod.keys", "title.keys", "console.keys")


class IpaError(Exception):
    """The archive is not a valid, game-data-free arm64 iOS app."""


def _cpu_name(cputype):
    return CPU_NAMES.get(cputype & 0xFFFFFFFF, "cputype_0x%08x" % (cputype & 0xFFFFFFFF))


def _architectures(header):
    if len(header) < 8:
        raise IpaError("executable is shorter than a Mach-O header")
    magic_le = struct.unpack("<I", header[:4])[0]
    magic_be = struct.unpack(">I", header[:4])[0]

    if magic_le in (MH_MAGIC_64, MH_MAGIC):
        return [_cpu_name(struct.unpack("<i", header[4:8])[0])]
    if magic_be in (FAT_MAGIC, FAT_MAGIC_64):
        count = struct.unpack(">I", header[4:8])[0]
        if count == 0 or count > 64:
            raise IpaError("fat header declares an implausible architecture count: %d" % count)
        entry_size = 32 if magic_be == FAT_MAGIC_64 else 20
        need = 8 + count * entry_size
        if len(header) < need:
            raise IpaError("fat header is truncated: need %d bytes, have %d" % (need, len(header)))
        return [_cpu_name(struct.unpack(">i", header[8 + i * entry_size: 12 + i * entry_size])[0])
                for i in range(count)]
    raise IpaError("executable has no Mach-O magic: 0x%08x" % magic_le)


def _forbidden_entries(names, app_root):
    offenders = []
    for name in names:
        if not name.startswith(app_root) or name.endswith("/"):
            continue
        relative = name[len(app_root):]
        lowered = relative.lower()
        base = lowered.rsplit("/", 1)[-1]
        if (lowered.startswith(FORBIDDEN_PREFIXES)
                or lowered.endswith(FORBIDDEN_SUFFIXES)
                or base in FORBIDDEN_NAMES):
            offenders.append(relative)
    return sorted(offenders)


def inspect_ipa(path):
    """Return a summary of a real arm64 IPA, or raise IpaError."""
    path = Path(path)
    if not path.is_file():
        raise IpaError("no such file: %s" % path)
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as error:
        raise IpaError("not a zip archive: %s" % error) from error

    with archive:
        names = archive.namelist()
        if not any(name.startswith(PAYLOAD_PREFIX) for name in names):
            raise IpaError("archive has no Payload/ directory")

        apps = sorted({name.split("/")[1] for name in names
                       if name.startswith(PAYLOAD_PREFIX) and name.count("/") >= 2
                       and name.split("/")[1].endswith(".app")})
        if not apps:
            raise IpaError("archive has no Payload/*.app bundle")
        app_root = PAYLOAD_PREFIX + apps[0] + "/"

        try:
            info = plistlib.loads(archive.read(app_root + "Info.plist"))
        except KeyError as error:
            raise IpaError("app bundle has no Info.plist") from error
        except plistlib.InvalidFileException as error:
            raise IpaError("Info.plist is not a property list: %s" % error) from error

        executable_name = info.get("CFBundleExecutable")
        if not executable_name:
            raise IpaError("Info.plist declares no CFBundleExecutable")
        executable_entry = app_root + executable_name
        if executable_entry not in names:
            raise IpaError("Info.plist executable %r is missing from the bundle" % executable_name)

        architectures = _architectures(archive.read(executable_entry)[:4096])
        if "arm64" not in architectures:
            raise IpaError("executable is not arm64: %s" % ", ".join(architectures))

        forbidden = _forbidden_entries(names, app_root)
        if forbidden:
            raise IpaError("bundle contains forbidden game payload entries: %s"
                           % ", ".join(forbidden[:5]))

        return {
            "path": str(path),
            "bundle_id": info.get("CFBundleIdentifier"),
            "bundle_name": info.get("CFBundleName"),
            "executable": executable_name,
            "version": info.get("CFBundleShortVersionString"),
            "minimum_os": info.get("MinimumOSVersion"),
            "architectures": architectures,
            "signed": any(name.startswith(app_root + "_CodeSignature/") for name in names),
            "entry_count": len(names),
            "forbidden": forbidden,
        }


def main(argv):
    if len(argv) != 2:
        print("usage: rinato_ipa.py <path/to/app.ipa>", file=sys.stderr)
        return 2
    try:
        info = inspect_ipa(argv[1])
    except IpaError as error:
        print("IPA INVALID: %s" % error, file=sys.stderr)
        return 1
    print("IPA VALID")
    for key in ("bundle_id", "executable", "version", "minimum_os", "architectures",
                "signed", "entry_count"):
        print("%-14s %s" % (key, info[key]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
