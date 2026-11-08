"""Small project-specific SVG diagrams in a common 300 × 132 coordinate space.

The parent SVG supplies the viewport and embeds ART_STYLE once. Every diagram
has a complete static state; motion only points at a part of that state.
"""
from html import escape

ART_WIDTH = 300
ART_HEIGHT = 132

ART_STYLE = """
.pa-package-scan{animation:pa-package-scan 6.4s ease-in-out infinite}
.pa-harness-return{animation:pa-harness-return 6.8s linear infinite}
.pa-diff-cursor{animation:pa-diff-cursor 7.2s steps(1,end) infinite}
.pa-port-probe{animation:pa-port-probe 8s linear infinite}
.pa-notes-cursor{animation:pa-notes-cursor 7.8s steps(1,end) infinite}
.pa-bits-emphasis{animation:pa-bits-emphasis 5.6s ease-in-out infinite}
.pa-unicode-cursor{animation:pa-unicode-cursor 6s ease-in-out infinite}
.pa-guess-caret{animation:pa-guess-caret 1.8s steps(1,end) infinite}
.pa-latex-cursor{animation:pa-latex-cursor 7.2s steps(1,end) infinite}
.pa-cognition-merge{animation:pa-cognition-merge 6.6s linear infinite}
.pa-repo-cursor{animation:pa-repo-cursor 7s steps(1,end) infinite}
@keyframes pa-package-scan{0%,100%{transform:translateY(-18px)}50%{transform:translateY(18px)}}
@keyframes pa-harness-return{0%,8%{transform:translate(0,0);opacity:0}12%{opacity:1}35%{transform:translate(0,24px);opacity:1}76%{transform:translate(-81px,24px);opacity:1}94%{transform:translate(-81px,-15px);opacity:1}100%{transform:translate(-81px,-15px);opacity:0}}
@keyframes pa-diff-cursor{0%,28%{transform:translateY(0)}33%,61%{transform:translateY(26px)}66%,94%{transform:translateY(52px)}100%{transform:translateY(0)}}
@keyframes pa-port-probe{0%,5%{transform:translate(0,0);opacity:0}10%{opacity:1}22%{transform:translate(27px,0);opacity:1}36%{transform:translate(56px,-33px);opacity:1}47%{transform:translate(90px,-33px);opacity:1}50%{transform:translate(90px,-33px);opacity:0}51%,55%{transform:translate(27px,0);opacity:0}58%{opacity:1}77%{transform:translate(56px,37px);opacity:1}94%{transform:translate(90px,37px);opacity:1}100%{transform:translate(90px,37px);opacity:0}}
@keyframes pa-notes-cursor{0%,28%{transform:translateY(0)}33%,61%{transform:translateY(26px)}66%,94%{transform:translateY(52px)}100%{transform:translateY(0)}}
@keyframes pa-bits-emphasis{0%,100%{stroke-opacity:.35}40%,64%{stroke-opacity:1}}
@keyframes pa-unicode-cursor{0%,100%{transform:translateX(0)}50%{transform:translateX(116px)}}
@keyframes pa-guess-caret{0%,44%,100%{opacity:1}50%,94%{opacity:.2}}
@keyframes pa-latex-cursor{0%,28%{transform:translateY(0)}33%,61%{transform:translateY(23px)}66%,94%{transform:translateY(46px)}100%{transform:translateY(0)}}
@keyframes pa-cognition-merge{0%,5%{transform:translate(0,0);opacity:0}10%{opacity:1}30%{transform:translate(15px,0);opacity:1}75%{transform:translate(38px,28px);opacity:1}90%{transform:translate(49px,28px);opacity:1}100%{transform:translate(49px,28px);opacity:0}}
@keyframes pa-repo-cursor{0%,45%{transform:translateY(0)}50%,95%{transform:translateY(26px)}100%{transform:translateY(0)}}
@media(prefers-reduced-motion:reduce){.project-art *{animation:none!important;transition:none!important}}
"""


