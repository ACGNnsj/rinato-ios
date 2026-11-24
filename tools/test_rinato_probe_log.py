#!/usr/bin/env python3
"""Tests for probe-log parsing and the M0 evidence aggregator."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rinato_probe_log import REQUIRED_KEYS, aggregate, parse_log, render_markdown  # noqa: E402

SAMPLE = """\
Rinato M0 probe
PROBE abi=arm64
PROBE arch=arm64
PROBE ptrauth_compile=0
PROBE fixed_value=0x5a17c0de
PROBE pac_indirect=ok value=0x5a17c0de
PROBE jit_mmap=FAILED errno=1 strerror="Operation not permitted"
PROBE mem_available=2147483648
PROBE mem_alloc=ok budget=33554432
PROBE metal_device="Apple A13 GPU"
PROBE metal_drawable=828x1792
PROBE metal_presents=1
"""


class ParseLogTests(unittest.TestCase):
    def test_parses_probe_lines_only(self):
        entries = parse_log(SAMPLE)
        assert entries["fixed_value"] == "0x5a17c0de"
        assert "Rinato M0 probe" not in entries

    def test_value_may_contain_equals_and_spaces(self):
        entries = parse_log('PROBE note=a=b c\n')
        assert entries["note"] == "a=b c"

    def test_empty_log_parses_to_empty_mapping(self):
        assert parse_log("") == {}


class AggregateTests(unittest.TestCase):
    def test_measured_and_unknown_are_separated(self):
        result = aggregate(parse_log(SAMPLE))
        by_key = {row["key"]: row for row in result["rows"]}
        assert by_key["fixed_value"]["status"] == "MEASURED"
        assert by_key["pac_indirect"]["status"] == "MEASURED"
        assert result["unknown"] == []

    def test_missing_key_becomes_unknown(self):
        result = aggregate(parse_log("PROBE fixed_value=0x1\n"))
        by_key = {row["key"]: row for row in result["rows"]}
        assert by_key["fixed_value"]["status"] == "MEASURED"
        assert by_key["jit_mmap"]["status"] == "UNKNOWN"
        assert set(result["unknown"]) == set(REQUIRED_KEYS) - {"fixed_value"}

    def test_aggregate_reports_failures_without_masking_them(self):
        result = aggregate(parse_log(SAMPLE))
        by_key = {row["key"]: row for row in result["rows"]}
        assert by_key["jit_mmap"]["value"].startswith("FAILED")

    def test_render_markdown_lists_every_required_key(self):
        markdown = render_markdown(aggregate(parse_log(SAMPLE)))
        for key in REQUIRED_KEYS:
            assert key in markdown, key
        assert "UNKNOWN" in markdown

    def test_render_markdown_marks_unmeasured_rows(self):
        markdown = render_markdown(aggregate(parse_log("")))
        assert markdown.count("UNKNOWN") >= len(REQUIRED_KEYS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
