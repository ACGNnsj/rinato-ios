#!/usr/bin/env python3
"""Reproducible Rinato APP/UPD extraction and SHA-256 manifest utilities.

Extraction verifies NCA data-block hashes, never RSA signatures. Machine-specific
package and key paths are CLI arguments and are never written to the manifest.
"""
import argparse
import bisect
import hashlib
import io
import json
import struct
from contextlib import ExitStack
from pathlib import Path, PurePosixPath, PureWindowsPath

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

BASE_TITLE = "010008702297A000"
UPDATE_TITLE = "010008702297A800"
CHUNK = 8 * 1024 * 1024
PIECE = 16 * 1024 * 1024
NODE = 0x4000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_at(f, offset, length):
    require(0 <= offset and 0 <= length <= 512 * 1024 * 1024, "Invalid/big read")
    f.seek(offset)
    data = f.read(length)
    require(len(data) == length, "Truncated input")
    return data


def partition_entries(f, offset, bound, magic=b"PFS0", stride=24):
    """Read a bounded PFS0/HFS0 table without loading its file payloads."""
    require(bound >= 16, "Truncated partition header")
    hdr = read_at(f, offset, 16)
    require(hdr[:4] == magic, f"Expected {magic.decode()}")
    count, strings_size = struct.unpack_from("<II", hdr, 4)
    require(count <= 4096 and strings_size <= 1024 * 1024, "Invalid partition table")
    size = 16 + count * stride + strings_size
    require(size <= bound, "Partition table out of bounds")
    raw = read_at(f, offset, size)
    strings = raw[16 + count * stride:]
    entries = []
    names = set()
    for i in range(count):
        off, length, nameoff = struct.unpack_from("<QQI", raw, 16 + i * stride)
        require(nameoff < len(strings), "Invalid partition filename offset")
        end = strings.find(b"\0", nameoff)
        require(end >= 0, "Unterminated partition filename")
        name = strings[nameoff:end].decode("utf-8")
        require(name not in ("", ".", "..") and "/" not in name and "\\" not in name and
                ":" not in name, "Unsafe partition filename")
        require(name not in names, "Duplicate partition filename")
        names.add(name)
        require(size + off + length <= bound, "Partition entry out of bounds")
        entries.append((name, offset + size + off, length))
    end = offset + size
    for _, start, length in sorted(entries, key=lambda e: e[1]):
        require(start >= end, "Overlapping partition entries")
        end = start + length
    return entries


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(root, path):
    return {
        "path": path.relative_to(root).as_posix(),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def scan_records(root, relative):
    directory = root / relative
    require(directory.is_dir(), f"Missing extracted directory: {relative}")
    return [file_record(root, path) for path in sorted(directory.rglob("*")) if path.is_file()]


def classify_locations(files):
    groups = {"unity_assets": [], "uninas": [], "shaders": [], "media": []}
    singles = {"global_metadata": [], "libunas_nrs": []}
    libunas_nro = []
    media_suffixes = {".mp4", ".webm", ".usm", ".bk2", ".bik", ".wav", ".ogg", ".adx",
                      ".acb", ".awb", ".aac", ".m4a", ".at9", ".wem", ".hpb", ".hph"}
    for record in files:
        path = record["path"]
        lower = path.lower()
        name = PurePosixPath(lower).name
        suffix = PurePosixPath(lower).suffix
        if name == "global-metadata.dat":
            singles["global_metadata"].append(record)
        if name == "libunas.nrs":
            singles["libunas_nrs"].append(record)
        if name == "libunas.nro":
            libunas_nro.append(record)
        if suffix in {".assets", ".resource", ".ress", ".bundle", ".unity3d"}:
            groups["unity_assets"].append(record)
        if "/uninas/" in f"/{lower}" or suffix in {".nrs", ".nas"} or name == "libunas.nro":
            groups["uninas"].append(record)
        if "shader" in lower:
            groups["shaders"].append(record)
        if suffix in media_suffixes:
            groups["media"].append(record)
    require(len(singles["global_metadata"]) == 1, "Expected one global-metadata.dat")
    require(len(singles["libunas_nrs"]) <= 1 and len(libunas_nro) <= 1, "Duplicate libunas module")
    require(singles["libunas_nrs"] or libunas_nro, "Expected libunas.nrs or libunas.nro")
    for name in ("unity_assets", "uninas"):
        require(groups[name], f"No {name} files found")
    for name in ("shaders", "media"):
        if not groups[name]:
            groups[name] = {"status": "not_present_as_loose_files", "files": [],
                            "note": "No standalone files matched; packaged Unity assets were not inspected"}
    locations = {name: records[0] for name, records in singles.items() if records}
    if not singles["libunas_nrs"]:
        locations["libunas_nrs"] = {"status": "not_present", "actual_file": libunas_nro[0],
                                      "note": "1.0.1 RomFS contains libunas.nro, not libunas.nrs"}
    return locations | groups


def build_manifest(app, update, data_root):
    """Hash original packages and the complete extracted tree; write no payload data."""
    app, update, data_root = Path(app), Path(update), Path(data_root)
    packages = []
    for role, path in (("app", app), ("update", update)):
        require(path.is_file(), f"Missing {role} package")
        packages.append({"role": role, "file_name": path.name, "size": path.stat().st_size,
                         "sha256": sha256_file(path)})
    exefs = {version: scan_records(data_root, f"{version}/exefs")
             for version in ("app-1.0.0", "update-1.0.1")}
    for version, records in exefs.items():
        require(records and any(PurePosixPath(r["path"]).name == "main" for r in records),
                f"No main executable in {version}")
    image = file_record(data_root, data_root / "update-1.0.1/romfs.bin")
    romfs_files = scan_records(data_root, "update-1.0.1/romfs")
    require(romfs_files, "Empty RomFS")
    return {
        "schema_version": 1,
        "game": {"title_id": BASE_TITLE, "update_title_id": UPDATE_TITLE, "version": "1.0.1"},
        "integrity": ("ExeFS FS headers, hash tables and data blocks verified; base/update RomFS merged "
                      "through BKTR tables; output files SHA-256 indexed; RSA signatures not checked"),
        "packages": packages,
        "exefs": exefs,
        "romfs": {"image": image, "file_count": len(romfs_files),
                  "total_payload_size": sum(r["size"] for r in romfs_files), "files": romfs_files},
        "locations": classify_locations(romfs_files),
    }


def safe_manifest_path(root, relative):
    require(isinstance(relative, str) and relative and "\\" not in relative and "\0" not in relative,
            "Unsafe manifest path")
    pure = PurePosixPath(relative)
    require(not pure.is_absolute() and not PureWindowsPath(relative).drive and
            all(part not in ("", ".", "..") for part in pure.parts), "Unsafe manifest path")
    root = root.resolve()
    path = root.joinpath(*pure.parts)
    try:
        path.resolve().relative_to(root)
    except ValueError:
        raise ValueError("Unsafe manifest path") from None
    return path


def extracted_records(manifest):
    for records in manifest["exefs"].values():
        yield from records
    yield manifest["romfs"]["image"]
    yield from manifest["romfs"]["files"]


def verify_record(root, record):
    path = safe_manifest_path(root, record["path"])
    require(path.is_file(), f"Missing extracted file: {record['path']}")
    require(path.stat().st_size == record["size"], f"Extracted size mismatch: {record['path']}")
    require(sha256_file(path) == record["sha256"], f"Extracted SHA-256 mismatch: {record['path']}")


def verify_manifest(manifest_path, data_root, app, update):
    """Independently recompute every package and extracted-file size and SHA-256."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    require(manifest.get("schema_version") == 1, "Unsupported manifest schema")
    data_root = Path(data_root)
    packages = {record["role"]: record for record in manifest["packages"]}
    require(set(packages) == {"app", "update"}, "Manifest must identify APP and UPD")
    for role, path in (("app", Path(app)), ("update", Path(update))):
        record = packages[role]
        require(path.is_file(), f"Missing {role} package")
        require(path.name == record["file_name"], f"{role} package filename mismatch")
        require(path.stat().st_size == record["size"], f"{role} package size mismatch")
        require(sha256_file(path) == record["sha256"], f"{role} package SHA-256 mismatch")
    records = list(extracted_records(manifest))
    listed = set()
    for record in records:
        safe_manifest_path(data_root, record["path"])
        require(record["path"] not in listed, f"Duplicate manifest path: {record['path']}")
        listed.add(record["path"])
    require(data_root.is_dir(), "Missing game-data directory")
    for path in data_root.rglob("*"):
        if path.is_file():
            relative = path.relative_to(data_root).as_posix()
            require(relative in listed, f"Unlisted extracted file: {relative}")
    for record in records:
        verify_record(data_root, record)
    # Rebuilding must reproduce the complete manifest, including resource locations.
    require(build_manifest(app, update, data_root) == manifest, "Manifest content mismatch")
    return manifest


# Adapted from hayarigami-recomp extract_exefs.py and extract_romfs.py (MIT).
def decrypt(key, mode, data):
    ctx = Cipher(algorithms.AES(key), mode).decryptor()
    return ctx.update(data) + ctx.finalize()


def load_keys(path):
    keys = {}
    for number, line in enumerate(path.read_text().splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            name, value = line.split("=", 1)
            try:
                keys[name.strip().lower()] = bytes.fromhex(value.strip())
            except ValueError:
                raise ValueError(f"Invalid key encoding at line {number}") from None
    return keys


def container_entries(f, size):
    if read_at(f, 0, 4) == b"PFS0":
        return "nsp", partition_entries(f, 0, size)
    require(size >= 0x138 and read_at(f, 0x100, 4) == b"HEAD", "Expected an XCI or NSP game file")
    root = struct.unpack("<Q", read_at(f, 0x130, 8))[0]
    partitions = partition_entries(f, root, size - root, b"HFS0", 64)
    secure = [entry for entry in partitions if entry[0] == "secure"]
    require(len(secure) == 1, "Expected one XCI secure partition")
    return "xci", partition_entries(f, secure[0][1], secure[0][2], b"HFS0", 64)


def common_tickets(f, entries):
    """Read common title keys into memory only; personalized tickets are rejected."""
    tickets = {}
    bodies = {0x10000: 0x240, 0x10001: 0x140, 0x10002: 0x80,
              0x10003: 0x240, 0x10004: 0x140, 0x10005: 0x80}
    for name, offset, size in entries:
        if not name.lower().endswith(".tik"):
            continue
        require(size >= 4, "Truncated NSP ticket")
        sig = struct.unpack("<I", read_at(f, offset, 4))[0]
        require(sig in bodies, "Unsupported NSP ticket signature type")
        body = bodies[sig]
        require(size >= body + 0x180, "Truncated NSP ticket body")
        data = read_at(f, offset + body, 0x180)
        require(data[0x141] == 0, "Personalized NSP tickets are unsupported")
        rights, key = data[0x160:0x170], data[0x40:0x50]
        require(rights not in tickets or tickets[rights] == key, "Conflicting NSP tickets")
        tickets[rights] = key
    return tickets


def read_nca_header(f, offset, size, keys):
    require(size >= 0xC00, "Truncated NCA header")
    require("header_key" in keys, "Missing header_key in prod.keys")
    raw = read_at(f, offset, 0xC00)
    hdr = b"".join(decrypt(keys["header_key"], modes.XTS(i.to_bytes(16, "big")),
                           raw[i * 512:(i + 1) * 512]) for i in range(6))
    require(hdr[0x200:0x204] == b"NCA3", "Expected NCA3 (check keys and game file)")
    require(struct.unpack_from("<Q", hdr, 0x208)[0] == size, "NCA size mismatch")
    for i in range(4):
        start, end = struct.unpack_from("<II", hdr, 0x240 + i * 16)
        require((start == end == 0) or 0xC00 <= start * 512 < end * 512 <= size,
                "NCA section out of bounds")
    return hdr


def nca_ctr_key(hdr, keys, tickets):
    generation = max(max(hdr[0x206], hdr[0x220]) - 1, 0)
    rights = hdr[0x230:0x240]
    if rights != bytes(16):
        require(rights in tickets, "Missing common ticket for rights-managed NCA")
        keyname = f"titlekek_{generation:02x}"
        require(keyname in keys, f"Missing {keyname} in prod.keys")
        return decrypt(keys[keyname], modes.ECB(), tickets[rights])
    require(hdr[0x207] < 3, "Unsupported NCA key area")
    area = ("application", "ocean", "system")[hdr[0x207]]
    keyname = f"key_area_key_{area}_{generation:02x}"
    require(keyname in keys, f"Missing {keyname} in prod.keys")
    return decrypt(keys[keyname], modes.ECB(), hdr[0x300:0x340])[32:48]


def nca_inventory(f, entries, keys):
    records = []
    for name, offset, length in entries:
        if not name.lower().endswith(".nca"):
            continue
        hdr = read_nca_header(f, offset, length, keys)
        record = {"name": name, "nca_offset": offset, "size": length, "content_type": hdr[0x205],
                  "title_id": f'{struct.unpack_from("<Q", hdr, 0x210)[0]:016X}'}
        records.append((record, hdr))
    return records


def update_title(title_id):
    return f"{int(title_id, 16) + 0x800:016X}"


def program_nca(records, update=False, title_id=BASE_TITLE):
    programs = [(record, hdr) for record, hdr in records if record["content_type"] == 0]
    require(len(programs) == 1, "Expected one Program NCA; combined packages are unsupported")
    record, hdr = programs[0]
    require(record["title_id"] == title_id, "Program belongs to another game or update")
    if update:
        require(any(hdr[0x400 + i * 512 + 4] == 4 for i in range(4)), "Expected a BKTR update")
        require(all(r["title_id"] in (title_id, update_title(title_id)) for r, _ in records),
                "Mixed-title update package")
    else:
        metadata = [r for r, _ in records if r["content_type"] == 1]
        require(len(metadata) <= 1 and
                all(r["title_id"] in (title_id, update_title(title_id)) for r in metadata),
                "Expected base game metadata")
    return record, hdr


def extract_exefs(source, keys, output, update):
    """Verify and extract every file in the selected base/update Program ExeFS."""
    source, output = Path(source), Path(output)
    with source.open("rb") as f:
        _, entries = container_entries(f, source.stat().st_size)
        tickets = common_tickets(f, entries)
        records = nca_inventory(f, entries, keys)
        record, hdr = program_nca(records, update=update)
        ctr_key = nca_ctr_key(hdr, keys, tickets)
        for i in range(4):
            start, end = struct.unpack_from("<II", hdr, 0x240 + 16 * i)
            if not start:
                continue
            fs = hdr[0x400 + 512 * i:0x600 + 512 * i]
            require(hashlib.sha256(fs).digest() == hdr[0x280 + 32 * i:0x2A0 + 32 * i],
                    "FS header hash mismatch")
            if fs[2:4] != b"\x01\x02":
                continue
            require(fs[4] == 3, "Only AES-CTR ExeFS is supported")
            blocksize, levels = struct.unpack_from("<II", fs, 0x28)
            hashoff, hashsize, pfsoff, pfssize = struct.unpack_from("<QQQQ", fs, 0x30)
            secstart, secsize = start * 512, (end - start) * 512
            require(levels == 2 and blocksize > 0 and pfssize <= 512 * 1024 * 1024,
                    "Unsupported ExeFS hash layout")

            def section_read(relative, size):
                require(relative >= 0 and relative + size <= secsize, "Section read out of bounds")
                absolute = secstart + relative
                aligned = absolute & ~15
                iv = fs[0x140:0x148][::-1] + (aligned // 16).to_bytes(8, "big")
                data = read_at(f, record["nca_offset"] + aligned, size + absolute - aligned)
                return decrypt(ctr_key, modes.CTR(iv), data)[absolute - aligned:]

            hashes = section_read(hashoff, hashsize)
            require(hashlib.sha256(hashes).digest() == fs[8:40], "ExeFS hash-table mismatch")
            pfs = section_read(pfsoff, pfssize)
            for index, pos in enumerate(range(0, pfssize, blocksize)):
                expected = hashes[index * 32:(index + 1) * 32]
                require(hashlib.sha256(pfs[pos:pos + blocksize]).digest() == expected,
                        f"ExeFS block hash mismatch: {index}")
            files = [(name, pfs[off:off + size]) for name, off, size in
                     partition_entries(io.BytesIO(pfs), 0, len(pfs))]
            require(any(name == "main.npdm" for name, _ in files), "PFS0 is not ExeFS")
            output.mkdir(parents=True)
            for name, data in files:
                (output / name).write_bytes(data)
            return {"section_index": i, "file_count": len(files), "program_nca_size": record["size"]}
    raise ValueError("No ExeFS section found")


# RomFS/BKTR logic adapted from hayarigami-recomp extract_romfs.py and xc2_merge_romfs.py (MIT).
class Section:
    """A base RomFS or update BKTR section inside a Program NCA."""

    def __init__(self, path, keys, update):
        self.path = Path(path)
        with self.path.open("rb") as f:
            _, entries = container_entries(f, self.path.stat().st_size)
            tickets = common_tickets(f, entries)
            record, hdr = program_nca(nca_inventory(f, entries, keys), update=update)
            self.key = nca_ctr_key(hdr, keys, tickets)
        self.nca = record["nca_offset"]
        wanted = 4 if update else 3
        found = [i for i in range(4) if struct.unpack_from("<I", hdr, 0x240 + i * 16)[0] and
                 hdr[0x400 + i * 512 + 2:0x400 + i * 512 + 5] == bytes([0, 3, wanted])]
        require(len(found) == 1, "Expected one RomFS/BKTR section")
        i = found[0]
        self.fs = hdr[0x400 + i * 512:0x600 + i * 512]
        require(hashlib.sha256(self.fs).digest() == hdr[0x280 + 32 * i:0x2A0 + 32 * i],
                "FS header hash mismatch")
        start, end = struct.unpack_from("<II", hdr, 0x240 + i * 16)
        self.start, self.size = start * 512, (end - start) * 512
        self.upper = self.fs[0x140:0x148][::-1]
        require(self.fs[8:12] == b"IVFC", "Expected an IVFC RomFS section")

    def level(self, number):
        offset, size, _, _ = struct.unpack_from("<QQII", self.fs, 0x18 + number * 24)
        return offset, size

    def read(self, f, relative, size, generation=None):
        require(0 <= relative and relative + size <= self.size, "RomFS section read out of bounds")
        absolute = self.start + relative
        aligned = absolute & ~15
        upper = self.upper if generation is None else self.upper[:4] + generation.to_bytes(4, "big")
        iv = upper + (aligned // 16).to_bytes(8, "big")
        data = read_at(f, self.nca + aligned, size + absolute - aligned)
        return decrypt(self.key, modes.CTR(iv), data)[absolute - aligned:]


def bucket_tree(section, f, offset, size, count, entry_format):
    raw = section.read(f, offset, size)
    _, sets, end = struct.unpack_from("<iiq", raw, 0)
    require(0 < sets and (1 + sets) * NODE <= size, "BKTR bucket tree out of bounds")
    entry_size = struct.calcsize(entry_format)
    entries = []
    for index in range(sets):
        node = raw[(1 + index) * NODE:(2 + index) * NODE]
        _, number, _ = struct.unpack_from("<iiq", node, 0)
        require(0 < number <= (NODE - 16) // entry_size, "BKTR entry set out of bounds")
        entries += [struct.unpack_from(entry_format, node, 16 + k * entry_size) for k in range(number)]
    require(len(entries) == count, "BKTR entry count mismatch")
    require(all(a[0] < b[0] for a, b in zip(entries, entries[1:])), "BKTR entries out of order")
    return entries, end


def bktr_plan(base, update, f):
    """Return ordered (source section, offset, size, counter generation) pieces."""
    fs = update.fs
    ind_offset, ind_size = struct.unpack_from("<QQ", fs, 0x100)
    ctr_offset, ctr_size = struct.unpack_from("<QQ", fs, 0x120)
    require(fs[0x110:0x114] == b"BKTR" and fs[0x130:0x134] == b"BKTR", "Missing BKTR tables")
    indirect, virtual_end = bucket_tree(update, f, ind_offset, ind_size,
                                        struct.unpack_from("<I", fs, 0x118)[0], "<qqi")
    ctr_ex, _ = bucket_tree(update, f, ctr_offset, ctr_size,
                            struct.unpack_from("<I", fs, 0x138)[0], "<qII")
    ctr_starts = [entry[0] for entry in ctr_ex]
    first, length = update.level(5)
    require(first + length <= virtual_end, "Update RomFS beyond indirect table")

    def generations(physical, size):
        index = bisect.bisect_right(ctr_starts, physical) - 1
        require(index >= 0, "Update data before first AES-CTR-EX entry")
        out = []
        while size:
            stop = ctr_starts[index + 1] if index + 1 < len(ctr_starts) else update.size
            amount = min(size, stop - physical)
            require(amount > 0, "Update data beyond AES-CTR-EX table")
            out.append((physical, amount, ctr_ex[index][2]))
            physical, size, index = physical + amount, size - amount, index + 1
        return out

    pieces = []
    for index, (virtual, physical, storage) in enumerate(indirect):
        stop = indirect[index + 1][0] if index + 1 < len(indirect) else virtual_end
        lo, hi = max(virtual, first), min(stop, first + length)
        if lo >= hi:
            continue
        physical += lo - virtual
        require(storage in (0, 1), "Unknown BKTR storage index")
        ranges = [(physical, hi - lo, None)] if storage == 0 else generations(physical, hi - lo)
        for offset, size, generation in ranges:
            for pos in range(0, size, PIECE):
                pieces.append((base if storage == 0 else update, offset + pos,
                               min(PIECE, size - pos), generation))
    require(sum(piece[2] for piece in pieces) == length, "BKTR tables do not cover whole RomFS")
    return pieces, length


def merge_romfs(app, update_path, keys, output):
    """Merge base and update in place, streaming the complete 1.0.1 RomFS image."""
    output = Path(output)
    require(not output.exists(), "RomFS output already exists")
    base, update = Section(app, keys, False), Section(update_path, keys, True)
    with update.path.open("rb") as f:
        pieces, total = bktr_plan(base, update, f)
    output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    done = 0
    with ExitStack() as stack:
        handles = {section.path: stack.enter_context(section.path.open("rb")) for section in (base, update)}
        with output.open("wb") as out:
            for section, offset, size, generation in pieces:
                data = section.read(handles[section.path], offset, size, generation)
                out.write(data)
                digest.update(data)
                done += len(data)
                if done == total or done // (256 * 1024 * 1024) != (done - len(data)) // (256 * 1024 * 1024):
                    print(f"RomFS: {done}/{total} bytes", flush=True)
    return {"size": total, "sha256": digest.hexdigest(), "pieces": len(pieces)}


def index_romfs(path):
    """Validate RomFS tables and return path/offset/size records without payloads."""
    with path.open("rb") as f:
        header = struct.unpack("<10Q", read_at(f, 0, 80))
        require(header[0] == 80, "RomFS header")
        length = path.stat().st_size
        for offset, size in ((header[1], header[2]), (header[3], header[4]),
                             (header[5], header[6]), (header[7], header[8])):
            require(offset + size <= length, "RomFS table bounds")
        dirs = read_at(f, header[3], header[4])
        entries = read_at(f, header[7], header[8])
        files, seen_dirs, seen_files, paths = [], set(), set(), set()

        def name(table, offset, size):
            require(offset + size <= len(table), "Name bounds")
            value = table[offset:offset + size].decode("utf-8")
            require(value not in (".", "..") and "/" not in value and "\\" not in value and "\0" not in value,
                    "Unsafe RomFS path")
            return value

        todo = [(0, "")]
        while todo:
            offset, parent = todo.pop()
            require(offset not in seen_dirs and offset + 24 <= len(dirs), "Invalid/cyclic directory")
            seen_dirs.add(offset)
            _, sibling, child, file, _, size = struct.unpack_from("<6I", dirs, offset)
            part = name(dirs, offset + 24, size)
            prefix = parent + part + "/" if part else parent
            if sibling != 0xFFFFFFFF:
                todo.append((sibling, parent))
            if child != 0xFFFFFFFF:
                todo.append((child, prefix))
            while file != 0xFFFFFFFF:
                require(file not in seen_files and file + 32 <= len(entries), "Invalid/cyclic file")
                seen_files.add(file)
                _, next_file, data, size, _, name_size = struct.unpack_from("<IIQQII", entries, file)
                part = name(entries, file + 32, name_size)
                require(part, "Empty RomFS file name")
                filename = prefix + part
                require(filename not in paths and header[9] + data + size <= length,
                        "Duplicate/out-of-bounds RomFS file")
                paths.add(filename)
                files.append({"path": filename, "offset": header[9] + data, "size": size})
                file = next_file
        return sorted(files, key=lambda item: item["path"])


def extract_romfs_files(image, output):
    """Extract every indexed RomFS file, rejecting traversal and truncated reads."""
    image, output = Path(image), Path(output)
    files = index_romfs(image)
    require(not output.exists(), "RomFS tree output already exists")
    output.mkdir(parents=True)
    with image.open("rb") as source:
        for record in files:
            target = safe_manifest_path(output, record["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            source.seek(record["offset"])
            remaining = record["size"]
            with target.open("wb") as out:
                while remaining:
                    data = source.read(min(CHUNK, remaining))
                    require(data, f"Truncated RomFS file: {record['path']}")
                    out.write(data)
                    remaining -= len(data)
    return len(files)


def extract_packages(app, update, keys_path, data_root, manifest_path):
    data_root, manifest_path = Path(data_root), Path(manifest_path)
    require(not data_root.exists(), "Data output already exists; choose a fresh directory")
    keys = load_keys(Path(keys_path))
    app_report = extract_exefs(app, keys, data_root / "app-1.0.0/exefs", False)
    update_report = extract_exefs(update, keys, data_root / "update-1.0.1/exefs", True)
    merged = merge_romfs(app, update, keys, data_root / "update-1.0.1/romfs.bin")
    file_count = extract_romfs_files(data_root / "update-1.0.1/romfs.bin",
                                     data_root / "update-1.0.1/romfs")
    manifest = build_manifest(app, update, data_root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return {"status": "pass", "app_exefs_files": app_report["file_count"],
            "update_exefs_files": update_report["file_count"], "romfs_files": file_count,
            "romfs_size": merged["size"], "romfs_sha256": merged["sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract", help="extract APP/UPD and build the manifest")
    for name in ("app", "update", "keys", "data", "manifest"):
        extract.add_argument(f"--{name}", required=True, type=Path)
    verify = sub.add_parser("verify", help="recompute a saved manifest")
    for name in ("manifest", "data", "app", "update"):
        verify.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "extract":
        print(json.dumps(extract_packages(args.app, args.update, args.keys, args.data, args.manifest)))
    if args.command == "verify":
        manifest = verify_manifest(args.manifest, args.data, args.app, args.update)
        print(json.dumps({"status": "pass", "packages": len(manifest["packages"]),
                          "exefs_files": sum(map(len, manifest["exefs"].values())),
                          "romfs_files": manifest["romfs"]["file_count"]}))


if __name__ == "__main__":
    main()