def _text(x, y, value, color, size=18, *, mono=False, weight=None, anchor=None):
    attrs = f'x="{x}" y="{y}" fill="{color}" font-size="{size}"'
    if mono:
        attrs += ' class="mono"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    return f'<text {attrs}>{escape(value)}</text>'


def _package(p):
    # A package and three evidence entries. No checkmark or verdict is implied.
    content = f'''<g fill="none" stroke="{p['ice']}" stroke-width="1.5" stroke-linejoin="round">
      <path d="M10 47 42 33 74 47v48l-32 14-32-14Z"/>
      <path d="m10 47 32 14 32-14M42 61v48M26 40l32 14v16"/>
    </g>
    <path d="M1 72h82" class="pa-package-scan" stroke="{p['copper']}" stroke-width="2"/>
    <path d="M84 72h20m-6-5 6 5-6 5" fill="none" stroke="{p['muted']}" stroke-width="1.5"/>
    <g fill="{p['canvas']}" stroke="{p['line']}">
      <rect x="118" y="12" width="174" height="30" rx="5"/>
      <rect x="118" y="51" width="174" height="30" rx="5"/>
      <rect x="118" y="90" width="174" height="30" rx="5"/>
    </g>
    <g fill="none" stroke="{p['muted']}" stroke-width="1.5" stroke-linecap="round">
      <path d="m131 22-5 5 5 5m8-10 5 5-5 5"/>
      <path d="M128 58h12l4 4v12h-16Zm12 0v5h4"/>
      <path d="M127 99h18m-18 6h18m-18 6h11"/>
    </g>'''
    content += _text(157, 34, "脚本", p['ink'])
    content += _text(157, 73, "文件", p['ink'])
    content += _text(157, 112, "证据", p['ink'])
    return content


def _harness(p):
    # The return path ends at the Harness control point, before installation.
    content = _text(150, 24, "Harness", p['muted'], 18, mono=True, anchor="middle")
    content += f'''<rect x="8" y="48" width="132" height="40" rx="6" fill="{p['canvas']}" stroke="{p['line']}"/>
    <rect x="190" y="48" width="103" height="40" rx="6" fill="{p['canvas']}" stroke="{p['line']}"/>
    <path d="M140 68h14m14 0h16m-5-5 5 5-5 5" fill="none" stroke="{p['muted']}" stroke-width="1.5"/>
    <circle cx="161" cy="68" r="7" fill="{p['surface']}" stroke="{p['ice']}" stroke-width="1.5"/>
    <path d="M242 88v27h-81V81m-5 5 5-5 5 5" fill="none" stroke="{p['line']}" stroke-width="1.5" stroke-linejoin="round"/>
    <circle class="pa-harness-return" cx="242" cy="91" r="3" fill="{p['copper']}"/>
    '''
    content += _text(17, 74, "npm install", p['ink'], 18, mono=True)
    content += _text(241, 75, "扫描", p['ink'], 18, anchor="middle")
    content += _text(20, 116, "安装前", p['muted'])
    return content


def _diff(p):
    # Two tarballs feed one comparison receipt, including its torn paper edge.
    teeth = " ".join(f'L{x} {119 if i % 2 else 125}'
                     for i, x in enumerate(range(238, 53, -8), 1))
    content = f'''<g fill="{p['canvas']}" stroke="{p['line']}">
      <rect x="8" y="5" width="94" height="29" rx="5"/>
      <rect x="198" y="5" width="94" height="29" rx="5"/>
    </g>
    <path d="M102 20h20v14m-4-4 4 4 4-4m72-10h-20v14m-4-4 4 4 4-4" fill="none" stroke="{p['line']}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M54 38h192v87 {teeth} Z" fill="{p['canvas']}" stroke="{p['line']}" stroke-width="1.5" stroke-linejoin="round"/>
    <g class="pa-diff-cursor">
      <rect x="60" y="44" width="180" height="20" rx="2" fill="{p['ice']}" opacity=".08"/>
      <path d="M60 44h-5v20h5m180-20h5v20h-5" fill="none" stroke="{p['ice']}" stroke-width="1.3"/>
    </g>
    <path d="M96 54h126" stroke="{p['muted']}" stroke-width="1.8" stroke-linecap="round"/>
    <path d="M96 80h98m9 0h19" stroke="{p['copper']}" stroke-width="1.8" stroke-linecap="round"/>
    <path d="M96 106h126" stroke="{p['ice']}" stroke-width="1.8" stroke-linecap="round"/>
    '''
    content += _text(20, 27, "A.tgz", p['muted'], 18, mono=True)
    content += _text(210, 27, "B.tgz", p['ink'], 18, mono=True)
    content += _text(70, 60, "=", p['muted'], 18, mono=True)
    content += _text(70, 86, "−", p['copper'], 18, mono=True)
    content += _text(70, 112, "+", p['ice'], 18, mono=True)
    return content


