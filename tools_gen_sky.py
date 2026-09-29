#!/usr/bin/env python3
"""
ポートフォリオのヒーロー背景（夕暮れの田舎・セルルック）を
インラインSVGとして生成し、index.html に差し込む。

方針
- ぼかしは一切使わない（セルルックの条件）
- 主役は太陽。山で埋めない。太陽の位置だけ稜線を凹ませる
- 雲は「丸の集まり」を一回り大きい黒で裏打ちして、一本の輪郭にする
- 画面中央（タイトルが載る帯）には雲を置かない
"""
import math, pathlib, random, re

W, H = 1600, 900
HORIZON = 620
INK = "#141227"
SUN_X, SUN_Y, SUN_R = 1168, 516, 146

random.seed(11)

# ───────── 空の帯（段階を持つ塗り） ─────────
BANDS = [
    (0.000, "#0D1234"), (0.080, "#161940"), (0.150, "#26214F"),
    (0.225, "#3D2760"), (0.300, "#5E2E६B".replace("६", "6")), (0.375, "#8A3369"),
    (0.445, "#B44061"), (0.510, "#D75B52"), (0.570, "#EC7A3D"),
    (0.625, "#F89F36"), (0.668, "#FFC152"), (0.692, "#FFDD86"),
]

def sky_gradient():
    out = ['<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">']
    for i, (off, col) in enumerate(BANDS):
        if i:
            out.append(f'<stop offset="{off:.4f}" stop-color="{BANDS[i-1][1]}"/>')
        out.append(f'<stop offset="{off:.4f}" stop-color="{col}"/>')
    out.append(f'<stop offset="1" stop-color="{BANDS[-1][1]}"/>')
    out.append('</linearGradient>')
    return "".join(out)

# ───────── 光条 ─────────
def rays():
    parts = []
    n = 22
    for i in range(n):
        a0 = (360 / n) * i + 4
        a1 = a0 + (360 / n) * 0.26
        L = 1900
        x0 = SUN_X + math.cos(math.radians(a0)) * L
        y0 = SUN_Y + math.sin(math.radians(a0)) * L
        x1 = SUN_X + math.cos(math.radians(a1)) * L
        y1 = SUN_Y + math.sin(math.radians(a1)) * L
        parts.append(f'<path d="M{SUN_X} {SUN_Y}L{x0:.0f} {y0:.0f}L{x1:.0f} {y1:.0f}Z"/>')
    return (f'<g class="rays" fill="#FFE9AE" opacity=".17" mask="url(#rayfade)" '
            f'style="transform-origin:{SUN_X}px {SUN_Y}px">' + "".join(parts) + "</g>")

# ───────── 雲 ─────────
def cloud(cx, cy, scale, lit, shade, seed):
    """丸の集まりを、一回り大きい黒で裏打ちして輪郭にする。内部に線が出ない。"""
    rnd = random.Random(seed)
    blobs, x = [], 0.0
    n = rnd.randint(4, 6)
    for i in range(n):
        mid = 1.0 - abs(i - (n - 1) / 2) / ((n - 1) / 2 + 0.6)   # 中央ほど大きく
        r = rnd.uniform(24, 34) * (0.62 + mid * 0.85)
        blobs.append((x, rnd.uniform(-6, 6), r))
        x += r * rnd.uniform(0.82, 1.02)
    span = blobs[-1][0]
    blobs = [(bx - span / 2, by, br) for bx, by, br in blobs]
    body = "".join(f'<ellipse cx="{bx:.1f}" cy="{by:.1f}" rx="{br:.1f}" ry="{br*0.78:.1f}"/>'
                   for bx, by, br in blobs)
    cid = f"cs{seed}"
    return f"""
<g class="cloud" transform="translate({cx},{cy}) scale({scale})">
  <clipPath id="{cid}"><rect x="-460" y="4" width="920" height="300"/></clipPath>
  <g fill="{INK}" transform="scale(1.058)">{body}</g>
  <g fill="{lit}">{body}</g>
  <g fill="{shade}" clip-path="url(#{cid})">{body}</g>
</g>"""

