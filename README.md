# BabelStone Han Webfonts

Chunked woff2 webfonts for the three BabelStone Han fonts, generated from
[babelstone/babelstonehan-ufo](https://github.com/babelstone/babelstonehan-ufo):

| Family | Coverage | Upstream version |
|--------|----------|------------------|
| `BabelStone Han Basic` | BMP: URO (U+4E00–9FFF), Ext A, compatibility ideographs, punctuation — 33,810 codepoints | 17.0.2 BETA (tag `20260707`) |
| `BabelStone Han Extra` | Supplementary planes: Ext B–J (U+20000–U+323AF), compat supplement — 36,909 codepoints | 17.0.2 BETA (tag `20260707`) |
| `BabelStone Han PUA` | BMP Private Use Area (U+E080–U+F8DE): 4,900+ unencoded or provisional ideographs — companion to the IDS data | 1.478 (tag `PUAv1.478`) |

Together they cover ~75,000 codepoints. Stack all three families and browsers
download only the 256-codepoint slices actually used on the page:

```html
<link rel="stylesheet" href="./babelstone-han.css">
```

```css
body {
  font-family: 'BabelStone Han Basic', 'BabelStone Han Extra',
    'BabelStone Han PUA', serif;
}
```

![Specimen: sample glyphs from BabelStone Han Basic, Extra, and PUA with their codepoints](assets/specimen.png)

(Rows 1: Basic — URO and Ext A; rows 2–3: Extra — Ext B and Ext C–J;
row 4: PUA. The full PUA glyph chart with IDS data is published as
`PUA.html` / `IDS_PUA.TXT` in each
[upstream release](https://github.com/babelstone/babelstonehan-ufo/releases).)

## OpenType features

The Basic slices keep the upstream GSUB/GPOS tables (`calt`, `liga`, `vert`)
and Ideographic Variation Sequences (cmap format 14); every slice carries the
font's variation selectors so base+VS pairs render correctly. Extra slices
keep IVS as well. PUA has no layout tables upstream.

- Upstream: https://github.com/babelstone/babelstonehan-ufo
  (UFO sources for https://www.babelstone.co.uk/Fonts/)
- Upstream font license: Arphic Public License
- Package scripts and metadata license: MIT
- Generated woff2 files: 484 (256-codepoint `unicode-range` chunks)
- Rebuild from upstream: `pip install fonttools brotli && python3 build.py`

## Modification notice (Arphic Public License §2a)

The `fonts/*.woff2` files in this package were generated from the upstream
`BabelStoneHanBasicBeta.ttf` / `BabelStoneHanExtraBeta.ttf` (tag `20260707`)
and `BabelStoneHanPUA.ttf` (tag `PUAv1.478`) by subsetting into 256-codepoint
slices and converting to WOFF2 with fontTools. Glyph outlines are unmodified.
