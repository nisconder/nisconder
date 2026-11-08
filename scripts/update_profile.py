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


def select_projects(profile, limit=PROJECT_LIMIT, featured=()):
    login = profile.get('user', {}).get('login', 'nisconder')
    eligible = {}
    for repo in profile['repositories']:
        if repo['isFork'] or repo['isArchived'] or repo['isProfile']:
            continue
        full_name = f'{login}/{repo["name"]}'
        eligible[full_name.casefold()] = dict(repo, fullName=full_name, owner=login, relationship='owner')
    for repo in profile.get('contributedRepositories', []):
        if repo['isArchived'] or repo.get('contribution', {}).get('mergedPullRequests', 0) < 1:
            continue
        eligible[repo['fullName'].casefold()] = repo.copy()
    selected = []
    for full_name in featured:
        key = full_name.casefold()
        if key in eligible and key not in selected:
            selected.append(key)
    for name in profile['pinnedRepositories']:
        key = f'{login}/{name}'.casefold()
        if key in eligible and key not in selected:
            selected.append(key)
    recent = sorted(eligible)
    recent.sort(key=lambda key: eligible[key]['pushedAt'] or '', reverse=True)
    selected.extend(key for key in recent if key not in selected)
    return [eligible[key].copy() for key in selected[:limit]]


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
    projects = [picture('section', '精选项目：包含自有开发工具和已核验上游贡献的协作项目。')]
    for project in profile['projects']:
        title, description = generate_cards.display_copy(project)
        full_name = project.get('fullName', project['name'])
        label = title if title == full_name else f'{title}（{full_name}）'
        role = '贡献者' if project.get('relationship') == 'contributor' else '自有项目'
        if project.get('relationship') == 'contributor':
            role += f' · 已核验 {project["contribution"]["mergedPullRequests"]} 个合并 PR'
        alt = f'{label}：{description} · {role} · {project["stars"]} Stars · {project["forks"]} Forks'
        projects.append('<a href="' + html.escape(project['url'], quote=True) + '">\n'
                        + picture('cards/' + generate_cards.asset_key(project), alt) + '\n</a>')
        if project.get('relationship') == 'contributor':
            links = ['<a href="' + html.escape(pull['url'], quote=True) + '" title="'
                     + html.escape(pull['title'], quote=True) + '">#' + str(pull['number']) + '</a>'
                     for pull in project['contribution']['pullRequests']]
            projects.append('<p align="right">已核验的合并贡献：' + ' · '.join(links) + '</p>')
    readme = replace_region(readme, 'projects', '\n\n'.join(projects))
    return cache_asset_urls(readme)


def main():
    profile_path = ROOT / 'data/github-profile.json'
    profile = json.loads(profile_path.read_text(encoding='utf-8-sig'))
    contributions = json.loads((ROOT / 'data/contributions.json').read_text(encoding='utf-8-sig'))
    if profile['snapshotDate'] != contributions['snapshotDate']:
        raise ValueError('Profile and contributions must have the same data date')
    featured = json.loads((ROOT / 'data/featured-projects.json').read_text(encoding='utf-8'))['projects']
    profile['projects'] = select_projects(profile, featured=featured)
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    generate_identity.main()
    generate_cards.main()
    readme_path = ROOT / 'README.md'
    readme = update_readme(readme_path.read_text(encoding='utf-8'), profile, contributions)
    readme_path.write_text(readme, encoding='utf-8', newline='\n')
    print('Updated SVG statistics, contribution calendar, project cards and content-based image versions.')


if __name__ == '__main__':
    main()