def _port(p):
    content = f'''<path d="M112 62h27l29-33h34m-63 33 29 37h34" fill="none" stroke="{p['line']}" stroke-width="1.8" stroke-linejoin="round"/>
    <circle cx="139" cy="62" r="3" fill="{p['muted']}"/>
    <circle cx="202" cy="29" r="5" fill="{p['surface']}" stroke="{p['muted']}" stroke-width="1.5"/>
    <circle cx="202" cy="99" r="5" fill="{p['surface']}" stroke="{p['muted']}" stroke-width="1.5"/>
    <circle class="pa-port-probe" cx="112" cy="62" r="3" fill="{p['copper']}"/>
    '''
    content += _text(7, 68, "localhost", p['ink'], 18, mono=True)
    content += _text(218, 35, "IPv4", p['ice'], 18, mono=True)
    content += _text(218, 105, "IPv6", p['ice'], 18, mono=True)
    return content


def _notes(p):
    # A page, its outline, and a reading cursor rather than a repository diagram.
    return f'''<path d="M42 8h147l25 25v91H42Z" fill="{p['canvas']}" stroke="{p['line']}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M189 8v25h25" fill="none" stroke="{p['line']}" stroke-width="1.5"/>
    <path d="M60 31h94" stroke="{p['ink']}" stroke-width="3" stroke-linecap="round"/>
    <path d="M60 53h132m-132 9h105m-105 17h132m-132 9h114m-114 17h132m-132 9h92" fill="none" stroke="{p['muted']}" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M236 33v72m0-72h8m-8 26h8m-8 26h8m-8 20h8M250 33h36m-36 26h29m-29 26h36m-36 20h23" fill="none" stroke="{p['line']}" stroke-width="1.5" stroke-linecap="round"/>
    <path class="pa-notes-cursor" d="M35 45h-7v20h7" fill="none" stroke="{p['copper']}" stroke-width="2"/>
    '''


def _bits(p):
    content = f'''<rect x="5" y="5" width="290" height="34" rx="6" fill="{p['canvas']}" stroke="{p['line']}"/>
    <path d="M92 65h25m-6-5 6 5-6 5" fill="none" stroke="{p['muted']}" stroke-width="1.5"/>
    <rect class="pa-bits-emphasis" x="127" y="46" width="118" height="36" rx="5" fill="none" stroke="{p['copper']}" stroke-width="1.5"/>
    '''
    content += _text(19, 29, "ADD AX, 1", p['ink'], 20, mono=True)
    content += _text(245, 29, "示例", p['muted'], 18)
    content += _text(14, 73, "7FFF", p['muted'], 22, mono=True)
    content += _text(140, 73, "8000", p['ice'], 28, mono=True, weight=600)
    content += _text(14, 117, "OF 1", p['ink'], 18, mono=True)
    content += _text(82, 117, "CF 0", p['muted'], 18, mono=True)
    for bit in range(16):
        x = 143 + bit * 9
        content += f'<rect x="{x}" y="99" width="6" height="13" rx="1" fill="{p["ice"] if bit == 0 else p["canvas"]}" stroke="{p["ice"] if bit == 0 else p["line"]}"/>'
    return content


