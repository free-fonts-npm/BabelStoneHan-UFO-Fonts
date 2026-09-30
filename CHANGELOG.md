# Changelog

## 1.1.0 — 2026-09-30

### 更新

- 上游 Basic／Extra 升至 **18.0.1**（tag [`v18.0.1`](https://github.com/babelstone/babelstonehan-ufo/releases/tag/v18.0.1)，
  首個正式版，檔名不再帶 `Beta`）；PUA 升至 **1.484**
  （tag [`PUAv1.484`](https://github.com/babelstone/babelstonehan-ufo/releases/tag/PUAv1.484)）。
  - Basic：33,810 碼位（不變），修改 8 個字形、新增 3 個異體字形。
  - Extra：36,909 → 37,010 碼位（+101），另修改 31 個字形。
  - PUA：4,979 → 5,058 碼位（1.479–1.484 累計）。
- 全部 484 個分片重新生成；分片清單不變。

### 修正

- Basic 有 110 個基底字（112 組序列）只能經異體字序列取用——多為相容表意文字
  U+2F800–2FA1D 正規化後的標準化變體，如 U+2F803 → `U+20122 U+FE00`。
  這些基底字不在 Basic 的 cmap 裡，1.0.0 的 CSS 因此沒有為它們宣告
  `unicode-range`，瀏覽器改用 Extra 顯示成未變體的基底字。現在打包成
  `fonts/BabelStoneHanBasic-svs.woff2`（約 38 KB），`unicode-range` 只列這
  110 個碼位，只有用到的頁面才會下載。

### 驗證

Chrome 154 逐一渲染全部 5,058 個 PUA 字元及 Basic／Extra 的 4,057 組 IVS／SVS
序列，與完整上游 TTF 逐像素比對，全部一致；110 個基底字單獨出現時仍正確落到 Extra。

新增 `BSH_IVS.html`（僅在 repo，不隨 npm 包發布）：上游 v18.0.1 的 IVS 對照表改用本包
切片字型渲染的測試頁。2,893 組 IVS（1,407 字）全部與 TTF 一致，每字第 1 個變體等於
基底字，同一字的各變體彼此不同。

---

### Updated

- Upstream Basic/Extra → **18.0.1** (tag `v18.0.1`, the first non-beta
  release; file names no longer carry `Beta`); PUA → **1.484** (tag `PUAv1.484`).
  - Basic: 33,810 codepoints (unchanged); 8 glyphs modified, 3 variant glyphs added.
  - Extra: 36,909 → 37,010 codepoints (+101); 31 glyphs modified.
  - PUA: 4,979 → 5,058 codepoints (cumulative 1.479–1.484).
- All 484 slices regenerated; the slice list is unchanged.

### Fixed

- 110 base characters (112 sequences) in Basic are reachable only through a
  variation sequence — mostly standardized variants of compatibility
  ideographs U+2F800–2FA1D after normalization, e.g. U+2F803 →
  `U+20122 U+FE00`. As the bases are not in Basic's cmap, the 1.0.0 CSS
  declared no `unicode-range` for them and browsers rendered the plain base
  from Extra. They now ship in `fonts/BabelStoneHanBasic-svs.woff2` (~38 KB)
  with a `unicode-range` listing only those 110 codepoints, so only pages
  using them download it.

### Verified

Rendered all 5,058 PUA characters and all 4,057 IVS/SVS sequences in
Basic/Extra in Chrome 154 and compared pixel-by-pixel with the full upstream
TTFs: all identical. The 110 bases on their own still fall through to Extra.

Added `BSH_IVS.html` (repo only, not in the npm package): the upstream v18.0.1
IVS chart rendered with these webfonts. All 2,893 IVSes (1,407 characters)
match the TTF; variant 1 equals the base glyph and the variants of each
character are all distinct.

## 1.0.0 — 2026-07-10

- 首次發布：Basic／Extra 17.0.2 BETA（tag `20260707`）、PUA 1.478，切成 484 個
  256 碼位分片。
- Initial release: Basic/Extra 17.0.2 BETA (tag `20260707`), PUA 1.478, as 484
  256-codepoint slices.
