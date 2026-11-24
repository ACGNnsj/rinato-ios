#!/usr/bin/env python3
"""Tests for the unsigned-IPA inspector used to verify CI build artifacts."""
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rinato_ipa import IpaError, inspect_ipa  # noqa: E402

MH_MAGIC_64 = 0xFEEDFACF
MH_MAGIC = 0xFEEDFACE
FAT_MAGIC = 0xCAFEBABE
CPU_ARM64 = 0x0100000C
CPU_X86_64 = 0x01000007

INFO_PLIST = {
    "CFBundleIdentifier": "dev.rinato.probe",
    "CFBundleExecutable": "Rinato",
    "CFBundleName": "Rinato",
    "CFBundleShortVersionString": "0.1.0",
    "MinimumOSVersion": "17.0",
}


def plist_bytes(mapping):
    import plistlib

    return plistlib.dumps(mapping, fmt=plistlib.FMT_BINARY)


def thin_macho(cputype=CPU_ARM64):
    return struct.pack("<IiiII", MH_MAGIC_64, cputype, 0, 6, 0) + b"\0" * 24


def fat_macho(cputypes=(CPU_ARM64,)):
    header = struct.pack(">II", FAT_MAGIC, len(cputypes))
    body = b"".join(struct.pack(">iiIII", c, 0, 0, 0, 0) for c in cputypes)
    return header + body


class IpaBuilder:
    def __init__(self, root):
        self.path = Path(root) / "app.ipa"
        self.entries = {}

    def add(self, name, data):
        self.entries[name] = data
        return self

    def write(self, app_name="Rinato.app", info=None, executable=None):
        with zipfile.ZipFile(self.path, "w") as archive:
            archive.writestr(f"Payload/{app_name}/Info.plist", plist_bytes(info or INFO_PLIST))
            archive.writestr(
                f"Payload/{app_name}/Rinato", executable if executable is not None else thin_macho()
            )
            for name, data in self.entries.items():
                archive.writestr(f"Payload/{app_name}/{name}", data)
        return self.path


class InspectIpaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_unsigned_arm64_ipa_is_accepted(self):
        path = IpaBuilder(self.root).write()
        info = inspect_ipa(path)
        assert info["bundle_id"] == "dev.rinato.probe"
        assert info["executable"] == "Rinato"
        assert info["version"] == "0.1.0"
        assert info["minimum_os"] == "17.0"
        assert info["architectures"] == ["arm64"]
        assert info["signed"] is False
        assert info["forbidden"] == []

    def test_fat_binary_reports_every_architecture(self):
        path = IpaBuilder(self.root).write(executable=fat_macho((CPU_ARM64, CPU_X86_64)))
        info = inspect_ipa(path)
        assert info["architectures"] == ["arm64", "x86_64"]

    def test_missing_payload_directory_is_rejected(self):
        path = self.root / "bad.ipa"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("Rinato.app/Info.plist", plist_bytes(INFO_PLIST))
        with self.assertRaises(IpaError) as raised:
            inspect_ipa(path)
        assert "Payload" in str(raised.exception)

    def test_missing_app_bundle_is_rejected(self):
        path = self.root / "bad.ipa"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("Payload/readme.txt", b"nope")
        with self.assertRaises(IpaError) as raised:
            inspect_ipa(path)
        assert ".app" in str(raised.exception)

    def test_missing_executable_is_rejected(self):
        path = self.root / "bad.ipa"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("Payload/Rinato.app/Info.plist", plist_bytes(INFO_PLIST))
        with self.assertRaises(IpaError) as raised:
            inspect_ipa(path)
        assert "executable" in str(raised.exception)

    def test_non_arm64_executable_is_rejected(self):
        path = IpaBuilder(self.root).write(executable=thin_macho(CPU_X86_64))
        with self.assertRaises(IpaError) as raised:
            inspect_ipa(path)
        assert "arm64" in str(raised.exception)

    def test_signed_bundle_is_reported(self):
        path = IpaBuilder(self.root).add("_CodeSignature/CodeResources", b"<plist/>").write()
        info = inspect_ipa(path)
        assert info["signed"] is True

    def test_game_payload_entries_are_rejected(self):
        for name in ("romfs/Data/x.bin", "game-data/main.nso", "assets/main.nsp", "keys/prod.keys"):
            with self.subTest(name=name):
                path = IpaBuilder(self.root).add(name, b"payload").write()
                with self.assertRaises(IpaError) as raised:
                    inspect_ipa(path)
                assert "forbidden" in str(raised.exception)

    def test_not_a_zip_is_rejected(self):
        path = self.root / "bad.ipa"
        path.write_bytes(b"not a zip at all")
        with self.assertRaises(IpaError) as raised:
            inspect_ipa(path)
        assert "zip" in str(raised.exception).lower()


if __name__ == "__main__":
    unittest.main(verbosity=2)
