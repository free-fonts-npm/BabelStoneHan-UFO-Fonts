#!/usr/bin/env python3
"""Build BSH_IVS.html: the upstream IVS chart, rendered with this package.

Takes upstream BSH_IVS.html from the same release tag build.py uses, swaps the
site stylesheet for this package's CSS on jsDelivr (pinned to the version in
package.json), and appends a section listing every other variation sequence
the fonts support (VS1-VS3: CJK compatibility ideographs, other Unicode
standardized variants, and BabelStone's own), so the page covers every
sequence in the fonts' cmap format-14 tables.

Usage:
    python3 build.py              # first, so src/*.ttf exist
    python3 build_ivs_page.py     # download inputs to src/ + write BSH_IVS.html
    python3 build_ivs_page.py --no-dl
"""

import argparse
import hashlib
import html
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

from build import RELEASE_BASE, SOURCES, SRC_DIR

ROOT = Path(__file__).parent
OUT_PATH = ROOT / "BSH_IVS.html"
UPSTREAM_HTML = SRC_DIR / "BSH_IVS.html"
UPSTREAM_TXT = SRC_DIR / "BSH_IVS.TXT"
IVD_VERSION = "2026-08-03"
IVD_TXT = SRC_DIR / f"IVD_Sequences-{IVD_VERSION}.txt"
IVD_URL = f"https://www.unicode.org/ivd/data/{IVD_VERSION}/IVD_Sequences.txt"

# Sequences BabelStone assigned before they were registered in the IVD. A new
# registration can carry a different glyph (a collision, not a match), so a
# star is added only after comparing the BabelStone glyph with the registered
# one by eye; each entry records the registration that was checked.
IVD_REVIEWED = {
    (0x20509, 0xE0103): "Moji_Joho:MJ057273",  # ⿻丷夫, matches
    (0x23AA3, 0xE0100): "Moji_Joho:MJ038918",  # ⿰⿱彐𧰨殳, matches
    (0x23AA3, 0xE0101): "Moji_Joho:MJ057925",  # ⿰彖殳, matches
}
SV_TXT = SRC_DIR / "StandardizedVariants.txt"
SV_URL = "https://www.unicode.org/Public/UCD/latest/ucd/StandardizedVariants.txt"

FONTS = [s for s in SOURCES if s["keep_layout"]]  # Basic, Extra (the ones with IVS)
TAG = FONTS[0]["tag"]
VERSION = json.loads((ROOT / "package.json").read_text())["version"]
CSS_URL = f"https://cdn.jsdelivr.net/npm/@free-fonts/babelstone-han@{VERSION}/babelstone-han.css"