# ───────── 稜線 ─────────
def ridge(seed, base, amp, fill, rim=None, rim_w=6):
    """
    太陽の真下だけ振幅を落として谷にする。主役を山で隠さないため。
    縁の光は「上端の折れ線」だけに引く（閉path全体に引くと横や下にも線が出る）。
    """
    rnd = random.Random(seed)
    pts, x = [], -120
    while x < W + 160:
        d = abs(x - SUN_X) / 560.0
        dip = min(1.0, max(0.12, d))            # 太陽付近で 0.12 倍まで下がる
        pts.append((x, base - abs(rnd.gauss(0, 1)) * amp * dip))
        x += rnd.uniform(160, 300)
    top = [f"M{pts[0][0]:.0f} {pts[0][1]:.0f}"]
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        mx = (x0 + x1) / 2
        top.append(f"Q{x0+(mx-x0)*0.62:.0f} {y0:.0f} {mx:.0f} {(y0+y1)/2:.0f}")
        top.append(f"Q{x1-(x1-mx)*0.62:.0f} {y1:.0f} {x1:.0f} {y1:.0f}")
    topd = " ".join(top)
    filled = f'{topd} L{W+160} {H} L-120 {H} Z'
    out = f'<path d="{filled}" fill="{fill}"/>'
    if rim:
        out += f'<path d="{topd}" fill="none" stroke="{rim}" stroke-width="{rim_w}" stroke-linecap="round" opacity=".85"/>'
    return out

# ───────── 水田と映り込み ─────────
def water():
    rows, y, i = [], HORIZON + 8, 0
    while y < H:
        h = 2.5 + i * 0.5
        rows.append(f'<rect x="0" y="{y:.1f}" width="{W}" height="{h:.1f}" '
                    f'fill="#2B3568" opacity="{max(0.10, 0.42 - i*0.028):.2f}"/>')
        y += h + 5 + i * 0.9
        i += 1

    glint, rnd, y, k = [], random.Random(3), HORIZON + 2, 0
    while y < H - 30:
        t = (y - HORIZON) / (H - HORIZON)
        w = SUN_R * 1.9 * (1 - t * 0.78) * rnd.uniform(0.62, 1.0)
        h = rnd.uniform(5, 13)
        col = ("#FFD86E", "#FBAF44", "#F08C2C")[k % 3]
        glint.append(f'<rect x="{SUN_X-w/2:.0f}" y="{y:.1f}" width="{max(8,w):.0f}" height="{h:.1f}" '
                     f'rx="{h/2:.1f}" fill="{col}" opacity="{max(0.55, 1.0-t*0.42):.2f}"/>')
        y += h + rnd.uniform(7, 17)
        k += 1
    return (f'<rect x="0" y="{HORIZON}" width="{W}" height="{H-HORIZON}" fill="#121738"/>'
            + "".join(rows) + f'<g class="glint">{"".join(glint)}</g>')

# ───────── 電柱と電線 ─────────
def poles():
    xs, base = [140, 470, 830, 1235, 1560], [772, 742, 718, 700, 690]
    hs = [250, 224, 202, 184, 176]
    g = []
    for x, b, h in zip(xs, base, hs):
        t = b - h
        g.append(f'<rect x="{x-6}" y="{t}" width="12" height="{h}" fill="{INK}"/>')
        g.append(f'<rect x="{x-36}" y="{t+18}" width="72" height="8" fill="{INK}"/>')
        g.append(f'<rect x="{x-26}" y="{t+44}" width="52" height="7" fill="{INK}"/>')
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        y0 = base[i] - hs[i] + 22
        y1 = base[i + 1] - hs[i + 1] + 22
        for dy in (0, 26):
            sag = (x1 - x0) * 0.17
            g.append(f'<path d="M{x0} {y0+dy}Q{(x0+x1)/2:.0f} {max(y0,y1)+sag+dy:.0f} {x1} {y1+dy}" '
                     f'fill="none" stroke="{INK}" stroke-width="3.2"/>')
    return "".join(g)

# ───────── 鳥 ─────────
def birds():
    g = []
    for (x, y, s) in [(286, 168, 1.0), (348, 198, .78), (398, 152, .6), (1372, 232, .72)]:
        g.append(f'<path transform="translate({x},{y}) scale({s})" '
                 f'd="M-19 0q9.5 -12 19 0q9.5 -12 19 0" fill="none" '
                 f'stroke="{INK}" stroke-width="3.6" stroke-linecap="round"/>')
    return f'<g class="birds">{"".join(g)}</g>'

# ───────── 手前の草 ─────────
def grass():
    rnd = random.Random(9)
    d, x = [f"M-20 {H+20}", f"L-20 {H-34}"], -20
    while x < W + 40:
        w = rnd.uniform(15, 34)
        h = rnd.uniform(16, 52)
        d.append(f"Q{x+w/2:.0f} {H-34-h:.0f} {x+w:.0f} {H-32:.0f}")
        x += w
    d.append(f"L{W+40} {H+20}Z")
    return f'<path d="{" ".join(d)}" fill="#070A1A"/>'