def _unicode(p):
    content = f'''<rect x="49" y="26" width="122" height="38" rx="5" fill="{p['canvas']}" stroke="{p['ice']}" stroke-width="1.2"/>
    <path class="pa-unicode-cursor" d="M52 22v46" stroke="{p['copper']}" stroke-width="2"/>
    <path d="M110 70v17h30m-5-5 5 5-5 5" fill="none" stroke="{p['line']}" stroke-width="1.5"/>
    '''
    content += _text(8, 52, "na", p['ink'], 22, mono=True)
    content += _text(58, 51, "[ZWSP]", p['ice'], 18, mono=True)
    content += _text(183, 52, "me", p['ink'], 22, mono=True)
    content += _text(12, 118, "零宽空格", p['muted'], 18)
    content += _text(154, 118, "U+200B", p['copper'], 20, mono=True)
    return content


def _guess(p):
    # Text clues lead to a guess input. The heart labels a mechanic, not a count.
    content = f'''<path d="M13 12h120a8 8 0 0 1 8 8v62a8 8 0 0 1-8 8h-28l-18 17 4-17H13a8 8 0 0 1-8-8V20a8 8 0 0 1 8-8Z" fill="{p['canvas']}" stroke="{p['line']}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M20 52h102m-102 14h82m-82 13h62" fill="none" stroke="{p['muted']}" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M148 55h15m-5-5 5 5-5 5" fill="none" stroke="{p['line']}" stroke-width="1.5"/>
    <rect x="170" y="31" width="123" height="46" rx="6" fill="{p['canvas']}" stroke="{p['ice']}" stroke-width="1.3"/>
    <path class="pa-guess-caret" d="M237 42v24" stroke="{p['copper']}" stroke-width="2"/>
    <path d="M186 99c-4-8-16-6-16 3 0 7 16 17 16 17s16-10 16-17c0-9-12-11-16-3Z" fill="none" stroke="{p['muted']}" stroke-width="1.5" stroke-linejoin="round"/>
    '''
    content += _text(20, 36, "AI 线索", p['ink'], 18)
    content += _text(182, 60, "猜词", p['ink'], 18)
    content += _text(215, 115, "生命", p['muted'], 18)
    return content


def _latex(p):
    # Code and typeset pages are examples, without a compilation-result badge.
    content = f'''<rect x="8" y="9" width="108" height="114" rx="6" fill="{p['canvas']}" stroke="{p['line']}" stroke-width="1.5"/>
    <path d="M186 9h82l24 24v90H186Z" fill="{p['canvas']}" stroke="{p['line']}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M268 9v24h24" fill="none" stroke="{p['line']}" stroke-width="1.5"/>
    <path d="M125 66h49m-6-5 6 5-6 5" fill="none" stroke="{p['muted']}" stroke-width="1.5"/>
    <path d="M23 49h76m-76 46h63m-63 12h49" fill="none" stroke="{p['muted']}" stroke-width="1.5" stroke-linecap="round"/>
    <path class="pa-latex-cursor" d="M16 42v15" stroke="{p['copper']}" stroke-width="2"/>
    <path d="M202 49h57" stroke="{p['ink']}" stroke-width="2.5" stroke-linecap="round"/>
    <path d="M202 86h74m-74 12h74m-74 12h54" fill="none" stroke="{p['muted']}" stroke-width="1.4" stroke-linecap="round"/>
    '''
    content += _text(22, 34, "TeX", p['ice'], 18, mono=True)
    content += _text(22, 80, "\\alpha", p['muted'], 18, mono=True)
    content += _text(202, 34, "PDF", p['ink'], 18, mono=True)
    content += _text(203, 73, "α + β", p['ink'], 18)
    return content


