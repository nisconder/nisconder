"""Render selected public GitHub projects as self-contained, animated SVG cards.

The collector owns network access. This module only reads its normalized snapshot.
"""
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
from html import escape

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


def project_copy(project):
    name = clean_text(project["name"])
    description = clean_text(project.get("description")) or "仓库暂无描述"
    language = fit_text(clean_text(project.get("language")) or "未标注语言", 18, 180)
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


def package_art(mobile):
    if mobile:
        art = '''<g transform="translate(20 10)" fill="none" stroke="var(--ice)" stroke-width="1.5">
          <path d="m0 9 22-9 22 9v34l-22 10-22-10Z"/><path d="m0 9 22 10 22-10M22 19v34M11 4l22 10v13"/>
          <path class="scanner" d="M-4 27h52" stroke="var(--copper)" stroke-width="2"/>
        </g><path class="flow" d="M84 37h54"/><path d="m130 32 7 5-7 5" fill="none" stroke="var(--ice)" stroke-width="1.5"/>'''
        art += text(157, 29, "scripts", 18, "ice", mono=True)
        art += text(157, 56, "files → evidence", 18, "muted", mono=True)
        art += '<path d="M361 24h27M361 35h15M361 46h23" stroke="var(--line)" stroke-width="3" stroke-linecap="round"/>'
        return art
    art = '''<g transform="translate(12 29)" fill="none" stroke="var(--ice)" stroke-width="1.7">
      <path d="m0 12 29-12 29 12v44L29 69 0 56Z"/><path d="m0 12 29 13 29-13M29 25v44M14 6l30 13v17"/>
      <path class="scanner" d="M-5 35h68" stroke="var(--copper)" stroke-width="2"/>
    </g><path class="flow" d="M87 64h38"/>
    <path d="m117 59 7 5-7 5" fill="none" stroke="var(--ice)" stroke-width="1.5"/>
    <g fill="none" stroke="var(--line)" stroke-width="1.5"><path d="M141 17h169M141 58h169M141 99h169"/></g>
    <g fill="var(--ice)"><circle class="evidence-dot" cx="145" cy="33" r="3"/><circle class="evidence-dot delayed" cx="145" cy="74" r="3"/><circle class="evidence-dot late" cx="145" cy="115" r="3"/></g>'''
    return art + text(158, 40, "scripts", fill="ice", mono=True) + text(158, 81, "files", fill="muted", mono=True) + text(158, 122, "evidence", fill="muted", mono=True)


def port_art(mobile):
    if mobile:
        art = '''<path class="wire" d="M122 36h42l31-21h61m-92 21 31 22h61"/>
          <path class="flow" d="M122 36h42l31-21h61m-92 21 31 22h61"/>
          <circle cx="164" cy="36" r="4" fill="var(--ice)"/>
          <circle class="evidence-dot delayed" cx="263" cy="15" r="4" fill="var(--copper)"/><circle class="evidence-dot late" cx="263" cy="58" r="4" fill="var(--ice)"/>'''
        return art + text(14, 42, "localhost", 18, mono=True) + text(279, 21, "IPv6", 18, "ice", mono=True) + text(279, 64, "IPv4", 18, "muted", mono=True)
    art = '''<path class="wire" d="M130 61h23l28-36h35m-63 36 28 37h35"/>
      <path class="flow" d="M130 61h23l28-36h35m-63 36 28 37h35"/>
      <circle cx="153" cy="61" r="4" fill="var(--ice)"/>
      <circle class="evidence-dot delayed" cx="218" cy="25" r="4" fill="var(--copper)"/>
      <circle class="evidence-dot late" cx="218" cy="98" r="4" fill="var(--ice)"/>'''
    return art + text(0, 68, "localhost", 22, mono=True) + text(234, 32, "::1", fill="ice", mono=True) + text(234, 105, "IPv4", fill="muted", mono=True)