# ───────── 組み立て ─────────
# 中央（x 460〜1180 / y 230〜470）はタイトルが載るので雲を置かない
far = "".join([
    cloud(200, 150, 0.92, "#EFC0AC", "#BE7580", 1),
    cloud(700, 108, 0.74, "#E8B6A8", "#B06E7C", 2),
    cloud(1330, 176, 0.86, "#F2C6A8", "#C07A73", 3),
])
near = "".join([
    cloud(170, 330, 1.18, "#FFD5A0", "#CE7658", 4),
    cloud(1420, 300, 1.05, "#FFCD96", "#C76E52", 5),
    cloud(760, 402, 0.8, "#FFDCAC", "#D28160", 6),
])

svg = f"""<svg class="scene" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
<defs>
  {sky_gradient()}
  <radialGradient id="sunfill" cx="42%" cy="36%">
    <stop offset="0" stop-color="#FFFBE6"/><stop offset="0.20" stop-color="#FFFBE6"/>
    <stop offset="0.20" stop-color="#FFEFB2"/><stop offset="0.42" stop-color="#FFEFB2"/>
    <stop offset="0.42" stop-color="#FFD468"/><stop offset="0.68" stop-color="#FFD468"/>
    <stop offset="0.68" stop-color="#FBAB3E"/><stop offset="0.88" stop-color="#FBAB3E"/>
    <stop offset="0.88" stop-color="#F08C2C"/><stop offset="1" stop-color="#F08C2C"/>
  </radialGradient>
  <radialGradient id="rf">
    <stop offset="0" stop-color="#000"/><stop offset="0.09" stop-color="#000"/>
    <stop offset="0.17" stop-color="#fff"/><stop offset="0.58" stop-color="#000"/>
  </radialGradient>
  <mask id="rayfade">
    <rect x="{SUN_X-1600}" y="{SUN_Y-1600}" width="3200" height="3200" fill="url(#rf)"/>
  </mask>
  <pattern id="halftone" width="9" height="9" patternUnits="userSpaceOnUse">
    <circle cx="4.5" cy="4.5" r="1.6" fill="{INK}"/>
  </pattern>
  <linearGradient id="htfade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0.34" stop-color="#000"/><stop offset="0.66" stop-color="#fff"/>
    <stop offset="0.688" stop-color="#fff"/><stop offset="0.688" stop-color="#000"/>
  </linearGradient>
  <mask id="htmask"><rect width="{W}" height="{H}" fill="url(#htfade)"/></mask>
</defs>

<rect width="{W}" height="{HORIZON}" fill="url(#sky)"/>
{rays()}

<g class="cl-far">{far}<g transform="translate({W},0)">{far}</g></g>
{birds()}

<circle cx="{SUN_X}" cy="{SUN_Y}" r="{SUN_R+58}" fill="none" stroke="#FFC768" stroke-width="3" opacity=".14"/>
<circle cx="{SUN_X}" cy="{SUN_Y}" r="{SUN_R+28}" fill="none" stroke="#FFD880" stroke-width="4" opacity=".26"/>
<circle id="sun" cx="{SUN_X}" cy="{SUN_Y}" r="{SUN_R}" fill="url(#sunfill)"
        stroke="{INK}" stroke-width="4.5" tabindex="0" role="button" aria-label="夕日"/>

<g class="cl-near">{near}<g transform="translate({W},0)">{near}</g></g>

{ridge(11, 604, 104, "#6B4A7E", "#FFC178", 4)}
{ridge(23, 620, 62, "#42305D", "#F09455", 3.5)}
{ridge(31, 636, 32, "#221E3D", "#D86B3E", 3)}

{water()}
{poles()}
{grass()}

<rect width="{W}" height="{H}" fill="url(#halftone)" mask="url(#htmask)" opacity=".13"/>
</svg>"""

# ───────── index.html を書き換える ─────────
p = pathlib.Path.home() / "kopo-k.github.io" / "index.html"
src = p.read_text(encoding="utf-8")