def _cognition(p):
    # README flow: events -> WorkUnit -> evidence-backed Insight. No alert level.
    content = f'''<path d="M29 45h15l23 28h7m-45 0h45m-45 28h15l23-28m2-5 5 5-5 5" fill="none" stroke="{p['line']}" stroke-width="1.5" stroke-linejoin="round"/>
    <g fill="{p['surface']}" stroke="{p['muted']}" stroke-width="1.5">
      <circle cx="23" cy="45" r="5"/><circle cx="23" cy="73" r="5"/><circle cx="23" cy="101" r="5"/>
    </g>
    <circle class="pa-cognition-merge" cx="29" cy="45" r="3" fill="{p['copper']}"/>
    <rect x="80" y="35" width="96" height="77" rx="6" fill="{p['canvas']}" stroke="{p['line']}" stroke-width="1.5"/>
    <path d="M95 81h65m-65 14h50" fill="none" stroke="{p['muted']}" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M182 73h18m-5-5 5 5-5 5" fill="none" stroke="{p['line']}" stroke-width="1.5"/>
    <rect x="206" y="35" width="87" height="77" rx="6" fill="{p['canvas']}" stroke="{p['ice']}" stroke-width="1.3"/>
    <path d="M217 67h65m-64 34h47" fill="none" stroke="{p['line']}" stroke-width="1.5" stroke-linecap="round"/>
    '''
    content += _text(6, 24, "事件", p['muted'], 18)
    content += _text(92, 64, "工作单元", p['ink'], 18)
    content += _text(231, 59, "洞察", p['ink'], 18)
    content += _text(231, 91, "证据", p['muted'], 18)
    return content


def _repo(p):
    content = f'''<path d="M10 17h35l10 10h56v39H10Z" fill="{p['canvas']}" stroke="{p['line']}" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M56 66v49m0-28h34m-34 28h34" fill="none" stroke="{p['line']}" stroke-width="1.5"/>
    <g fill="{p['canvas']}" stroke="{p['line']}">
      <rect x="96" y="76" width="189" height="23" rx="4"/>
      <rect x="96" y="102" width="189" height="23" rx="4"/>
    </g>
    <rect class="pa-repo-cursor" x="100" y="80" width="4" height="15" rx="1" fill="{p['copper']}"/>
    <path d="M118 87h71m-71 26h97" stroke="{p['muted']}" stroke-width="1.5" stroke-linecap="round"/>
    '''
    return content + _text(26, 53, "repo", p['ice'], 20, mono=True)


_RENDERERS = {
    "package": _package, "harness": _harness, "diff": _diff, "port": _port,
    "notes": _notes, "bits": _bits, "unicode": _unicode, "guess": _guess, "repo": _repo,
    "latex": _latex, "cognition": _cognition,
}
_LABELS = {
    "package": "npm 包静态扫描与脚本、文件、证据条目",
    "harness": "Harness 在 npm install 之前交给扫描器检查，再返回安装控制点",
    "diff": "两个归档的文件清单及增加、删除行的对照",
    "port": "localhost 的 IPv4 与 IPv6 分支示意，不表示网络探测结果",
    "notes": "文章页面、目录和阅读位置",
    "bits": "16 位算例：7FFFh 加 1 得到 8000h，OF 为 1，CF 为 0；非实时执行状态",
    "unicode": "文本中的零宽空格显影为 ZWSP 和 U+200B",
    "guess": "生存竞速：AI 文字线索、猜词输入与生命机制示意，不表示实际题目、生命值或分数",
    "latex": "VisualLaTeX：TeX 代码页与 PDF 排版页示意，不表示实际编译结果",
    "cognition": "Coding Agent 事件归并为工作单元，再连接带证据条目的洞察示意；不表示告警级别或测试通过",
    "repo": "仓库文件目录",
}


def render_art(kind, palette, mobile=False):
    """Return a fragment for a 300 × 132 viewBox; never fetch or execute code."""
    # The same coordinates keep diagrams proportional in either parent layout.
    del mobile
    kind = kind if kind in _RENDERERS else "repo"
    p = {key: escape(str(palette[key]), quote=True)
         for key in ("canvas", "surface", "line", "ink", "muted", "ice", "copper")}
    return (f'<g class="project-art pa-{kind}" data-art="{kind}">'
            f'<title>{escape(_LABELS[kind])}</title>{_RENDERERS[kind](p)}</g>')
