"""Regression tests for data-driven project metadata and safe SVG layout."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_cards as cards


def project(**changes):
    value = {
        "name": "new-project", "description": "A project added after the profile was created.",
        "url": "https://github.com/nisconder/new-project", "stars": 1234, "forks": 56,
        "language": "Python", "pushedAt": "2026-11-07T20:30:00Z",
    }
    value.update(changes)
    return value


def text_nodes(source):
    return [node.text or "" for node in ET.fromstring(source).iter() if node.tag.endswith("}text")]


class ProjectCardTests(unittest.TestCase):
    def test_live_metadata_and_shanghai_code_date_appear_in_all_variants(self):
        for mobile in (False, True):
            for theme in cards.PALETTES:
                with self.subTest(mobile=mobile, theme=theme):
                    svg = cards.render(project(), theme, mobile)
                    cards.validate(svg)
                    words = " ".join(text_nodes(svg))
                    self.assertIn("new-project", words)
                    self.assertIn("Python", words)
                    self.assertIn("1,234", words)
                    self.assertIn("56", words)
                    self.assertIn('aria-label="Star 1,234"', svg)
                    self.assertIn('aria-label="Fork 56"', svg)
                    self.assertIn("更新 2026-11-08", words)
                    self.assertIn('viewBox="0 0 400 ' if mobile else 'viewBox="0 0 1100 ', svg)

    def test_new_repositories_get_generic_art_and_original_art_is_preserved(self):
        for name, kind in {**cards.PROJECT_ART, "brand-new-tool": "repo"}.items():
            for mobile in (False, True):
                with self.subTest(name=name, mobile=mobile):
                    svg = cards.render(project(name=name), "light", mobile)
                    cards.validate(svg)
                    self.assertIn("prefers-reduced-motion:reduce", svg)
                    self.assertIn('data-art="' + kind + '"', svg)
        self.assertEqual(cards.asset_key(project(name="8086-step-lab")), "8086-lab")
        self.assertEqual(cards.asset_key(project(name="brand-new-tool")), "brand-new-tool")
        for name in ("../escape", ".", "..", "a/b"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    cards.asset_key(project(name=name))

    def test_untrusted_metadata_is_text_and_cannot_add_svg_elements(self):
        unsafe = 'repo <script>alert("x")</script> & href="x"'
        value = project(name='safe<&"name', description=unsafe + "\x00\ud800")
        for mobile in (False, True):
            for theme in cards.PALETTES:
                with self.subTest(mobile=mobile, theme=theme):
                    svg = cards.render(value, theme, mobile)
                    cards.validate(svg)
                    root = ET.fromstring(svg)
                    self.assertFalse(any(node.tag.endswith("}script") for node in root.iter()))
                    self.assertEqual(root.find("{http://www.w3.org/2000/svg}title").text, 'safe<&"name')
                    self.assertIn("&lt;script&gt;", svg)
                    self.assertNotIn("\x00", svg)

    def test_long_names_and_mixed_descriptions_wrap_without_smaller_fonts(self):
        value = project(
            name="a-very-long-repository-name-with-more-than-a-normal-title-can-fit" * 3,
            description=("计算机系统和项目记录 with-long-identifiers-and-English words " * 30),
        )
        for mobile in (False, True):
            for theme in cards.PALETTES:
                with self.subTest(mobile=mobile, theme=theme):
                    svg = cards.render(value, theme, mobile)
                    cards.validate(svg)
                    root = ET.fromstring(svg)
                    text = [node for node in root.iter() if node.tag.endswith("}text")]
                    title = next(node for node in text if node.attrib.get('class') == 'card-title')
                    self.assertEqual(title.attrib["font-size"], "28" if mobile else "34")
                    self.assertTrue(title.text.endswith("…"))
                    self.assertTrue(all(float(node.attrib["font-size"]) >= 18 for node in text))
                    self.assertIn("…", " ".join(node.text or "" for node in text if node.attrib.get('class') == 'card-description'))

    def test_empty_metadata_and_empty_repository_have_honest_fallbacks(self):
        value = project(description=None, language=None, pushedAt=None, stars=0, forks=0)
        for mobile in (False, True):
            svg = cards.render(value, "dark", mobile)
            cards.validate(svg)
            words = " ".join(text_nodes(svg))
            self.assertIn("仓库暂无描述", words)
            self.assertIn("未标注语言", words)
            self.assertIn('aria-label="Star 0"', svg)
            self.assertIn('aria-label="Fork 0"', svg)
            self.assertIn("暂无代码更新", words)

    def test_large_exact_statistics_and_long_language_stay_visible(self):
        value = project(language="An unusually long language name " * 20, stars=1234567890, forks=1987654321)
        for mobile in (False, True):
            svg = cards.render(value, "light", mobile)
            cards.validate(svg)
            words = " ".join(text_nodes(svg))
            self.assertIn("1,234,567,890", words)
            self.assertIn("1,987,654,321", words)

    def test_changing_api_numbers_changes_visible_card(self):
        first = " ".join(text_nodes(cards.render(project(stars=9, forks=1), "light", False)))
        second = " ".join(text_nodes(cards.render(project(stars=10, forks=2), "light", False)))
        self.assertIn("9", first)
        self.assertIn("10", second)
        self.assertNotEqual(first, second)
        with self.assertRaises(ValueError):
            cards.render(project(stars=-1), "dark", False)
        with self.assertRaises(ValueError):
            cards.render(project(forks=True), "dark", True)

    def test_reviewed_summaries_yield_to_new_repository_descriptions(self):
        snapshot = __import__('json').loads((cards.ROOT / 'data/github-profile.json').read_text(encoding='utf-8'))
        for value in snapshot['projects']:
            with self.subTest(name=value['name']):
                name, summary = cards.display_copy(value)
                if value['name'] in cards.PROJECT_DISPLAY:
                    self.assertEqual(name, cards.PROJECT_DISPLAY[value['name']]['title'])
                    self.assertEqual(summary, cards.PROJECT_DISPLAY[value['name']]['summary'])
                changed = dict(value, description='New capability published after this card was designed.')
                self.assertEqual(cards.display_copy(changed)[1], changed['description'])
                svg = cards.render(changed, 'light', False)
                cards.validate(svg)
                self.assertIn('New capability', ' '.join(text_nodes(svg)))

    def test_contributed_cards_identify_upstream_owner_and_verified_prs(self):
        value = project(name='VisualLaTeX', fullName='Escap1ng/VisualLaTeX', owner='Escap1ng',
                        relationship='contributor', contribution=dict(mergedPullRequests=2))
        for mobile in (False, True):
            for theme in cards.PALETTES:
                svg = cards.render(value, theme, mobile)
                cards.validate(svg)
                words = ' '.join(text_nodes(svg))
                self.assertIn('贡献者 · Escap1ng', words)
                self.assertIn('已核验 2 个合并 PR', words)
                self.assertNotIn('自有项目', words)
                self.assertIn('data-art="latex"', svg)
        self.assertEqual(cards.asset_key(value), 'upstream/Escap1ng/VisualLaTeX')
        self.assertNotEqual(cards.asset_key(value), cards.asset_key(project(name='Escap1ng--VisualLaTeX')))
        other = dict(value, fullName='OtherOwner/VisualLaTeX', owner='OtherOwner')
        self.assertNotEqual(cards.asset_key(value), cards.asset_key(other))
        with self.assertRaises(ValueError):
            cards.asset_key(dict(value, fullName='../VisualLaTeX'))

    def test_same_named_upstream_does_not_inherit_owned_project_copy_or_art(self):
        snapshot = __import__('json').loads((cards.ROOT / 'data/github-profile.json').read_text(encoding='utf-8'))
        owned = next(value for value in snapshot['repositories'] if value['name'] == 'npm-safe')
        other = dict(owned, fullName='OtherOwner/npm-safe', owner='OtherOwner',
                     relationship='contributor', contribution=dict(mergedPullRequests=1))
        self.assertEqual(cards.display_copy(other)[1], owned['description'])
        svg = cards.render(other, 'light', False)
        self.assertIn('data-art="repo"', svg)
        self.assertNotIn('data-art="package"', svg)


if __name__ == "__main__":
    unittest.main()
