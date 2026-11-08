"""Render selected public GitHub projects as self-contained, animated SVG cards.

The collector owns network access. This module only reads its normalized snapshot.
"""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
from html import escape
from project_art import ART_HEIGHT, ART_STYLE, render_art

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "cards"
OUT.mkdir(parents=True, exist_ok=True)

PALETTES = {
    "dark": dict(canvas="#0d1421", surface="#121d2e", line="#283b54", ink="#ecf2fa", muted="#a6b7ca", ice="#88bfff", copper="#d9ba85"),
    "light": dict(canvas="#f7f9fc", surface="#ffffff", line="#d6e0eb", ink="#1b2d46", muted="#526985", ice="#2674bc", copper="#a26f25"),
}

PROJECT_ART = {
    "npm-safe": "package", "portdoc": "port", "paste-xray": "unicode",
    "pack-receipt": "diff", "8086-step-lab": "bits",
    "npm-safe-forDSH": "harness", "nisconder.github.io": "notes",
    "ai-draw-guess": "guess",
}


def clean_text(value):
    """Collapse metadata whitespace and omit characters forbidden by XML 1.0."""
    value = "" if value is None else str(value)
    value = "".join(char for char in value if (ord(char) >= 32 and ord(char) not in (0xFFFE, 0xFFFF)
                    and not 0xD800 <= ord(char) <= 0xDFFF) or char in "\t\r\n")
    return " ".join(value.split())


def text_width(value, size):
    # Deliberately conservative: no font downloads or rasterizer are needed in CI.
    return sum(0 if unicodedata.combining(char) else size * (1.05 if ord(char) > 0x2FFF else .65)
               for char in value)


def fit_text(value, size, max_width):
    value = clean_text(value)
    if text_width(value, size) <= max_width:
        return value
    while value and text_width(value.rstrip() + "…", size) > max_width:
        value = value[:-1]
    return value.rstrip() + "…"