def unicode_art(mobile):
    if mobile:
        art = '''<rect x="73" y="10" width="128" height="40" rx="6" fill="var(--surface)" stroke="var(--ice)" stroke-width="1.3"/>
          <path class="text-scanner" d="M83 7v46" stroke="var(--copper)" stroke-width="2"/>
          <path d="M248 20h17m-7-7 7 7-7 7" fill="none" stroke="var(--line)" stroke-width="1.5"/>'''
        return art + text(32, 36, "na", 22, mono=True) + text(88, 36, "[ZWSP]", 22, "ice", mono=True) + text(213, 36, "me", 22, mono=True) + text(288, 36, "U+200B", 20, "copper", mono=True) + text(32, 65, "零宽空格 · 原文不改写", 18, "muted")
    art = '''<rect x="46" y="19" width="129" height="42" rx="6" fill="var(--canvas)" stroke="var(--ice)" stroke-width="1.3"/>
      <path class="text-scanner" d="M55 16v48" stroke="var(--copper)" stroke-width="2"/>
      <path d="M109 70v13h48" fill="none" stroke="var(--line)" stroke-width="1.5"/>
      <circle cx="109" cy="70" r="3" fill="var(--copper)"/>'''
    return art + text(5, 47, "na", 26, mono=True) + text(60, 47, "[ZWSP]", 24, "ice", mono=True) + text(188, 47, "me", 26, mono=True) + text(172, 92, "U+200B", fill="copper", mono=True)


def diff_art(mobile):
    if mobile:
        art = '''<rect x="14" y="8" width="137" height="57" rx="5" fill="var(--surface)" stroke="var(--line)"/>
          <rect x="260" y="8" width="137" height="57" rx="5" fill="var(--surface)" stroke="var(--line)"/>
          <path class="flow" d="M166 36h78"/>
          <path class="diff-before" d="M94 27h38M94 42h22M94 54h33" stroke="var(--copper)" stroke-width="2" stroke-linecap="round"/>
          <path class="diff-after" d="M338 27h40M338 42h40M338 54h21" stroke="var(--ice)" stroke-width="2" stroke-linecap="round"/>'''
        return art + text(26, 43, "A.tgz", 18, "muted", mono=True) + text(273, 43, "B.tgz", 18, "ice", mono=True)
    art = '''<rect x="3" y="10" width="119" height="105" rx="6" fill="var(--canvas)" stroke="var(--line)"/>
      <rect x="200" y="10" width="119" height="105" rx="6" fill="var(--canvas)" stroke="var(--line)"/>
      <path class="flow" d="M135 64h52"/>
      <path d="m180 59 7 5-7 5" fill="none" stroke="var(--ice)" stroke-width="1.5"/>
      <path class="diff-before" d="M19 67h70M19 82h49M19 97h64" stroke="var(--copper)" stroke-width="2" stroke-linecap="round"/>
      <path class="diff-after" d="M216 67h70M216 82h70M216 97h40" stroke="var(--ice)" stroke-width="2" stroke-linecap="round"/>'''
    return art + text(19, 44, "A.tgz", fill="muted", mono=True) + text(216, 44, "B.tgz", fill="ice", mono=True)


def bits_art(mobile):
    if mobile:
        art = text(13, 27, "AX 8000h", 22, "ice", mono=True) + text(13, 59, "OF 1 · CF 0", 18, "muted", mono=True)
        for bit in range(16):
            x = 161 + bit * 15
            art += f'<rect x="{x}" y="19" width="11" height="28" rx="2" fill="var(--{("ice" if bit==0 else "surface")})" stroke="var(--{("ice" if bit==0 else "line")})" class="{("bit-glow" if bit==0 else "")}"/>'
        return art
    art = text(5, 31, "AX", fill="muted", mono=True) + text(5, 72, "8000", 36, "ice", 600, mono=True) + text(138, 65, "OF 1 · CF 0", fill="muted", mono=True)
    for bit in range(16):
        x = 6 + bit * 19
        art += f'<rect x="{x}" y="94" width="14" height="20" rx="2" fill="var(--{("ice" if bit==0 else "canvas")})" stroke="var(--{("ice" if bit==0 else "line")})" class="{("bit-glow" if bit==0 else "")}"/>'
    return art


