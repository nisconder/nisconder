from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate_identity import PALETTES, activity, statistics


class IdentityDataTests(unittest.TestCase):
    def test_stats_values_and_the_metric_scope_are_visible_in_all_variants(self):
        data = dict(snapshotDate='2026-11-08', user=dict(followers=321),
                    stats=dict(publicRepositories=15, originalStars=1234, originalForks=12))
        for palette in PALETTES.values():
            for mobile in (False, True):
                root = ET.fromstring(statistics(palette, data, mobile))
                texts = [node.text for node in root.iter('{http://www.w3.org/2000/svg}text')]
                for value in ['15', '1,234', '12', '321', 'Stars / Forks 统计自有非 Fork 公开仓库']:
                    self.assertIn(value, texts)
                self.assertTrue(any('2026-11-08' in value for value in texts))

    def test_mobile_calendar_total_matches_only_the_displayed_weeks(self):
        weeks = [dict(contributionDays=[dict(date=f'2026-01-{i+1:02}', contributionCount=1,
                                          contributionLevel='FIRST_QUARTILE')]) for i in range(27)]
        data = dict(snapshotDate='2026-11-08', weeks=weeks)
        mobile = activity(PALETTES['light'], data, True)
        desktop = activity(PALETTES['light'], data, False)
        self.assertIn('26 次贡献', mobile)
        self.assertIn('27 次贡献', desktop)
        self.assertIn('自动更新 · 2026-11-08', mobile)


if __name__ == '__main__':
    unittest.main()
