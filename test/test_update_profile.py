import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from update_profile import cache_asset_urls, replace_region, select_projects


def repo(name, pushed='2026-11-01T00:00:00Z', **flags):
    return dict(name=name, pushedAt=pushed, isFork=False, isArchived=False, isProfile=False, **flags)


class UpdateProfileTests(unittest.TestCase):
    def test_pins_are_preserved_and_new_projects_fill_the_remaining_slots(self):
        profile = dict(pinnedRepositories=['old-pin', 'fork', 'old-pin', 'archived', 'missing'], repositories=[
            repo('old-pin', '2020-01-01T00:00:00Z'), repo('new-project', '2026-11-08T00:00:00Z'),
            repo('older'), dict(repo('fork'), isFork=True), dict(repo('archived'), isArchived=True),
            dict(repo('profile'), isProfile=True), repo('third', '2026-11-02T00:00:00Z')])
        selected = select_projects(profile, 3)
        self.assertEqual([p['name'] for p in selected], ['old-pin', 'new-project', 'third'])
        selected[0]['name'] = 'changed copy'
        self.assertEqual(profile['repositories'][0]['name'], 'old-pin')

    def test_missing_or_removed_projects_do_not_produce_dead_links(self):
        profile = dict(pinnedRepositories=['gone'], repositories=[repo('b'), repo('a')])
        self.assertEqual([p['name'] for p in select_projects(profile)], ['a', 'b'])
        self.assertEqual(select_projects(dict(pinnedRepositories=[], repositories=[])), [])

    def test_generated_sections_preserve_manual_content(self):
        source = 'manual badges\n<!-- BEGIN:stats -->\nold\n<!-- END:stats -->\nmanual notes'
        updated = replace_region(source, 'stats', '<svg>new</svg>')
        self.assertEqual(updated, 'manual badges\n<!-- BEGIN:stats -->\n<svg>new</svg>\n<!-- END:stats -->\nmanual notes')
        self.assertEqual(replace_region(updated, 'stats', '<svg>new</svg>'), updated)
        for invalid in [source + '<!-- BEGIN:stats -->', source.replace('END:stats', 'END:other'),
                        '<!-- END:stats --><!-- BEGIN:stats -->']:
            with self.assertRaises(ValueError):
                replace_region(invalid, 'stats', 'new')

    def test_image_versions_follow_content_and_leave_external_badges_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            path = root / 'assets/stats-dark.svg'
            path.write_bytes(b'one')
            source = '<img src="assets/stats-dark.svg?v=old"><img src="https://example.test/assets/remote.svg">'
            first = cache_asset_urls(source, root)
            digest = hashlib.sha256(b'one').hexdigest()[:10]
            self.assertIn('assets/stats-dark.svg?v=' + digest, first)
            self.assertIn('https://example.test/assets/remote.svg', first)
            self.assertEqual(cache_asset_urls(first, root), first)
            path.write_bytes(b'two')
            self.assertNotEqual(cache_asset_urls(first, root), first)


if __name__ == '__main__':
    unittest.main()