HEAD = f"""<!--
  Adapted from BSH_IVS.html in the upstream BabelStone Han {TAG} release
  (https://github.com/babelstone/babelstonehan-ufo/releases/tag/{TAG}),
  (c) Andrew West. Changes: the site stylesheet ../BabelStone.css is replaced by
  this package's chunked webfont CSS (from jsDelivr, pinned to {VERSION}, matching
  this chart) plus a minimal inline style; relative links point to
  babelstone.co.uk / the upstream release; IVD markers (*) that the HTML
  table lacks but BSH_IVS.TXT of the same release has are restored (dotted
  underline); sequences registered in a later IVD ({IVD_VERSION}) whose glyph was
  checked against the registered one are starred too (double underline);
  the "Standardized Variation Sequences" section at the end is
  generated from the fonts by build_ivs_page.py. The upstream table content is
  otherwise unchanged.
-->
<link rel="stylesheet" type="text/css" href="{CSS_URL}" />
<style type="text/css">
:root {{ color-scheme: light dark; }}
body {{ margin: 1.5em auto; max-width: 72em; padding: 0 16px;
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'BabelStone Han Basic', 'BabelStone Han Extra', 'BabelStone Han PUA', sans-serif;
  line-height: 1.5; }}
.bs_han {{ font-family: 'BabelStone Han Basic', 'BabelStone Han Extra', 'BabelStone Han PUA'; }}
.vbig {{ font-size: 40px; line-height: 1.2; margin: 0.1em 0; }}
.webfont-note {{ border: 1px solid #c90; background: rgba(255, 204, 0, 0.12); padding: 0 1em; }}
table.solid {{ border-collapse: collapse; }}
table.solid th, table.solid td {{ border: 1px solid #999; padding: 0.2em 0.5em; vertical-align: middle; }}
.sm, .sm1, .sm2, .sm3 {{ text-align: center; }}
.sml1, .sml2, .sml3 {{ text-align: left; }}
.sm1, .sml1 {{ background: rgba(128, 128, 128, 0.06); }}
.sm3, .sml3 {{ background: rgba(128, 128, 128, 0.12); }}
.ivd-restored {{ text-decoration: underline dotted; text-underline-offset: 3px; cursor: help; }}
.em-box {{ display: inline-block; line-height: 1; margin: 0.15em 0;
  outline: 1px dashed rgba(128, 128, 128, 0.8); }}
.zh {{ border-left: 3px solid rgba(128, 128, 128, 0.35); padding-left: 0.8em; }}
.toc {{ border: 1px solid rgba(128, 128, 128, 0.5); padding: 0.4em 1.2em; margin: 1em 0; }}
.toc h2 {{ font-size: 1.1em; margin: 0.4em 0; }}
.toc ol {{ margin: 0.2em 0; }}
.ivd-new {{ text-decoration: underline double; text-underline-offset: 3px; cursor: help; }}
</style>"""


def download() -> None:
    SRC_DIR.mkdir(exist_ok=True)
    for url, dest in [(f"{RELEASE_BASE}/{TAG}/BSH_IVS.html", UPSTREAM_HTML),
                      (f"{RELEASE_BASE}/{TAG}/BSH_IVS.TXT", UPSTREAM_TXT),
                      (IVD_URL, IVD_TXT),
                      (SV_URL, SV_TXT)]:
        print(f"Downloading {url} ...")
        urllib.request.urlretrieve(url, dest)


IVS_ROW = re.compile(
    r'<td class="(sm\d)">(VS\d+)(\**)</td>(\s*<td class="sml\d"><span class="bs_han vbig">)([^<]{2})</span>')


def restore_ivd_markers(page: str) -> tuple[str, int]:
    """Take the IVD markers (*) of the upstream table from BSH_IVS.TXT.

    Both files list the same sequences in the same order, but the v18.0.1 HTML
    table leaves 24 IVD-registered sequences unstarred although its own intro
    counts 384 as the TXT does. Only missing stars are added; a star the TXT
    lacks is reported, not removed.
    """
    txt = []
    for line in UPSTREAM_TXT.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        m = re.match(r"U\+\S+ \+ VS\d+\t<(\w+) (\w+)>\t\{.*\}\t(\*?)\s*$", line)
        if not m:
            raise SystemExit(f"unexpected BSH_IVS.TXT line: {line!r}")
        txt.append(((int(m.group(1), 16), int(m.group(2), 16)), m.group(3) == "*"))

    start = page.index('<table id="Variants"')
    end = page.index("</table>", start)
    table = page[start:end]
    rows = [((ord(m.group(5)[0]), ord(m.group(5)[1])), m.group(3) == "*")
            for m in IVS_ROW.finditer(table)]
    if [seq for seq, _ in rows] != [seq for seq, _ in txt]:
        raise SystemExit("BSH_IVS.TXT and BSH_IVS.html list different sequences")
    extra = [f"U+{b:04X} U+{v:04X}" for ((b, v), star), (_, t) in zip(rows, txt) if star and not t]
    if extra:
        raise SystemExit(f"HTML marks {len(extra)} sequences as IVD that BSH_IVS.TXT does not: {extra[:5]}")

    stars = iter(t for _, t in txt)
    restored = 0

    def fix(m: re.Match) -> str:
        nonlocal restored
        if next(stars) and m.group(3) == "":
            restored += 1
            return (f'<td class="{m.group(1)} ivd-restored" title="IVD marker restored from '
                    f'BSH_IVS.TXT">{m.group(2)}*</td>{m.group(4)}{m.group(5)}</span>')
        return m.group(0)

    table = IVS_ROW.sub(fix, table)
    return page[:start] + table + page[end:], restored


