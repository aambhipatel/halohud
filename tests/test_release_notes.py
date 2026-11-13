import unittest
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_notes',ROOT/'source/extract_release_notes.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ReleaseNoteTests(unittest.TestCase):
    def test_current_version_only(self):
        notes=module.extract((ROOT/'README.md').read_text(encoding='utf-8'),'v1.10.0')
        self.assertIn('vertical leaderboard',notes)
        self.assertNotIn('### 1.9.0',notes)
        self.assertNotIn('## Maintainers',notes)

    def test_missing_empty_and_duplicate_entries_fail(self):
        for text in ['## Changelog\n### 1.0.0\n', '## Changelog\n### 2.0.0\n- Other\n',
                     '## Changelog\n### 1.0.0\n- A\n### 1.0.0\n- B\n']:
            with self.assertRaises(ValueError): module.extract(text,'v1.0.0')

    def test_code_fence_and_changelog_scope(self):
        text='### 1.0.0\nOutside\n## Changelog\n### 1.0.0 — Initial\n- A\n```md\n### 2.0.0\n```\n- B\n## Help\nEnd'
        notes=module.extract(text,'1.0.0')
        self.assertIn('- B',notes)
        self.assertNotIn('Outside',notes)
        self.assertNotIn('End',notes)

    def test_exact_version_boundary(self):
        text='## Changelog\n### 1.10.0 — New\n- Ten\n### 1.1.0 — Old\n- One\n'
        self.assertEqual(module.extract(text,'v1.1.0'),'- One\n')
        with self.assertRaises(ValueError): module.extract(text,'bad tag')
