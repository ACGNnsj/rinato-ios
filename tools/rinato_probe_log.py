#!/usr/bin/env python3
"""Parse the on-device M0 probe log and render the evidence table.

The probe writes one "PROBE key=value" line per measurement. Anything the device
did not report stays UNKNOWN; this module never invents a value.
"""
import sys

REQUIRED_KEYS = (
    "abi",
    "ptrauth_compile",
    "fixed_value",
    "pac_indirect",
    "jit_mmap",
    "mem_available",
    "mem_alloc",
    "metal_device",
    "metal_drawable",
    "metal_presents",
)

PROBE_PREFIX = "PROBE "


def parse_log(text):
    """Map every "PROBE key=value" line to its raw value."""
    entries = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith(PROBE_PREFIX):
            continue
        body = line[len(PROBE_PREFIX):]
        if "=" not in body:
            continue
        key, value = body.split("=", 1)
        key = key.strip()
        if key:
            entries[key] = value.strip()
    return entries


def aggregate(entries):
    """Split parsed entries into measured rows and the still-unknown keys."""
    rows = []
    unknown = []
    for key in REQUIRED_KEYS:
        if key in entries:
            rows.append({"key": key, "value": entries[key], "status": "MEASURED"})
        else:
            rows.append({"key": key, "value": "", "status": "UNKNOWN"})
            unknown.append(key)
    return {"rows": rows, "unknown": unknown}


def render_markdown(result):
    """Render the evidence table. Failures keep their verbatim text."""
    lines = [
        "| Probe key | Result | Status |",
        "|---|---|---|",
    ]
    for row in result["rows"]:
        value = row["value"].replace("|", "\\|") if row["value"] else "not measured"
        lines.append("| `%s` | %s | %s |" % (row["key"], value, row["status"]))
    lines.append("")
    if result["unknown"]:
        lines.append("Not measured on device (UNKNOWN): " + ", ".join(result["unknown"]))
    else:
        lines.append("Every required key was reported by the device; UNKNOWN means not measured.")
    return "\n".join(lines)


def main(argv):
    if len(argv) != 2:
        print("usage: rinato_probe_log.py <probe.log>", file=sys.stderr)
        return 2
    with open(argv[1], "r", encoding="utf-8", errors="replace") as handle:
        result = aggregate(parse_log(handle.read()))
    print(render_markdown(result))
    return 0 if not result["unknown"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