def load_ivd() -> dict[tuple[int, int], list[str]]:
    ivd: dict[tuple[int, int], list[str]] = {}
    for line in IVD_TXT.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        seq, collection, ident = (f.strip() for f in line.split(";"))
        base, vs = (int(x, 16) for x in seq.split())
        ivd.setdefault((base, vs), []).append(f"{collection}:{ident}")
    return ivd


def add_new_ivd_markers(page: str) -> tuple[str, int]:
    """Star sequences registered in IVD_VERSION that upstream has not starred yet."""
    ivd = load_ivd()
    start = page.index('<table id="Variants"')
    end = page.index("</table>", start)
    table = page[start:end]
    added = 0
    unreviewed = []

    def fix(m: re.Match) -> str:
        nonlocal added
        seq = (ord(m.group(5)[0]), ord(m.group(5)[1]))
        if m.group(3) or seq not in ivd:
            return m.group(0)
        if IVD_REVIEWED.get(seq) not in ivd[seq]:
            unreviewed.append(f"U+{seq[0]:04X} U+{seq[1]:04X} {ivd[seq]}")
            return m.group(0)
        added += 1
        return (f'<td class="{m.group(1)} ivd-new" title="Registered in IVD {IVD_VERSION} as '
                f'{IVD_REVIEWED[seq]}; glyph checked against the registered one">'
                f'{m.group(2)}*</td>{m.group(4)}{m.group(5)}</span>')

    table = IVS_ROW.sub(fix, table)
    for item in unreviewed:
        print(f"warning: {item} is registered in IVD {IVD_VERSION} but not reviewed; "
              "compare the glyphs and add it to IVD_REVIEWED")
    return page[:start] + table + page[end:], added


def load_standardized_variants() -> tuple[dict, str]:
    text = SV_TXT.read_text(encoding="utf-8")
    sv = {}
    for line in text.splitlines():
        data = line.split("#")[0].strip()
        if not data:
            continue
        seq, desc, context = (f.strip() for f in data.split(";")[:3])
        base, vs = (int(x, 16) for x in seq.split())
        sv[(base, vs)] = (desc, context)
    version = re.search(r"StandardizedVariants-([\d.]+)\.txt", text).group(1)
    return sv, version


class Fonts:
    """Basic + Extra, resolved in CSS stack order like a browser would."""

    def __init__(self) -> None:
        self.fonts = [TTFont(str(SRC_DIR / s["file"])) for s in FONTS]
        self.cmaps = [f.getBestCmap() for f in self.fonts]
        self.glyphsets = [f.getGlyphSet() for f in self.fonts]
        self.uvs: dict[tuple[int, int], tuple[int, str]] = {}  # (base, vs) -> (font idx, glyph)
        for i, font in enumerate(self.fonts):
            for table in font["cmap"].tables:
                if table.format != 14:
                    continue
                for vs, pairs in table.uvsDict.items():
                    for base, glyph in pairs:
                        if (base, vs) in self.uvs:
                            continue  # the earlier family in the stack wins
                        self.uvs[(base, vs)] = (i, glyph or self.cmaps[i][base])

    def default(self, cp: int):
        for i, cmap in enumerate(self.cmaps):
            if cp in cmap:
                return i, cmap[cp]
        return None

    def outline(self, ref) -> str:
        i, glyph = ref
        pen = DecomposingRecordingPen(self.glyphsets[i])
        self.glyphsets[i][glyph].draw(pen)
        return repr(pen.value)

    def advance(self, ref) -> int:
        i, glyph = ref
        return self.fonts[i]["hmtx"][glyph][0]

    def same(self, a, b) -> bool:
        """Same rendering: same outline *and* same advance (e.g. U+2019 VS2 reuses
        the plain outline in a fullwidth cell, so it is not the same glyph)."""
        if a is None or b is None:
            return False
        return a == b or (self.outline(a) == self.outline(b)
                          and self.advance(a) == self.advance(b))


