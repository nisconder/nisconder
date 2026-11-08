"""Render public GitHub snapshots into SVGs and bounded README sections.

No network calls: fetch_github_data.py supplies the validated public data first.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re

import generate_cards
import generate_identity

ROOT = Path(__file__).resolve().parents[1]
PROJECT_LIMIT = 6


def select_projects(profile, limit=PROJECT_LIMIT):
    eligible = {
        repo['name']: repo for repo in profile['repositories']
        if not repo['isFork'] and not repo['isArchived'] and not repo['isProfile']
    }
    selected = []
    for name in profile['pinnedRepositories']:
        if name in eligible and name not in selected:
            selected.append(name)
    recent = sorted(eligible, key=lambda name: name.casefold())
    recent.sort(key=lambda name: eligible[name]['pushedAt'] or '', reverse=True)
    selected.extend(name for name in recent if name not in selected)
    return [eligible[name].copy() for name in selected[:limit]]


def picture(asset, alt):
    alt = html.escape(alt, quote=True)
    return f'''<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: light)" srcset="assets/{asset}-mobile-light.svg">
  <source media="(max-width: 640px)" srcset="assets/{asset}-mobile-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/{asset}-light.svg">
  <img src="assets/{asset}-dark.svg" width="100%" alt="{alt}">
</picture>'''


def replace_region(readme, name, body):
    start, end = f'<!-- BEGIN:{name} -->', f'<!-- END:{name} -->'
    if readme.count(start) != 1 or readme.count(end) != 1:
        raise ValueError(f'README must contain one {name} marker pair')
    before, rest = readme.split(start)
    if end not in rest:
        raise ValueError(f'Invalid README marker order for {name}')
    _, after = rest.split(end)
    return before + start + '\n' + body.strip() + '\n' + end + after


def cache_asset_urls(readme, root=ROOT):
    def version(match):
        path = match.group('path')
        content = (root / path).read_bytes()
        digest = hashlib.sha256(content).hexdigest()[:10]
        return path + '?v=' + digest
    return re.sub(r'(?<![A-Za-z0-9_/:.-])(?P<path>assets/[A-Za-z0-9_./-]+\.svg)(?:\?v=[A-Za-z0-9]+)?', version, readme)


def update_readme(readme, profile, contributions):
    stats = profile['stats']
    stats_alt = (f'GitHub 公开数据：{stats["publicRepositories"]} 个公开仓库；'
                 f'自有非 Fork 仓库共 {stats["originalStars"]} Stars、{stats["originalForks"]} Forks；'
                 f'{profile["user"]["followers"]} 位关注者。每六小时自动更新，数据日期 {profile["snapshotDate"]}。')
    readme = replace_region(readme, 'stats', picture('stats', stats_alt))
    calendar = ('<a href="https://github.com/' + profile['user']['login'] + '?tab=overview">\n'
                + picture('activity', f'GitHub 贡献日历：近一年 {contributions["totalContributions"]} 次贡献；'
                          f'手机显示近半年。每六小时自动更新，数据日期 {contributions["snapshotDate"]}。') + '\n</a>')
    readme = replace_region(readme, 'activity', calendar)
    projects = [picture('section', '项目：优先 GitHub 置顶，再按最近代码更新补足六个；不含 Fork、归档及主页仓库。')]
    for project in profile['projects']:
        title, description = generate_cards.display_copy(project)
        label = title if title == project['name'] else f'{title}（{project["name"]}）'
        alt = f'{label}：{description} · {project["stars"]} Stars · {project["forks"]} Forks'
        projects.append('<a href="' + html.escape(project['url'], quote=True) + '">\n'
                        + picture('cards/' + generate_cards.asset_key(project), alt) + '\n</a>')
    readme = replace_region(readme, 'projects', '\n\n'.join(projects))
    return cache_asset_urls(readme)


def main():
    profile_path = ROOT / 'data/github-profile.json'
    profile = json.loads(profile_path.read_text(encoding='utf-8-sig'))
    contributions = json.loads((ROOT / 'data/contributions.json').read_text(encoding='utf-8-sig'))
    if profile['snapshotDate'] != contributions['snapshotDate']:
        raise ValueError('Profile and contributions must have the same data date')
    profile['projects'] = select_projects(profile)
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    generate_identity.main()
    generate_cards.main()
    readme_path = ROOT / 'README.md'
    readme = update_readme(readme_path.read_text(encoding='utf-8'), profile, contributions)
    readme_path.write_text(readme, encoding='utf-8', newline='\n')
    print('Updated SVG statistics, contribution calendar, project cards and content-based image versions.')


if __name__ == '__main__':
    main()