def wrap_text(value, size, max_width, max_lines=2):
    remaining, lines = clean_text(value), []
    while remaining and len(lines) < max_lines:
        if text_width(remaining, size) <= max_width:
            lines.append(remaining)
            break
        if len(lines) == max_lines - 1:
            lines.append(fit_text(remaining, size, max_width))
            break
        length = 0
        while length < len(remaining) and text_width(remaining[:length + 1], size) <= max_width:
            length += 1
        # Prefer whole English words, but still wrap long identifiers and CJK text.
        space = remaining.rfind(" ", 0, length + 1)
        if space >= max(1, length // 2):
            length = space
        lines.append(remaining[:length].rstrip())
        remaining = remaining[length:].lstrip()
    return lines


def asset_key(project):
    name = project["name"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in (".", ".."):
        raise ValueError("A project asset requires a valid GitHub repository name")
    return "8086-lab" if name == "8086-step-lab" else name


def updated_date(project):
    value = project.get("pushedAt")
    if not value:
        return "暂无代码更新"
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("pushedAt must contain a timezone")
    return "代码更新 " + timestamp.astimezone(timezone(timedelta(hours=8))).date().isoformat()


def display_copy(project):
    entry = PROJECT_DISPLAY.get(project["name"], {})
    original = clean_text(project.get("description"))
    reviewed = entry.get("descriptionSha256") == hashlib.sha256(original.encode()).hexdigest()
    name = entry.get("title") or clean_text(project["name"])
    description = entry.get("summary") if reviewed else original
    return clean_text(name), clean_text(description) or "仓库暂无描述"


def project_copy(project):
    name, description = display_copy(project)
    language = fit_text(clean_text(project.get("language")) or "未标注语言", 20, 180)
    counts = [project.get("stars", 0), project.get("forks", 0)]
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts):
        raise ValueError("Project stars and forks must be non-negative integers")
    stats = f"{language} · Star {counts[0]:,} · Fork {counts[1]:,}"
    updated = updated_date(project)
    return name, description, stats, updated


def text(x, y, value, size=22, fill="ink", weight=400, mono=False, anchor=None):
    attrs = f'x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="var(--{fill})"'
    if mono:
        attrs += ' class="mono"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    return f'<text {attrs}>{escape(value)}</text>'


PROJECT_DISPLAY = json.loads((ROOT / "data/project-display.json").read_text(encoding="utf-8"))

# Official GitHub Octicons, MIT. See assets/OCTICONS-LICENSE.txt.
ICONS = {
    "Star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5a.75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.75.75 0 0 1 .216.664l-.528 3.084 2.769-1.456a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 0 0 1 .216-.664l2.24-2.183-3.096-.45a.75.75 0 0 1-.564-.41L8 2.694Z",
    "Fork": "M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z",
}


def metric(x, baseline, label, value):
    formatted = f"{value:,}"
    return (f'<g role="img" aria-label="{label} {formatted}"><title>{label} {formatted}</title>'
            f'<g transform="translate({x} {baseline-17}) scale(1.25)" fill="var(--muted)"><path d="{ICONS[label]}"/></g>'
            + text(x+30, baseline, formatted, 20, "muted") + '</g>')


def render(project, theme, mobile):
    p = PALETTES[theme]
    name, description, stats, updated = project_copy(project)
    kind = PROJECT_ART.get(project["name"], "repo")
    width = 400 if mobile else 1100
    description_size = 22 if mobile else 24
    copy_width = 352 if mobile else 620
    lines = wrap_text(description, description_size, copy_width, max_lines=3)
    title_size = 28 if mobile else 34
    body = text(24 if mobile else 32, 46 if mobile else 52,
                fit_text(name, title_size, 308 if mobile else 620), title_size, weight=650)
    first_line, line_height = (86, 31) if mobile else (102, 34)
    for index, line in enumerate(lines):
        body += text(24 if mobile else 32, first_line + index*line_height, line, description_size)
    last_line = first_line + (len(lines)-1)*line_height
    body += f'<path d="M{width-47} 27h15v15m-15 0 15-15" fill="none" stroke="var(--muted)" stroke-width="1.6"/>'
    if mobile:
        art_y = last_line + 24
        body += f'<g transform="translate(50 {art_y})">{render_art(kind,p,True)}</g>'
        footer_y = art_y + ART_HEIGHT + 20
        baseline = footer_y + 32
        body += text(24, baseline, fit_text(clean_text(project.get("language")) or "未标注语言", 20, 140), 20, "muted")
        metric_x, metric_y = 188, baseline
        for label, value in [("Star", project["stars"]), ("Fork", project["forks"])]:
            metric_width = 30 + text_width(f"{value:,}", 20)
            if metric_x + metric_width > width-24:
                metric_x, metric_y = 24, metric_y+32
            body += metric(metric_x, metric_y, label, value)
            metric_x += metric_width+24
        body += text(24, metric_y+34, updated.replace("代码更新 ", "更新 "), 20, "muted")
        height = metric_y+60
    else:
        footer_y = max(184, last_line+36)
        body += f'<path d="M708 28v{footer_y-52}" stroke="var(--line)"/>'
        body += f'<g transform="translate(750 {(footer_y-ART_HEIGHT)/2})">{render_art(kind,p,False)}</g>'
        baseline = footer_y+37
        body += text(32, baseline, fit_text(clean_text(project.get("language")) or "未标注语言", 20, 180), 20, "muted")
        metric_x = 250
        for label, value in [("Star", project["stars"]), ("Fork", project["forks"])]:
            body += metric(metric_x, baseline, label, value)
            metric_x += 30 + text_width(f"{value:,}", 20)+44
        body += text(1068, baseline, updated.replace("代码更新 ", "更新 "), 20, "muted", anchor="end")
        height = footer_y+64
    body += f'<path d="M1 {footer_y}h{width-2}" stroke="var(--line)"/>'
    variables = ";".join(f"--{key}:{value}" for key,value in p.items())
    style = f""":root{{{variables}}}
text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans CJK SC','Microsoft YaHei',sans-serif}}
.mono{{font-family:Consolas,'Cascadia Code','SFMono-Regular',monospace}}
{ART_STYLE}"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
<title id="title">{escape(name)}</title>
<desc id="description">{escape(project['name']+'：'+clean_text(project.get('description'))+'。'+stats+'。'+updated)}。图形为功能示意，不是实时执行结果。</desc>
<style>{style}</style>
<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="12" fill="var(--surface)" stroke="var(--line)"/>
{body}</svg>"""


def validate(source):
    root = ET.fromstring(source)
    width,height = map(float,root.attrib["viewBox"].split()[2:])
    assert "prefers-reduced-motion:reduce" in source
    def visit(node,tx=0,ty=0):
        tag = node.tag.rsplit("}",1)[-1]
        assert tag.lower() not in {"script","foreignobject","image"}
        assert not any(key.rsplit("}",1)[-1].lower()=="href" or key.lower().startswith("on") for key in node.attrib)
        if tag=="style": assert "url(" not in (node.text or "")
        transform = node.attrib.get("transform","")
        match = re.fullmatch(r"translate\(([-\d.]+)[ ,]+([-\d.]+)\)",transform)
        if match:
            tx += float(match[1]); ty += float(match[2])
        if tag=="text":
            x=float(node.attrib.get("x",0))+tx
            y=float(node.attrib.get("y",0))+ty
            size=float(node.attrib["font-size"])
            assert size>=18
            extent=text_width("".join(node.itertext()),size)
            left=x-extent if node.attrib.get("text-anchor")=="end" else x-extent/2 if node.attrib.get("text-anchor")=="middle" else x
            assert left>=0 and left+extent<=width-12,(node.text,left,extent,width)
            assert y-size>=0 and y+size*.3<=height,(node.text,y,height)
        for child in node: visit(child,tx,ty)
    visit(root)


def main(profile=None):
    if profile is None:
        profile=json.loads((ROOT/"data/github-profile.json").read_text(encoding="utf-8-sig"))
    paths=[]
    for project in profile["projects"]:
        for mobile in (False,True):
            for theme in PALETTES:
                source=render(project,theme,mobile)
                validate(source)
                suffix=("mobile-" if mobile else "")+theme
                path=OUT/f"{asset_key(project)}-{suffix}.svg"
                path.write_text(source,encoding="utf-8",newline="\n")
                paths.append(path)
    print(f"Generated and validated {len(paths)} project SVGs.")
    return paths


if __name__=="__main__": main()
