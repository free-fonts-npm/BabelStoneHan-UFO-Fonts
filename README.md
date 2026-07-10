# BabelStone Han Webfonts ／ BabelStone Han 網頁字型

[繁體中文](#繁體中文) · [English](#english)

![樣張：BabelStone Han Basic、Extra、PUA 各行示例字形及其碼位 ／ Specimen: sample glyphs from BabelStone Han Basic, Extra, and PUA with their codepoints](assets/specimen.png)

（第 1 行：Basic — URO 與 Ext A；第 2–3 行：Extra — Ext B 與 Ext C–J；第 4 行：PUA。
Row 1: Basic — URO and Ext A; rows 2–3: Extra — Ext B and Ext C–J; row 4: PUA.）

---

## 繁體中文

BabelStone Han 三款字型的 256 碼位切片 woff2 網頁字型，生成自
[babelstone/babelstonehan-ufo](https://github.com/babelstone/babelstonehan-ufo)
（[BabelStone Fonts](https://www.babelstone.co.uk/Fonts/) 的 UFO 源碼倉庫）：

| 字族 | 覆蓋範圍 | 上游版本 |
|------|----------|----------|
| `BabelStone Han Basic` | 基本平面：URO（U+4E00–9FFF）、Ext A、相容表意文字、標點——33,810 碼位 | 17.0.2 BETA（tag `20260707`） |
| `BabelStone Han Extra` | 增補平面：Ext B–J（U+20000–U+323AF）、相容表意文字補充——36,909 碼位 | 17.0.2 BETA（tag `20260707`） |
| `BabelStone Han PUA` | BMP 私用區（U+E080–U+F8DE）：4,900 多個未編碼或暫定漢字——配合 IDS 資料使用 | 1.478（tag `PUAv1.478`） |

三者合計覆蓋約 75,000 碼位。將三個字族依序疊入 font stack，瀏覽器只會下載
頁面實際用到的 256 碼位分片：

### 使用方式

```html
<link rel="stylesheet" href="./babelstone-han.css">
```

發布到 npm 後建議從 jsDelivr 載入（本包僅約 19 MB，遠低於 jsDelivr 150 MB
的整包上限，可正常服務）：

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@free-fonts/babelstone-han@1.0.0/babelstone-han.css">
```

unpkg 等效：

```html
<link rel="stylesheet" href="https://unpkg.com/@free-fonts/babelstone-han@1.0.0/babelstone-han.css">
```

```css
body {
  font-family: 'BabelStone Han Basic', 'BabelStone Han Extra',
    'BabelStone Han PUA', serif;
}
```

CSS 以 256 碼位為一片的 `unicode-range` 切片（與 `jigmo-webfonts` 等 CJK
網頁字型專案相同的慣例），沒有生僻字的頁面下載零位元組。

### OpenType 特性

Basic 的分片保留上游 GSUB/GPOS 表（`calt`、`liga`、`vert` 直排替換）與
表意文字異體字序列（IVS，cmap format 14）；每個分片都帶有字型的異體字
選擇符，base+VS 組合可正常顯示。Extra 分片同樣保留 IVS。PUA 上游本身
無 layout 表。

- 上游：<https://github.com/babelstone/babelstonehan-ufo>（<https://www.babelstone.co.uk/Fonts/> 的 UFO 源碼）
- 上游字型授權：Arphic Public License（文鼎公眾授權）
- 本包腳本與詮釋資料授權：MIT
- 生成的 woff2 檔案：484 個（256 碼位 `unicode-range` 分片）
- 從上游重建：`pip install fonttools brotli && python3 build.py`

### 修改聲明（Arphic Public License §2a）

本包 `fonts/*.woff2` 生成自上游 `BabelStoneHanBasicBeta.ttf`／
`BabelStoneHanExtraBeta.ttf`（tag `20260707`）與 `BabelStoneHanPUA.ttf`
（tag `PUAv1.478`），以 fontTools 切為 256 碼位分片並轉換為 WOFF2。
字形輪廓未經修改。

完整的 PUA 字形對照表（含 IDS 資料）以 `PUA.html`／`IDS_PUA.TXT` 隨每次
[上游 release](https://github.com/babelstone/babelstonehan-ufo/releases) 發布。

---

## English

Chunked woff2 webfonts for the three BabelStone Han fonts, generated from
[babelstone/babelstonehan-ufo](https://github.com/babelstone/babelstonehan-ufo)
(the UFO source repository for
[BabelStone Fonts](https://www.babelstone.co.uk/Fonts/)):

| Family | Coverage | Upstream version |
|--------|----------|------------------|
| `BabelStone Han Basic` | BMP: URO (U+4E00–9FFF), Ext A, compatibility ideographs, punctuation — 33,810 codepoints | 17.0.2 BETA (tag `20260707`) |
| `BabelStone Han Extra` | Supplementary planes: Ext B–J (U+20000–U+323AF), compat supplement — 36,909 codepoints | 17.0.2 BETA (tag `20260707`) |
| `BabelStone Han PUA` | BMP Private Use Area (U+E080–U+F8DE): 4,900+ unencoded or provisional ideographs — companion to the IDS data | 1.478 (tag `PUAv1.478`) |

Together they cover ~75,000 codepoints. Stack all three families and browsers
download only the 256-codepoint slices actually used on the page:

### Usage

```html
<link rel="stylesheet" href="./babelstone-han.css">
```

Once published to npm, loading from jsDelivr is recommended (at ~19 MB the
package is well under jsDelivr's 150 MB whole-package limit):

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@free-fonts/babelstone-han@1.0.0/babelstone-han.css">
```

unpkg equivalent:

```html
<link rel="stylesheet" href="https://unpkg.com/@free-fonts/babelstone-han@1.0.0/babelstone-han.css">
```

```css
body {
  font-family: 'BabelStone Han Basic', 'BabelStone Han Extra',
    'BabelStone Han PUA', serif;
}
```

The CSS uses 256-codepoint `unicode-range` chunks (the same convention used by
CJK webfont projects like `jigmo-webfonts`), so pages containing no rare
characters download zero bytes.

### OpenType features

The Basic slices keep the upstream GSUB/GPOS tables (`calt`, `liga`, `vert`)
and Ideographic Variation Sequences (cmap format 14); every slice carries the
font's variation selectors so base+VS pairs render correctly. Extra slices
keep IVS as well. PUA has no layout tables upstream.

- Upstream: <https://github.com/babelstone/babelstonehan-ufo>
  (UFO sources for <https://www.babelstone.co.uk/Fonts/>)
- Upstream font license: Arphic Public License
- Package scripts and metadata license: MIT
- Generated woff2 files: 484 (256-codepoint `unicode-range` chunks)
- Rebuild from upstream: `pip install fonttools brotli && python3 build.py`

### Modification notice (Arphic Public License §2a)

The `fonts/*.woff2` files in this package were generated from the upstream
`BabelStoneHanBasicBeta.ttf` / `BabelStoneHanExtraBeta.ttf` (tag `20260707`)
and `BabelStoneHanPUA.ttf` (tag `PUAv1.478`) by subsetting into 256-codepoint
slices and converting to WOFF2 with fontTools. Glyph outlines are unmodified.

The full PUA glyph chart with IDS data is published as `PUA.html` /
`IDS_PUA.TXT` in each
[upstream release](https://github.com/babelstone/babelstonehan-ufo/releases).