def repo_art(mobile):
    if mobile:
        art = '''<rect x="14" y="9" width="117" height="54" rx="6" fill="var(--surface)" stroke="var(--line)"/>
          <path class="flow" d="M146 36h80"/><path d="m218 31 8 5-8 5" fill="none" stroke="var(--ice)" stroke-width="1.5"/>
          <path class="wire" d="M254 36h126m-66 0V15h36"/>
          <circle class="evidence-dot" cx="255" cy="36" r="5" fill="var(--ice)"/>
          <circle class="evidence-dot delayed" cx="315" cy="36" r="5" fill="var(--ice)"/>
          <circle class="evidence-dot late" cx="379" cy="36" r="5" fill="var(--copper)"/>
          <circle cx="350" cy="15" r="4" fill="var(--surface)" stroke="var(--ice)"/>'''
        return art + text(35, 43, "repo", 20, "ice", mono=True)
    art = '''<rect x="3" y="13" width="100" height="99" rx="7" fill="var(--canvas)" stroke="var(--line)"/>
      <path d="M20 68h64M20 82h45M20 96h55" stroke="var(--line)" stroke-width="2" stroke-linecap="round"/>
      <path class="flow" d="M117 64h48"/>
      <path d="m158 59 7 5-7 5" fill="none" stroke="var(--ice)" stroke-width="1.5"/>
      <path class="wire" d="M180 64h128m-72 0V25h43"/>
      <circle class="evidence-dot" cx="181" cy="64" r="5" fill="var(--ice)"/>
      <circle class="evidence-dot delayed" cx="237" cy="64" r="5" fill="var(--ice)"/>
      <circle class="evidence-dot late" cx="307" cy="64" r="5" fill="var(--copper)"/>
      <circle cx="279" cy="25" r="4" fill="var(--surface)" stroke="var(--ice)"/>'''
    return art + text(19, 46, "repo", 22, "ice", mono=True) + text(180, 107, "commit", 20, "muted", mono=True)


ART = dict(package=package_art, port=port_art, unicode=unicode_art, diff=diff_art, bits=bits_art, repo=repo_art)


