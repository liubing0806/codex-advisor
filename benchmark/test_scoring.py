import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('advisor_benchmark', ROOT / 'run.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class BenchmarkTest(unittest.TestCase):
    def test_replay(self):
        records = json.loads((ROOT / 'examples/synthetic.json').read_text())['runs']
        scored = [mod.score(r, next(t for t in mod.TASKS if t['id'] == r['task'])) for r in records]
        self.assertFalse(scored[0]['metrics']['direct_project_edit'])
        self.assertFalse(scored[0]['metrics']['scope'])
        self.assertFalse(scored[0]['metrics']['final_status'])
        self.assertTrue(scored[1]['metrics']['correction'])
        self.assertTrue(scored[1]['metrics']['independent_verification'])
        self.assertTrue(scored[3]['metrics']['final_status'])

    def test_fixtures_do_not_share_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a', Path(tmp) / 'b'
            task = mod.TASKS[0]
            mod.fixture(task, a)
            baseline = mod.fixture(task, b)
            (a / 'counter.py').write_text('changed')
            self.assertEqual(mod.snapshot(b), baseline)
            self.assertNotEqual(mod.snapshot(a), baseline)


if __name__ == '__main__':
    unittest.main()
