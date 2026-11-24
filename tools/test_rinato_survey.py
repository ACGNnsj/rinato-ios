import json
import subprocess
import unittest
BASE = 'D:/consoles/.scratch/rinato-ios-probe/base/exefs'
UPDATE = 'D:/consoles/.scratch/rinato-ios-probe/update/exefs'
PY = 'D:/consoles/ns/hayarigami-recomp/.venv/Scripts/python.exe'
class TestRinatoSurvey(unittest.TestCase):
    def test_module_facts(self):
        p = subprocess.run([PY, 'tools/rinato_survey.py', BASE, UPDATE], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        out = json.loads(p.stdout)
        for side in ('base', 'update'):
            mods = out[side]['mods']
            self.assertIn('main', mods)
            self.assertIn('sdk', mods)
            self.assertRegex(mods['main']['bid'], '^[0-9a-f]{32}$')
            self.assertGreater(mods['main']['nimports'], 100)
        self.assertTrue(out['base']['sdkver'])
        self.assertTrue(out['base']['unity'])
if __name__ == '__main__':
    unittest.main()