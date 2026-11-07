"""Original profile identity and an honestly dated contribution snapshot.

Standard library only. The contribution data is a saved GitHub GraphQL response;
running this generator does not make network calls or execute project code.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PALETTES = {
    "dark": dict(bg="#0d1421", surface="#121d2e", line="#283b54", ink="#ecf2fa", muted="#a6b7ca", ice="#88bfff", gold="#d9ba85", zero="#17263c", levels=["#17263c", "#274766", "#3c729b", "#69a4c2", "#b0d4e1"]),
    "light": dict(bg="#f7f9fc", surface="#ffffff", line="#d6e0eb", ink="#1b2d46", muted="#526985", ice="#2674bc", gold="#a26f25", zero="#e6edf5", levels=["#e6edf5", "#bdd4e6", "#83b3d2", "#4a8cb9", "#25618f"]),
}


def esc(value):
    return html.escape(str(value), quote=True)


def text(x, y, value, size=22, fill="ink", *, p, anchor=None, weight=None, spacing=None, cls=""):
    attrs = f'x="{x}" y="{y}" font-size="{size}" fill="{p.get(fill, fill)}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if spacing is not None:
        attrs += f' letter-spacing="{spacing}"'
    if cls:
        attrs += f' class="{cls}"'
    return f'<text {attrs}>{esc(value)}</text>'


def wrap(width, height, name, description, content, css=""):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{esc(name)}</title><desc id="desc">{esc(description)}</desc>
<style>
text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans CJK SC','Microsoft YaHei',sans-serif}} .mono{{font-family:Consolas,'Cascadia Code',monospace}}
{css}
@media(prefers-reduced-motion:reduce){{.motion,.motion *{{animation:none!important}} .moving-mark{{display:none}}}}
</style>{content}</svg>'''


def hero(p, mobile=False):
    w, h = (480, 196) if mobile else (1100, 210)
    cx = w / 2
    # The contours are original curves; they illustrate a visual field, not data.
    contours = []
    for i in range(9):
        y = h - 28 + i * 7
        d = f'M-30 {y} C{w*.2:.0f} {y-72-i*2} {w*.33:.0f} {y+33} {cx} {y-15} S{w*.82:.0f} {y-50-i*2} {w+30} {y-5}'
        contours.append(f'<path d="{d}" fill="none" stroke="{p["ice"]}" stroke-width=".8" opacity="{.07+i*.009:.3f}"/>')
    signal = f'M0 {h-20} C{w*.25:.0f} {h-76} {w*.4:.0f} {h+10} {cx} {h-35} S{w*.8:.0f} {h-65} {w} {h-20}'
    content = f'''<defs>
<radialGradient id="mist"><stop stop-color="{p['ice']}" stop-opacity=".12"/><stop offset="1" stop-color="{p['bg']}" stop-opacity="0"/></radialGradient>
<linearGradient id="edge"><stop stop-color="{p['ice']}" stop-opacity="0"/><stop offset=".5" stop-color="{p['gold']}" stop-opacity=".65"/><stop offset="1" stop-color="{p['ice']}" stop-opacity="0"/></linearGradient>
<clipPath id="crop"><rect width="{w}" height="{h}" rx="15"/></clipPath></defs>
<g clip-path="url(#crop)"><rect width="{w}" height="{h}" fill="{p['bg']}"/>
<ellipse cx="{cx}" cy="{h+100}" rx="{w*.7}" ry="230" fill="url(#mist)"/>
{''.join(contours)}
<path d="{signal}" fill="none" stroke="{p['gold']}" stroke-width="1" opacity=".12"/>
<circle class="moving-mark" r="2.1" fill="{p['gold']}" opacity=".8"><animateMotion dur="18s" repeatCount="indefinite" path="{signal}"/></circle>
{text(cx,94 if mobile else 106,'Nisconder',48 if mobile else 72,p=p,anchor='middle',weight=650,spacing=-2)}
{text(cx,134 if mobile else 150,'开发工具与技术笔记',20 if mobile else 24,p=p,anchor='middle',fill='muted')}
<path d="M20 {h-1}h{w-40}" stroke="url(#edge)"/></g>'''
    return wrap(w, h, "Nisconder", "Nisconder 的个人主页。代码、工具与记录；底部有缓慢经过轮廓曲线的信号，静态时全部文字仍可读。", content)


def activity(p, data, mobile=False):
    weeks = data['weeks'][-26:] if mobile else data['weeks']
    w, h = (480, 174) if mobile else (1100, 208)
    pitch, size = (16,10) if mobile else (18.3,12)
    x0 = (w - ((len(weeks)-1)*pitch+size))/2
    y0 = 62 if mobile else 71
    count = sum(d['contributionCount'] for week in weeks for d in week['contributionDays'])
    title = '近半年贡献' if mobile else 'GitHub 贡献'
    content = [f'<defs><clipPath id="activity-crop"><rect x="{x0}" y="{y0}" width="{w-2*x0}" height="108"/></clipPath><linearGradient id="sweep"><stop stop-color="{p["ice"]}" stop-opacity="0"/><stop offset=".5" stop-color="{p["ice"]}" stop-opacity=".15"/><stop offset="1" stop-color="{p["ice"]}" stop-opacity="0"/></linearGradient></defs>', f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="12" fill="{p["bg"]}" stroke="{p["line"]}"/>', text(24 if mobile else 40,32 if mobile else 35,title,20 if mobile else 22,p=p,weight=500), text(w-(24 if mobile else 40),32 if mobile else 35,f'{count} 次贡献',16 if mobile else 18,p=p,anchor='end',fill='muted')]
    level_keys = ['NONE','FIRST_QUARTILE','SECOND_QUARTILE','THIRD_QUARTILE','FOURTH_QUARTILE']
    for col, week in enumerate(weeks):
        for day in week['contributionDays']:
            from datetime import date
            weekday = (date.fromisoformat(day['date']).weekday()+1)%7
            level = level_keys.index(day['contributionLevel'])
            content.append(f'<rect x="{x0+col*pitch:.1f}" y="{y0+weekday*14}" width="{size}" height="{size}" rx="2" fill="{p["levels"][level]}"><title>{day["date"]}: {day["contributionCount"]} contributions</title></rect>')
    # A slow wash passes above the real grid. It never changes the underlying values.
    content += [f'<g clip-path="url(#activity-crop)"><rect class="moving-mark" x="{x0}" y="{y0}" width="100" height="100" fill="url(#sweep)"><animateTransform attributeName="transform" type="translate" from="-110 0" to="{w} 0" dur="16s" repeatCount="indefinite"/></rect></g>', text(24 if mobile else 40,h-15,f'数据快照 {data["snapshotDate"]}',14 if mobile else 16,p=p,fill='muted')]
    return wrap(w,h,'Nisconder 的贡献日历',f'截至 {data["snapshotDate"]} 的真实 GitHub 贡献数据快照，图中显示 {count} 次贡献。不是实时统计。', ''.join(content))


def section(p, mobile=False):
    w,h=(480,55) if mobile else (1100,64)
    return wrap(w,h,'项目','以下项目卡片可点击进入各自仓库。', text(0,36,'项目',24 if mobile else 28,p=p,weight=600))


def notes(p, mobile=False):
    w,h=(480,136) if mobile else (1100,120)
    content=f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="12" fill="{p["bg"]}" stroke="{p["line"]}"/>'
    content+=text(25 if mobile else 38,44 if mobile else 49,'技术笔记',26 if mobile else 28,p=p,weight=600)
    content+=text(25 if mobile else 38,79 if mobile else 87,'计算机系统、工具开发与使用记录',18 if mobile else 22,p=p,fill='muted')
    if mobile: content+=text(455,116,'文章列表 ↗',18,p=p,anchor='end',fill='ice')
    else: content+=text(1062,65,'文章列表 ↗',18,p=p,anchor='end',fill='ice')
    return wrap(w,h,'技术笔记','计算机系统、工具开发与使用记录。',content)


def main():
    data = json.loads((ROOT/'data/contributions.json').read_text(encoding='utf-8-sig'))
    assert sum(d['contributionCount'] for w in data['weeks'] for d in w['contributionDays']) == data['totalContributions']
    ASSETS.mkdir(exist_ok=True)
    for mode,p in PALETTES.items():
        for mobile in [False,True]:
            suffix=('mobile-' if mobile else '')+mode
            for name, renderer in [('hero',hero),('section',section),('notes',notes)]:
                svg=renderer(p,mobile)
                ET.fromstring(svg)
                (ASSETS/f'{name}-{suffix}.svg').write_text(svg,encoding='utf-8')
            svg=activity(p,data,mobile)
            ET.fromstring(svg)
            (ASSETS/f'activity-{suffix}.svg').write_text(svg,encoding='utf-8')
    print('Generated 16 identity SVGs; contribution counts reconcile with the saved GitHub snapshot.')


if __name__=='__main__':
    main()