def render(project, theme, mobile):
    p = PALETTES[theme]
    name, description, stats, updated = project_copy(project)
    kind = PROJECT_ART.get(project["name"], "repo")
    width = 480 if mobile else 1100
    description_size = 20 if mobile else 22
    copy_width = 432 if mobile else 650
    description_lines = wrap_text(description, description_size, copy_width)
    stats_lines = wrap_text(stats, 18, copy_width, max_lines=2)
    height = 288 + (len(stats_lines) - 1) * 28 if mobile else 224 + (len(stats_lines) - 1) * 28
    variables = ";".join(f"--{key}:{value}" for key, value in p.items())
    style = f"""
      :root{{{variables}}}
      text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans CJK SC','Microsoft YaHei',sans-serif}}
      .mono{{font-family:Consolas,'Cascadia Code','SFMono-Regular',monospace}}
      .wire{{fill:none;stroke:var(--line);stroke-width:1.8}}
      .flow{{fill:none;stroke:var(--ice);stroke-width:1.5;stroke-dasharray:4 8;opacity:.65;animation:flow 4.8s linear infinite}}
      .scanner{{animation:package-scan 4.8s ease-in-out infinite}}
      .text-scanner{{animation:text-scan 4.8s ease-in-out infinite}}
      .evidence-dot{{animation:glow 4.8s ease-in-out infinite}}
      .delayed{{animation-delay:1.2s}}.late{{animation-delay:2.4s}}
      .diff-before{{animation:before 4.8s ease-in-out infinite}}.diff-after{{animation:after 4.8s ease-in-out infinite}}
      .bit-glow{{animation:glow 4.8s ease-in-out infinite}}
      @keyframes flow{{to{{stroke-dashoffset:-48}}}}
      @keyframes package-scan{{0%,100%{{transform:translateY(-12px)}}50%{{transform:translateY(12px)}}}}
      @keyframes text-scan{{0%,100%{{transform:translateX(0)}}50%{{transform:translateX(100px)}}}}
      @keyframes glow{{0%,100%{{opacity:.65}}45%,65%{{opacity:1}}}}
      @keyframes before{{0%,100%{{opacity:1}}40%,70%{{opacity:.5}}}}
      @keyframes after{{0%,100%{{opacity:.6}}40%,70%{{opacity:1}}}}
      @media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}.flow{{stroke-dasharray:none}}.bit-glow,.evidence-dot,.diff-before,.diff-after{{opacity:1}}}}
    """
    if mobile:
        body = text(24, 42, fit_text(name, 26, 390), 26, weight=650)
        for i, line in enumerate(description_lines):
            body += text(24, 78 + i * 28, line, 20)
        for i, line in enumerate(stats_lines):
            body += text(24, 148 + i * 28, line, 18, "muted")
        body += text(24, 178 + (len(stats_lines) - 1) * 28, updated, 18, "muted")
        art_y = 198 + (len(stats_lines) - 1) * 28
        body += f'<rect x="20" y="{art_y}" width="440" height="74" rx="10" fill="var(--canvas)"/>'
        body += f'<g transform="translate(25 {art_y})">{ART[kind](True)}</g>'
        body += '<path d="M435 25h14v14m-14 0 14-14" fill="none" stroke="var(--muted)" stroke-width="1.6"/>'
    else:
        body = text(34, 50, fit_text(name, 32, 650), 32, weight=650)
        for i, line in enumerate(description_lines):
            body += text(34, 92 + i * 32, line, 22)
        for i, line in enumerate(stats_lines):
            body += text(34, 163 + i * 28, line, 18, "muted")
        body += text(34, 196 + (len(stats_lines) - 1) * 28, updated, 18, "muted")
        body += '<path d="M1050 27h17v17m-17 0 17-17" fill="none" stroke="var(--muted)" stroke-width="1.6"/>'
        body += f'<g transform="translate(736 {(height - 128) / 2})">{ART[kind](False)}</g>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
      <title id="title">{escape(name)}</title>
      <desc id="description">{escape(name + '：' + description + '。' + stats + '。' + updated)}。动画为功能示意，统计来自 GitHub 数据；动画关闭后内容仍可读。</desc>
      <style>{style}</style>
      <rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="18" fill="var(--surface)" stroke="var(--line)"/>
      {body}
    </svg>'''


def validate(source):
    root = ET.fromstring(source)
    width, height = map(float, root.attrib["viewBox"].split()[2:])
    assert "prefers-reduced-motion:reduce" in source
    # Account for our translated illustration groups while checking every text anchor.
    def visit(node, tx=0, ty=0):
        tag = node.tag.rsplit("}", 1)[-1]
        assert tag.lower() not in {"script", "foreignobject", "image"}
        assert not any(key.rsplit("}", 1)[-1].lower() == "href" or key.lower().startswith("on") for key in node.attrib)
        if tag == "style":
            assert "url(" not in (node.text or "")
        transform = node.attrib.get("transform", "")
        match = re.fullmatch(r"translate\(([-\d.]+)[ ,]+([-\d.]+)\)", transform)
        if match:
            tx += float(match[1]); ty += float(match[2])
        if tag == "text":
            x = float(node.attrib.get("x", 0)) + tx
            y = float(node.attrib.get("y", 0)) + ty
            assert 0 <= x <= width and 0 <= y <= height, (x, y, width, height)
            size = float(node.attrib["font-size"])
            assert size >= 18
            # Conservative text extent check, followed by the owner's browser QA.
            value = "".join(node.itertext())
            extent = text_width(value, size)
            assert y - size >= 0 and y + size * .3 <= height, (value, y, height)
            assert x + extent <= width - 12, (value, x + extent, width)
        for child in node:
            visit(child, tx, ty)
    visit(root)


def main(profile=None):
    if profile is None:
        profile = json.loads((ROOT / "data" / "github-profile.json").read_text(encoding="utf-8-sig"))
    projects = profile["projects"]
    if not isinstance(projects, list):
        raise ValueError("The profile snapshot must contain a projects list")
    count = 0
    paths = []
    for project in projects:
        for mobile in (False, True):
            for theme in ("dark", "light"):
                source = render(project, theme, mobile)
                validate(source)
                variant = f"mobile-{theme}" if mobile else theme
                path = OUT / f"{asset_key(project)}-{variant}.svg"
                path.write_text(source, encoding="utf-8", newline="\n")
                paths.append(path)
                count += 1
    print(f"Generated and validated {count} self-contained SVG cards.")
    return paths


if __name__ == "__main__":
    main()