def zh(inner: str) -> str:
    return f'<p class="zh" lang="zh-Hant">{inner}</p>'


BSH_HAN = "https://www.babelstone.co.uk/Fonts/Han.html"
TR37 = "http://www.unicode.org/reports/tr37/"
IVD = "https://unicode.org/ivd/"
IVD_2025 = "https://www.unicode.org/ivd/data/2025-07-14/"

# Traditional Chinese translations of the upstream intro paragraphs, keyed by
# the SHA-1 of each English paragraph (after link rewriting). If upstream
# rewords a paragraph the hash no longer matches and the build stops, so a
# stale translation never sits next to new English text.
UPSTREAM_ZH = {
    "p1": (
        f'<a href="{BSH_HAN}">BabelStone Han</a> 18.0.1 版為下表所列的 1,407 個中日韓統一表意文字，'
        f'支援一套實驗性的 2,893 組<a href="{TR37}">表意文字異體字序列</a>（IVS）。其中 1,343 字有兩個變體，'
        "55 字有三個變體，七字有四個變體，一字有五個變體，一字有九個變體。每個字的第一個變體，"
        "一律與 BabelStone Han 中不加選擇符的該字字形相同。IVS 的純文字清單見 "
        '<a href="{txt}">BSH_IVS.TXT</a>。'
    ),
    "p2": (
        f'這些表意文字異體字序列並未在<a href="{IVD}">表意文字異體字資料庫</a>（IVD）註冊，'
        "在字型日後的版本中可能變動。待此處所列序列穩定後，作者打算日後在 IVD 註冊一個 "
        "BabelStone 集合（BabelStone Collection）。"
    ),
    "p3": (
        "標有星號的 384 個變體選擇符（如「VS17*」）表示對應的異體字序列已在 IVD 註冊，"
        "且作者認為 BabelStone 的字形與該已註冊 IVS 的字形可視為相符。下表所列的其他異體字序列，"
        f'目前應都未在 IVD 註冊（截至 <a target="_blank" href="{IVD_2025}">2025-07-14</a>）。'
        "注意：作者打算把大部分標有星號的 IVS 重新指派，使它們各自擁有唯一的 IVS 序列。"
    ),
    "p4": (
        "原則上，BabelStone Han 依循 G 源（中國）字形；但若 G 源字形不符合中國慣常的字形規範，"
        "或 G 源字形本身前後不一致，有時不依循 G 源字形似乎更為可取。這種情況下，會為 G 源字形"
        "指派一個 IVS，並在來源參照後以雙星號（**）標示。目前共有 49 例，但若中國日後修正這些字"
        "的字形，數量將會減少。注意：中國在 URO 與擴充 A 區的字中，「鬼」的右腳一律不相連，"
        "在擴充 B 區及之後的字中卻一律相連——為求一致，BabelStone Han 所有含「鬼」的字右腳"
        "都不相連，但由於這類字太多，目前並未為另一種寫法提供 IVS。中國對「旡」右腳相連與否的"
        "處理也不一致——為求一致，BabelStone Han 在「旡」位於左右兩側時右腳不相連，其他位置則相連。"
    ),
}
UPSTREAM_EN_SHA1 = {
    "p1": "eeceab14f1957c93df52600854cfc4859e862426",
    "p2": "ce21fd8face62978ece03bb1d369a6cef3c53fd1",
    "p3": "ebb2e0cedb201904881da19d7e3183fd42fa5671",
    "p4": "737ff1707501d99e464d3b225105c465414db608",
}


