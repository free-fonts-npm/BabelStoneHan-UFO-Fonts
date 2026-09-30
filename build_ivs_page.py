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
  babelstone.co.uk / the upstream release; the "Standardized Variation
  Sequences" section at the end is generated from the fonts by
  build_ivs_page.py. The upstream table content is unchanged.
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
.webfont-note {{ border: 1px solid #c90; background: rgba(255, 204, 0, 0.12); padding: 0.6em 1em; }}
table.solid {{ border-collapse: collapse; }}
table.solid th, table.solid td {{ border: 1px solid #999; padding: 0.2em 0.5em; vertical-align: middle; }}
.sm, .sm1, .sm2, .sm3 {{ text-align: center; }}
.sml1, .sml2, .sml3 {{ text-align: left; }}
.sm1, .sml1 {{ background: rgba(128, 128, 128, 0.06); }}
.sm3, .sml3 {{ background: rgba(128, 128, 128, 0.12); }}
</style>"""


def download() -> None:
    SRC_DIR.mkdir(exist_ok=True)
    for url, dest in [(f"{RELEASE_BASE}/{TAG}/BSH_IVS.html", UPSTREAM_HTML),
                      (SV_URL, SV_TXT)]:
        print(f"Downloading {url} ...")
        urllib.request.urlretrieve(url, dest)


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

    def same(self, a, b) -> bool:
        return a is not None and b is not None and (a == b or self.outline(a) == self.outline(b))


def u(cp: int) -> str:
    return f"U+{cp:04X}"


def glyph_span(text: str) -> str:
    return f'<span class="bs_han vbig">{html.escape(text)}</span>'


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


def plain_table(table_id: str, rows: list) -> str:
    out = [f'<table id="{table_id}" class="solid" width="100%">', "<thead>", "<tr>"]
    for label, width in [("Code Point", 12), ("VS", 8), ("Plain", 12),
                         ("With VS", 12), ("Description", 56)]:
        out.append(f'\t<th class="sm" width="{width}%">{label}</th>')
    out += ["</tr>", "</thead>", "<tbody>"]
    for base, vs, desc in rows:
        out += ["<tr>",
                f'\t<td class="sm1">{u(base)}</td>',
                f'\t<td class="sm1">{vs_label(vs)}</td>',
                f'\t<td class="sml1">{glyph_span(chr(base))}</td>',
                f'\t<td class="sml1">{glyph_span(chr(base) + chr(vs))}</td>',
                f'\t<td class="sml1">{html.escape(desc)}</td>',
                "</tr>"]
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def svs_section(fonts: Fonts, sv: dict, sv_version: str, n_ivs: int) -> tuple[str, int]:
    compat, other, private = [], [], []
    for (base, vs) in sorted(fonts.uvs):
        if vs >= 0xE0100:
            continue
        desc, context = sv.get((base, vs), (None, None))
        name = unicodedata.name(chr(base), u(base))
        if fonts.same(fonts.uvs[(base, vs)], fonts.default(base)):
            name += ". Same glyph as the plain character (already its default form)."
        if desc and desc.startswith("CJK COMPATIBILITY IDEOGRAPH-"):
            compat.append((base, vs, int(desc.rsplit("-", 1)[1], 16)))
        elif desc:
            other.append((base, vs, f"{desc}{f' ({context})' if context else ''} — {name}"))
        else:
            private.append((base, vs, name))
    total = len(compat) + len(other) + len(private)
    sv_compat = sum(1 for d, _ in sv.values() if d.startswith("CJK COMPATIBILITY IDEOGRAPH-"))
    parts = [
        '<h2 id="SVS">Standardized Variation Sequences</h2>',
        f"<p>In addition to the {n_ivs:,} ideographic variation sequences above, "
        f"BabelStone Han supports {total:,} variation sequences with the standard "
        "variation selectors VS1–VS3 (U+FE00–FE02), listed below, so that this page "
        "covers every variation sequence in the fonts. This section is not part of "
        "the upstream chart: it is generated from the fonts' cmap format 14 tables "
        f"and <a href=\"https://www.unicode.org/Public/{sv_version}/ucd/StandardizedVariants.txt\">"
        f"StandardizedVariants-{sv_version}.txt</a>.</p>",
        f"<p>本節不屬於上游對照表：由字型的 cmap format 14 表與 Unicode 標準化變體列表自動生成，"
        f"列出 VS1–VS3 的 {total:,} 組序列，連同上方 {n_ivs:,} 組 IVS，涵蓋字型支援的全部異體字序列。</p>",
        f'<h3 id="SVS-compat-h">CJK Compatibility Ideographs ({len(compat):,})</h3>',
        "<p>Unicode normalization turns each CJK compatibility ideograph into its "
        "unified ideograph, losing its distinct glyph; the standardized variation "
        "sequence (unified ideograph + VS) listed here keeps that glyph. The Glyph and "
        "Compatibility Ideograph columns should therefore look the same. BabelStone Han "
        f"supports {len(compat):,} of the {sv_compat:,} such sequences defined in "
        f"Unicode {sv_version}.</p>",
        compat_table(compat, fonts),
        "<br/>",
        f'<h3 id="SVS-other">Other Standardized Variants ({len(other):,})</h3>',
        plain_table("SVS-other-table", other),
        "<br/>",
        f'<h3 id="SVS-babelstone">BabelStone-specific Sequences ({len(private):,})</h3>',
        f"<p>These sequences are not in StandardizedVariants-{sv_version}.txt; they are "
        "private conventions of BabelStone Han and may change in future versions.</p>",
        plain_table("SVS-babelstone-table", private),
    ]
    return "\n\n".join(parts) + "\n", total


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

    section, n_svs = svs_section(fonts, sv, sv_version, len(listed))
    note = (
        '<p class="webfont-note">Test copy of the upstream <code>BSH_IVS.html</code>, rendered with the\n'
        f'<code>@free-fonts/babelstone-han@{VERSION}</code> chunked webfonts from jsDelivr\n'
        f'(<a href="{CSS_URL}">babelstone-han.css</a>) instead of locally installed fonts;\n'
        "it needs nothing else and works from any computer with Internet access.\n"
        "Every glyph in the tables should show the variant for its variation selector.\n"
        f'A generated <a href="#SVS">Standardized Variation Sequences</a> section ({n_svs:,} more\n'
        f"sequences) at the end makes the page cover all {len(listed) + n_svs:,} variation sequences in the fonts.\n"
        f"本頁為上游 <code>BSH_IVS.html</code> 的測試副本，改用本包 {VERSION} 的切片網頁字型（經 jsDelivr 載入）渲染，"
        "無其他依賴，任何聯網電腦皆可正確顯示；"
        f'文末另附自動生成的<a href="#SVS">標準化變體序列</a>一節，合計涵蓋字型支援的全部 {len(listed) + n_svs:,} 組異體字序列。</p>'
    )
    for old, new in [
        ('<link rel="stylesheet" type="text/css" href="../BabelStone.css" />', HEAD),
        ("<h1>BabelStone Fonts</h1>", "<h1>BabelStone Fonts</h1>\n" + note),
        ('href="Han.html"', 'href="https://www.babelstone.co.uk/Fonts/Han.html"'),
        ('href="BSH_IVS.TXT"', f'href="{RELEASE_BASE}/{TAG}/BSH_IVS.TXT"'),
        ('href="../CJK/Evidence/', 'href="https://www.babelstone.co.uk/CJK/Evidence/'),
        ('</table>\n<br/>\n<hr class="toe" />',
         '</table>\n<br/>\n\n' + section + '<br/>\n<hr class="toe" />'),
    ]:
        if page.count(old) != 1:
            raise SystemExit(f"upstream page changed; expected one {old!r}")
        page = page.replace(old, new)

    OUT_PATH.write_text(page, encoding="utf-8")
    print(f"{OUT_PATH.name}: {len(listed):,} IVS (upstream) + {n_svs:,} SVS "
          f"(generated, Unicode {sv_version}); fonts from {CSS_URL}")


if __name__ == "__main__":
    main()