new_css = """.sky{position:absolute; inset:0; overflow:hidden; background:#0D1234;}
.scene{position:absolute; inset:0; width:100%; height:100%; display:block;}
#sun{cursor:pointer; transform-box:fill-box; transform-origin:center; transition:transform .18s;}
#sun:hover{transform:scale(1.035);}
#sun:focus-visible{outline:4px solid #77D6B5; outline-offset:6px;}
.rays{animation:spin 160s linear infinite;}
.cl-far{animation:drift 165s linear infinite;}
.cl-near{animation:drift 95s linear infinite;}
.birds{animation:fly 52s linear infinite;}
.glint{animation:glint 5.5s ease-in-out infinite alternate;}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes drift{from{transform:translateX(0)}to{transform:translateX(-1600px)}}
@keyframes fly{from{transform:translateX(160px)}to{transform:translateX(-1800px)}}
@keyframes glint{from{opacity:.6}to{opacity:1}}
@media (prefers-reduced-motion:reduce){ .rays,.cl-far,.cl-near,.birds,.glint{animation:none;} }
@media (max-width:480px){
  .hud{padding:0 12px; gap:8px;}
  .who{font-size:14px;}
  .who small{font-size:8.5px;}
  .stagenum{font-size:10.5px;}
  .stagenum b{font-size:13px;}
}
"""

if ".scene{" in src:                       # 2回目以降の実行
    start = src.index(".sky{")
    end = src.index(".titlewrap{")
    src = src[:start] + new_css + src[end:]
    m = re.search(r'<div class="sky">.*?</div>\s*\n\s*<div class="titlewrap">', src, re.S)
else:                                      # 初回
    start = src.index(".sky{")
    end = src.index(".titlewrap{")
    src = src[:start] + new_css + src[end:]
    m = re.search(r'<div class="sky">.*?</div>\s*\n\s*<div class="titlewrap">', src, re.S)

assert m, "skyブロックが見つからない"
src = src[:m.start()] + f'<div class="sky">{svg}</div>\n  <div class="titlewrap">' + src[m.end():]

# タイトルは太陽と重ならないよう少し左へ
if "margin-right:clamp" not in src:
    src = src.replace(
        '.titlewrap{position:relative; z-index:2; text-align:center; padding:40px 0 90px;}',
        '.titlewrap{position:relative; z-index:2; text-align:center; padding:40px 0 90px;\n'
        '  margin-right:clamp(0px,14vw,260px);}\n'
        '@media (max-width:860px){ .titlewrap{margin-right:0;} }'
    )

src = src.replace(
    ".romaji{\n  font-family:var(--mono); font-size:13px; letter-spacing:.3em;\n"
    "  color:var(--paper); margin:20px 0 0; text-shadow:2px 2px 0 var(--ink);\n}",
    ".romaji{\n  font-family:var(--mono); font-size:13px; letter-spacing:.3em; font-weight:700;\n"
    "  color:var(--paper); margin:20px 0 0;\n"
    "  text-shadow:2px 2px 0 var(--ink),-1px -1px 0 var(--ink),1px -1px 0 var(--ink),-1px 1px 0 var(--ink);\n}")

# 暗い山に埋もれる注意書きの視認性
src = re.sub(r'\.upwarn\{[^}]*\}',
  '.upwarn{font-family:var(--mono); font-size:12.5px; color:#FFE3AE; font-weight:700;\n'
  '  text-shadow:2px 2px 0 #151327,-1px -1px 0 #151327,1px -1px 0 #151327,-1px 1px 0 #151327;}',
  src)

# 縦長の画面でも太陽が画面内に入るよう、SVGの寄せ方を切り替える
fit = """
  // 縦長の画面では、主役の夕日を中心に据えたトリミングに切り替える。
  // 寄せ方の指定だけでは太陽が画面端で切れてしまうため、viewBox 自体を計算し直す。
  function fitScene(){
    var sc = document.querySelector('.scene');
    if (!sc) return;
    var w = window.innerWidth, h = Math.max(1, window.innerHeight - 60);
    if (w / h >= 1.15){ sc.setAttribute('viewBox', '0 0 1600 900'); return; }
    var vw = 900 * (w / h);                 // 縦を基準に、画面比に合う幅を取る
    var x0 = 1168 - vw * 0.54;              // 太陽が横 54% に来る位置
    x0 = Math.max(0, Math.min(1600 - vw, x0));
    sc.setAttribute('viewBox', x0.toFixed(1) + ' 0 ' + vw.toFixed(1) + ' 900');
  }
  fitScene();
  window.addEventListener('resize', fitScene);
"""
if "fitScene" not in src:
    src = src.replace("  var secs = Array.prototype.slice.call(document.querySelectorAll('section'));",
                      fit.rstrip() + "\n\n  var secs = Array.prototype.slice.call(document.querySelectorAll('section'));")

p.write_text(src, encoding="utf-8")
print("index.html を更新しました")
print("SVG:", len(svg), "文字 / HTML合計:", round(len(src.encode()) / 1024, 1), "KB")