def add_upstream_translations(page: str) -> str:
    start = page.index('<h2 id="intro">')
    end = page.index('<table id="Variants"', start)
    intro = page[start:end]
    paras = re.findall(r"<p>.*?</p>", intro, re.S)
    if len(paras) != len(UPSTREAM_ZH):
        raise SystemExit(f"upstream intro has {len(paras)} paragraphs, "
                         f"translations cover {len(UPSTREAM_ZH)}; update UPSTREAM_ZH")
    for key, para in zip(UPSTREAM_ZH, paras):
        digest = hashlib.sha1(para.encode("utf-8")).hexdigest()
        if digest != UPSTREAM_EN_SHA1[key]:
            raise SystemExit(f"upstream intro paragraph {key} changed (sha1 {digest}); "
                             "update its translation in UPSTREAM_ZH and UPSTREAM_EN_SHA1")
        text = UPSTREAM_ZH[key].replace("{txt}", f"{RELEASE_BASE}/{TAG}/BSH_IVS.TXT")
        intro = intro.replace(para, para + "\n\n" + zh(text), 1)
    return page[:start] + intro + page[end:]


def toc(n_ivs: int, n_svs: int, counts: dict) -> str:
    items = [
        ("intro", "BabelStone Han Variation Sequences", "說明", None),
        ("Variants", "Ideographic Variation Sequences", "表意文字異體字序列表", n_ivs),
        ("SVS", "Standardized Variation Sequences", "標準化變體序列", n_svs),
    ]
    sub = [
        ("SVS-compat-h", "CJK Compatibility Ideographs", "中日韓相容表意文字", counts["compat"]),
        ("SVS-other", "Other Standardized Variants", "其他標準化變體", counts["other"]),
        ("SVS-babelstone", "BabelStone-specific Sequences", "BabelStone 自訂序列", counts["private"]),
    ]
    li = lambda a, en, zh_, n: (f'<li><a href="#{a}">{en}</a> <span lang="zh-Hant">{zh_}</span>'
                                + (f" ({n:,})" if n is not None else ""))
    out = ['<nav class="toc" aria-label="Contents">', "<h2>Contents 目錄</h2>", "<ol>"]
    out += [li(*items[0]) + "</li>", li(*items[1]) + "</li>", li(*items[2]), "<ol>"]
    out += [li(*x) + "</li>" for x in sub]
    out += ["</ol></li>", "</ol>", "</nav>"]
    return "\n".join(out)


def u(cp: int) -> str:
    return f"U+{cp:04X}"


def glyph_span(text: str, boxed: bool = False) -> str:
    cls = "bs_han vbig em-box" if boxed else "bs_han vbig"
    return f'<span class="{cls}">{html.escape(text)}</span>'


def vs_label(vs: int) -> str:
    return f"VS{vs - 0xFE00 + 1}"


