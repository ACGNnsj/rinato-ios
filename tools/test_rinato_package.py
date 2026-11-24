#!/usr/bin/env python3
"""Standard-library tests for the reproducible Rinato package manifest."""
import hashlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rinato_package import build_manifest, partition_entries, verify_manifest  # noqa: E402


def put(root, relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class PackageManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "game-data"
        self.app = put(self.root, "input/app.xci", b"app package")
        self.update = put(self.root, "input/update.nsp", b"update package")
        for version, names in {
            "app-1.0.0": ["main", "rtld", "sdk", "subsdk0", "main.npdm"],
            "update-1.0.1": ["main", "rtld", "sdk", "subsdk0", "main.npdm"],
        }.items():
            for index, name in enumerate(names):
                put(self.data, f"{version}/exefs/{name}", f"{version}:{name}".encode())
        put(self.data, "update-1.0.1/romfs.bin", b"synthetic romfs image")
        files = {
            "Data/Managed/Metadata/global-metadata.dat": b"metadata",
            "Data/resources.assets": b"assets",
            "Data/sharedassets0.resource": b"resource",
            "UniNAS/libunas.nrs": b"libunas",
            "UniNAS/archive.nas": b"archive",
            "Data/StreamingAssets/Shaders/main.shader": b"shader",
            "Data/StreamingAssets/Movies/opening.mp4": b"movie",
            "Data/StreamingAssets/Audio/theme.ogg": b"audio",
            "Data/readme.txt": b"other",
        }
        for name, payload in files.items():
            put(self.data, f"update-1.0.1/romfs/{name}", payload)
        self.manifest = build_manifest(self.app, self.update, self.data)
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_sample_recomputes_identically(self):
        rebuilt = build_manifest(self.app, self.update, self.data)
        assert rebuilt == self.manifest
        verified = verify_manifest(self.manifest_path, self.data, self.app, self.update)
        assert verified == self.manifest
        assert len(self.manifest["exefs"]["app-1.0.0"]) == 5
        assert len(self.manifest["exefs"]["update-1.0.1"]) == 5
        assert self.manifest["romfs"]["file_count"] == 9
        locations = self.manifest["locations"]
        assert locations["global_metadata"]["path"].endswith("global-metadata.dat")
        assert locations["libunas_nrs"]["path"] == "update-1.0.1/romfs/UniNAS/libunas.nrs"
        assert len(locations["unity_assets"]) == 2
        assert len(locations["uninas"]) == 2
        assert len(locations["shaders"]) == 1
        assert len(locations["media"]) == 2
        assert str(self.root) not in json.dumps(self.manifest)

    def test_truncated_file_fails(self):
        target = self.data / self.manifest["romfs"]["files"][0]["path"]
        target.write_bytes(target.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError, "size mismatch"):
            verify_manifest(self.manifest_path, self.data, self.app, self.update)

    def test_wrong_hash_fails(self):
        target = self.data / self.manifest["romfs"]["files"][0]["path"]
        payload = bytearray(target.read_bytes())
        payload[0] ^= 0xFF
        target.write_bytes(payload)
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_manifest(self.manifest_path, self.data, self.app, self.update)

    def test_wrong_package_hash_fails(self):
        self.app.write_bytes(b"app packagf")
        with self.assertRaisesRegex(ValueError, "app.*SHA-256 mismatch"):
            verify_manifest(self.manifest_path, self.data, self.app, self.update)

    def test_manifest_path_traversal_fails(self):
        self.manifest["romfs"]["files"][0]["path"] = "../outside.dat"
        self.manifest_path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "Unsafe manifest path"):
            verify_manifest(self.manifest_path, self.data, self.app, self.update)

    def test_libunas_nro_is_explicit_when_nrs_is_absent(self):
        source = self.data / "update-1.0.1/romfs/UniNAS/libunas.nrs"
        target = self.data / "update-1.0.1/romfs/Plugins/libunas.nro"
        target.parent.mkdir(parents=True)
        source.rename(target)
        manifest = build_manifest(self.app, self.update, self.data)
        location = manifest["locations"]["libunas_nrs"]
        assert location["status"] == "not_present"
        assert location["actual_file"]["path"].endswith("Plugins/libunas.nro")
        assert any(r["path"].endswith("Plugins/libunas.nro") for r in manifest["locations"]["uninas"])

    def test_absent_loose_shader_and_media_are_explicit(self):
        (self.data / "update-1.0.1/romfs/Data/StreamingAssets/Shaders/main.shader").unlink()
        (self.data / "update-1.0.1/romfs/Data/StreamingAssets/Movies/opening.mp4").unlink()
        (self.data / "update-1.0.1/romfs/Data/StreamingAssets/Audio/theme.ogg").unlink()
        manifest = build_manifest(self.app, self.update, self.data)
        for category in ("shaders", "media"):
            assert manifest["locations"][category]["status"] == "not_present_as_loose_files"
            assert manifest["locations"][category]["files"] == []

    def test_partition_path_traversal_fails(self):
        # PFS0 header, one 24-byte entry, and an unsafe name string.
        name = b"../payload.bin\0"
        raw = bytearray(struct.pack("<4sIII", b"PFS0", 1, len(name), 0))
        raw += struct.pack("<QQII", 0, 0, 0, 0)
        raw += name
        with self.assertRaisesRegex(ValueError, "Unsafe partition filename"):
            partition_entries(io.BytesIO(raw), 0, len(raw))

    def test_missing_file_fails(self):
        listed = self.data / self.manifest["romfs"]["files"][0]["path"]
        listed.unlink()
        with self.assertRaisesRegex(ValueError, "size mismatch|Missing extracted file"):
            verify_manifest(self.manifest_path, self.data, self.app, self.update)

    def test_unlisted_file_fails(self):
        put(self.data, "update-1.0.1/romfs/unlisted.dat", b"unlisted")
        with self.assertRaisesRegex(ValueError, "Unlisted extracted file"):
            verify_manifest(self.manifest_path, self.data, self.app, self.update)


if __name__ == "__main__":
    unittest.main(verbosity=2)
