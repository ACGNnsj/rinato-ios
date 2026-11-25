import json
import subprocess
import unittest
UPDATE = 'D:/consoles/.scratch/rinato-ios-probe/update/exefs'
PY = 'D:/consoles/ns/hayarigami-recomp/.venv/Scripts/python.exe'
ALLOW_UNRESOLVED = {
    'nnProfilerInitialize', 'nnProfilerRecordHeartbeat',
    '_ZTH15gDeferredAction',
}
EXPECTED_BIDS = {
    'main': '0831254e3f469d8af3eaf6e38da32e50',
    'sdk': 'f118ae1c2e7728471aaf1a0d58484968',
    'subsdk0': '14765b1d77b12d8654ea87a61c65e2b1',
}

def run_tool():
    p = subprocess.run([PY, 'tools/rinato_nsoload.py', UPDATE], capture_output=True, text=True, timeout=300)
    return p


class TestRinatoNsoLoad(unittest.TestCase):
    def test_load_and_relocate(self):
        p = run_tool()
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        out = json.loads(p.stdout)
        self.assertEqual(set(out['modules']), {'main', 'subsdk0', 'sdk'})
        for name, m in out['modules'].items():
            self.assertEqual(m['bid'][:32], EXPECTED_BIDS[name])  # upstream convention: first 16 bytes
            self.assertGreater(m['image_size'], 0)
            self.assertEqual(m['relocs_applied'] + m['relocs_deferred'], m['nrelocs'])
            self.assertGreater(m['relocs_applied'], 0)
    def test_binding_closure(self):
        out = json.loads(run_tool().stdout)
        unresolved = set(out['binding']['unresolved'])
        self.assertLessEqual(unresolved, ALLOW_UNRESOLVED, sorted(unresolved)[:10])
    def test_link_map_resolves(self):
        out = json.loads(run_tool().stdout)
        link = out['link']
        self.assertEqual(link['deferred'], link['resolved'] + link['unresolved_count'])
        self.assertLessEqual(set(link['unresolved']), ALLOW_UNRESOLVED, sorted(link['unresolved'])[:10])
    def test_deterministic(self):
        self.assertEqual(run_tool().stdout, run_tool().stdout)


if __name__ == '__main__':
    unittest.main()