def compat_table(rows: list, fonts: Fonts) -> str:
    groups: dict[int, list] = {}
    for base, vs, compat in rows:
        groups.setdefault(base, []).append((vs, compat))
    out = ['<table id="SVS-compat" class="solid" width="100%">', "<thead>", "<tr>"]
    for label, width in [("Code Point", 12), ("VS", 8), ("Glyph", 12),
                         ("Compatibility Ideograph", 20), ("Note", 48)]:
        out.append(f'\t<th class="sm" width="{width}%">{label}</th>')
    out += ["</tr>", "</thead>", "<tbody>"]
    for base in sorted(groups):
        variants = sorted(groups[base])
        unified = fonts.default(base)
        for n, (vs, compat) in enumerate(variants, 1):
            cls = min(n, 3)
            seq_glyph = fonts.uvs[(base, vs)]
            notes = []
            if fonts.same(seq_glyph, unified):
                notes.append("Same glyph as the unified ideograph.")
            if not fonts.same(seq_glyph, fonts.default(compat)):
                notes.append(f"Differs from the glyph of {u(compat)}.")
            out.append("<tr>")
            if n == 1:
                out += [f'\t<td class="sm" rowspan="{len(variants)}">',
                        f"\t\t<p>{u(base)}</p>",
                        f'\t\t<p class="bs_han vbig">{html.escape(chr(base))}</p>',
                        "\t</td>"]
            out += [f'\t<td class="sm{cls}">{vs_label(vs)}</td>',
                    f'\t<td class="sml{cls}">{glyph_span(chr(base) + chr(vs))}</td>',
                    f'\t<td class="sml{cls}">{u(compat)} {glyph_span(chr(compat))}</td>',
                    f'\t<td class="sml{cls}">{" ".join(notes)}</td>',
                    "</tr>"]
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def plain_table(table_id: str, rows: list, boxed: bool = False) -> str:
    out = [f'<table id="{table_id}" class="solid" width="100%">', "<thead>", "<tr>"]
    for label, width in [("Code Point", 12), ("VS", 8), ("Plain", 12),
                         ("With VS", 12), ("Description", 56)]:
        out.append(f'\t<th class="sm" width="{width}%">{label}</th>')
    out += ["</tr>", "</thead>", "<tbody>"]
    for base, vs, desc in rows:
        out += ["<tr>",
                f'\t<td class="sm1">{u(base)}</td>',
                f'\t<td class="sm1">{vs_label(vs)}</td>',
                f'\t<td class="sml1">{glyph_span(chr(base), boxed)}</td>',
                f'\t<td class="sml1">{glyph_span(chr(base) + chr(vs), boxed)}</td>',
                f'\t<td class="sml1">{html.escape(desc)}</td>',
                "</tr>"]
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def svs_section(fonts: Fonts, sv: dict, sv_version: str, n_ivs: int) -> tuple[str, int, dict]:
    compat, other, private = [], [], []
    for (base, vs) in sorted(fonts.uvs):
        if vs >= 0xE0100:
            continue
        desc, context = sv.get((base, vs), (None, None))
        name = unicodedata.name(chr(base), u(base))
        if fonts.same(fonts.uvs[(base, vs)], fonts.default(base)):
            name += ". The font maps this sequence to the same glyph as the plain character."
        if desc and desc.startswith("CJK COMPATIBILITY IDEOGRAPH-"):
            compat.append((base, vs, int(desc.rsplit("-", 1)[1], 16)))
        elif desc:
            other.append((base, vs, f"{desc}{f' ({context})' if context else ''} — {name}"))
        else:
            private.append((base, vs, name))
    total = len(compat) + len(other) + len(private)
    sv_compat = sum(1 for d, _ in sv.values() if d.startswith("CJK COMPATIBILITY IDEOGRAPH-"))
    sv_url = f"https://www.unicode.org/Public/{sv_version}/ucd/StandardizedVariants.txt"
    parts = [
        '<h2 id="SVS">Standardized Variation Sequences 標準化變體序列</h2>',
        f"<p>In addition to the {n_ivs:,} ideographic variation sequences above, "
        f"BabelStone Han supports {total:,} variation sequences with the standard "
        "variation selectors VS1–VS3 (U+FE00–FE02), listed below, so that this page "
        "covers every variation sequence in the fonts. This section is not part of "
        "the upstream chart: it is generated from the fonts' cmap format 14 tables "
        f'and <a href="{sv_url}">StandardizedVariants-{sv_version}.txt</a>.</p>',
        zh(f"除了上方的 {n_ivs:,} 組表意文字異體字序列（IVS），BabelStone Han 還支援 {total:,} 組"
           "使用標準變體選擇符 VS1–VS3（U+FE00–FE02）的變體序列，列於下方，使本頁涵蓋字型中的"
           "全部異體字序列。本節不屬於上游對照表，而是由字型的 cmap format 14 表與 "
           f'<a href="{sv_url}">StandardizedVariants-{sv_version}.txt</a> 自動生成。'),
        f'<h3 id="SVS-compat-h">CJK Compatibility Ideographs 中日韓相容表意文字 ({len(compat):,})</h3>',
        "<p>Unicode normalization turns each CJK compatibility ideograph into its "
        "unified ideograph, losing its distinct glyph; the standardized variation "
        "sequence (unified ideograph + VS) listed here keeps that glyph. The Glyph and "
        "Compatibility Ideograph columns should therefore look the same. Unicode has "
        "defined such a sequence for every CJK compatibility ideograph since version 6.3 "
        f"(2013); BabelStone Han supports {len(compat):,} of the {sv_compat:,} in "
        f"Unicode {sv_version}, while most CJK fonts support few or none.</p>",
        zh("Unicode 正規化會把每個中日韓相容表意文字轉為對應的統一表意文字，因而失去其獨特字形；"
           "此處列出的標準化變體序列（統一表意文字＋VS）則保留了該字形，因此 Glyph 與 "
           "Compatibility Ideograph 兩欄應顯示相同的字形。Unicode 自 6.3 版（2013 年）起即為每個"
           f"中日韓相容表意文字定義了這類序列；Unicode {sv_version} 共 {sv_compat:,} 組，BabelStone Han "
           f"支援其中 {len(compat):,} 組，而多數中日韓字型支援得很少或完全不支援。"),
        compat_table(compat, fonts),
        "<br/>",
        f'<h3 id="SVS-other">Other Standardized Variants 其他標準化變體 ({len(other):,})</h3>',
        "<p>The dashed box around each glyph is its character cell: the glyph's advance "
        "width by 1 em, so the position of a mark within a fullwidth cell (corner or "
        "centre) and the narrower advance of a non-fullwidth form can be compared "
        "directly.</p>",
        zh("每個字形外的虛線框是它的字身框：寬為字形的步進寬度（advance width），高為 1 em。"
           "由此可直接比較標點在全形字身框中的位置（靠角或置中），以及非全形形式較窄的步進寬度。"),
        plain_table("SVS-other-table", other, boxed=True),
        "<br/>",
        f'<h3 id="SVS-babelstone">BabelStone-specific Sequences BabelStone 自訂序列 ({len(private):,})</h3>',
        f"<p>These sequences are not in StandardizedVariants-{sv_version}.txt; they are "
        "private conventions of BabelStone Han and may change in future versions.</p>",
        zh(f"這些序列不在 StandardizedVariants-{sv_version}.txt 中，是 BabelStone Han "
           "自訂的慣例，日後版本可能會變動。"),
        plain_table("SVS-babelstone-table", private),
    ]
    counts = {"compat": len(compat), "other": len(other), "private": len(private)}
    return "\n\n".join(parts) + "\n", total, counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-dl", action="store_true", help="Skip download step")
    args = ap.parse_args()
    if not args.no_dl:
        download()

    page = UPSTREAM_HTML.read_text(encoding="utf-8")
    fonts = Fonts()
    sv, sv_version = load_standardized_variants()

    # The upstream table must list exactly the fonts' IVSes, or the page is stale.
    listed = {(ord(s[0]), ord(s[1])) for s in
              re.findall(r'<span class="bs_han vbig">([^<]{2})</span>', page)}
    in_fonts = {k for k in fonts.uvs if k[1] >= 0xE0100}
    if listed != in_fonts:
        raise SystemExit(f"upstream chart lists {len(listed)} IVSes, fonts have "
                         f"{len(in_fonts)} ({len(in_fonts - listed)} missing, "
                         f"{len(listed - in_fonts)} extra); check the release tag")

    page, restored = restore_ivd_markers(page)
    page, ivd_new = add_new_ivd_markers(page)
    section, n_svs, counts = svs_section(fonts, sv, sv_version, len(listed))
    note = (
        '<div class="webfont-note">\n<p>Test copy of the upstream <code>BSH_IVS.html</code>, rendered with the\n'
        f'<code>@free-fonts/babelstone-han@{VERSION}</code> chunked webfonts from jsDelivr\n'
        f'(<a href="{CSS_URL}">babelstone-han.css</a>) instead of locally installed fonts;\n'
        "it needs nothing else and works from any computer with Internet access.\n"
        "Every glyph in the tables should show the variant for its variation selector.\n"
        f'A generated <a href="#SVS">Standardized Variation Sequences</a> section ({n_svs:,} more\n'
        f"sequences) at the end makes the page cover all {len(listed) + n_svs:,} variation sequences in the fonts.\n"
        + (f'{restored} IVD markers (<span class="ivd-restored">*</span>) missing from the upstream HTML table '
           "were restored from <code>BSH_IVS.TXT</code> of the same release." if restored else "")
        + (f'{ivd_new} sequences registered since, in IVD {IVD_VERSION}, are starred as well '
           f'(<span class="ivd-new">*</span>) after comparing their glyphs with the registered ones.' if ivd_new else "")
        + '</p>\n<p lang="zh-Hant">'
        +
        f"本頁為上游 <code>BSH_IVS.html</code> 的測試副本，改用本包 {VERSION} 的切片網頁字型（經 jsDelivr 載入）渲染，"
        "無其他依賴，任何聯網電腦皆可正確顯示；"
        f'文末另附自動生成的<a href="#SVS">標準化變體序列</a>一節，合計涵蓋字型支援的全部 {len(listed) + n_svs:,} 組異體字序列'
        + (f"；上游 HTML 漏標的 {restored} 個 IVD 已註冊標記（虛線底線）依同版本 <code>BSH_IVS.TXT</code> 補上" if restored else "")
        + (f"；另有 {ivd_new} 組在 IVD {IVD_VERSION} 新註冊、經比對字形相符者亦加上標記（雙底線）" if ivd_new else "")
        + "。</p>\n</div>"
    )
    for old, new in [
        ('<link rel="stylesheet" type="text/css" href="../BabelStone.css" />', HEAD),
        ("<h1>BabelStone Fonts</h1>",
         "<h1>BabelStone Fonts</h1>\n" + note + "\n" + toc(len(listed), n_svs, counts)),
        ("<h2>BabelStone Han Variation Sequences</h2>",
         '<h2 id="intro">BabelStone Han Variation Sequences</h2>'),
        ('href="Han.html"', 'href="https://www.babelstone.co.uk/Fonts/Han.html"'),
        ('href="BSH_IVS.TXT"', f'href="{RELEASE_BASE}/{TAG}/BSH_IVS.TXT"'),
        ('href="../CJK/Evidence/', 'href="https://www.babelstone.co.uk/CJK/Evidence/'),
        ('</table>\n<br/>\n<hr class="toe" />',
         '</table>\n<br/>\n\n' + section + '<br/>\n<hr class="toe" />'),
    ]:
        if page.count(old) != 1:
            raise SystemExit(f"upstream page changed; expected one {old!r}")
        page = page.replace(old, new)

    page = add_upstream_translations(page)
    OUT_PATH.write_text(page, encoding="utf-8")
    print(f"{OUT_PATH.name}: {len(listed):,} IVS (upstream, {restored} IVD markers "
          f"restored from BSH_IVS.TXT, {ivd_new} added from IVD {IVD_VERSION}) + {n_svs:,} SVS "
          f"(generated, Unicode {sv_version}); fonts from {CSS_URL}")


if __name__ == "__main__":
    main()
