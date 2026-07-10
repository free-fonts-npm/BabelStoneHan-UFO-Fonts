#!/usr/bin/env python3
"""Build chunked woff2 + CSS for the BabelStone Han webfont package.

Downloads the three BabelStone Han TTFs from the upstream GitHub releases
(babelstone/babelstonehan-ufo), slices each into 256-codepoint woff2 chunks,
and generates babelstone-han.css.

Basic keeps OpenType layout (GSUB calt/liga/vert, GPOS) and IVS; every
Basic/Extra chunk also carries the font's variation selectors so cmap
format-14 data survives subsetting.

Usage:
    pip install fonttools brotli
    python3 build.py            # download to src/ + build all chunks
    python3 build.py --no-dl    # skip download (src/*.ttf already present)
"""

import argparse
import logging
import urllib.request
from multiprocessing import Pool, cpu_count
from pathlib import Path

from fontTools import subset as ft_subset
from fontTools.ttLib import TTFont

logging.getLogger("fontTools").setLevel(logging.ERROR)

ROOT = Path(__file__).parent
SRC_DIR = ROOT / "src"
FONTS_DIR = ROOT / "fonts"
CSS_PATH = ROOT / "babelstone-han.css"
CHUNK_SIZE = 0x100

RELEASE_BASE = "https://github.com/babelstone/babelstonehan-ufo/releases/download"

SOURCES = [
    {
        "url": f"{RELEASE_BASE}/20260707/BabelStoneHanBasicBeta.ttf",
        "file": "BabelStoneHanBasicBeta.ttf",
        "tag": "20260707",
        "prefix": "BabelStoneHanBasic",
        "family": "BabelStone Han Basic",
        "keep_layout": True,
        "note": "BMP: URO, Ext A, compatibility ideographs; GSUB/GPOS/IVS kept",
    },
    {
        "url": f"{RELEASE_BASE}/20260707/BabelStoneHanExtraBeta.ttf",
        "file": "BabelStoneHanExtraBeta.ttf",
        "tag": "20260707",
        "prefix": "BabelStoneHanExtra",
        "family": "BabelStone Han Extra",
        "keep_layout": True,  # no GSUB upstream, but keep the cmap14 IVS path
        "note": "Supplementary planes: Ext B-J; IVS kept",
    },
    {
        "url": f"{RELEASE_BASE}/PUAv1.478/BabelStoneHanPUA.ttf",
        "file": "BabelStoneHanPUA.ttf",
        "tag": "PUAv1.478",
        "prefix": "BabelStoneHanPUA",
        "family": "BabelStone Han PUA",
        "keep_layout": False,
        "note": "PUA U+E080-F8DE: unencoded/provisional ideographs",
    },
]


def download() -> None:
    SRC_DIR.mkdir(exist_ok=True)
    for src in SOURCES:
        dest = SRC_DIR / src["file"]
        if dest.exists():
            print(f"{dest.name} already present, skipping download.")
            continue
        print(f"Downloading {src['url']} ...")
        urllib.request.urlretrieve(src["url"], dest)
        print(f"  {dest.stat().st_size / 1024 / 1024:.1f} MB -> {dest}")


def variation_selectors(ttf_path: Path) -> list[int]:
    tt = TTFont(str(ttf_path), lazy=True)
    vs: set[int] = set()
    for table in tt["cmap"].tables:
        if table.format == 14:
            vs.update(table.uvsDict.keys())
    tt.close()
    return sorted(vs)


def _build_chunk(args: tuple) -> tuple[str, int]:
    ttf_path, cps, out_path, keep_layout, extra_unicodes = args
    options = ft_subset.Options()
    options.flavor = "woff2"
    options.name_IDs = [1, 2, 4]
    options.drop_tables += ["DSIG"]
    if not keep_layout:
        options.layout_features = []
        options.drop_tables += ["morx", "prop", "GDEF", "GPOS", "GSUB"]

    font = ft_subset.load_font(ttf_path, options)
    subsetter = ft_subset.Subsetter(options=options)
    subsetter.populate(unicodes=sorted(cps) + extra_unicodes)
    subsetter.subset(font)
    ft_subset.save_font(font, out_path, options)
    font.close()
    p = Path(out_path)
    return p.name, p.stat().st_size


def unicode_range_str(start: int) -> str:
    end = start + CHUNK_SIZE - 1
    if end <= 0xFFFF:
        return f"U+{start:04X}-{end:04X}"
    return f"U+{start:05X}-{end:05X}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-dl", action="store_true", help="Skip download step")
    ap.add_argument("--jobs", type=int, default=cpu_count(), metavar="N")
    args = ap.parse_args()

    if not args.no_dl:
        download()

    FONTS_DIR.mkdir(exist_ok=True)
    sections = []
    for src in SOURCES:
        ttf = SRC_DIR / src["file"]
        tt = TTFont(str(ttf), lazy=True)
        cps = set(tt.getBestCmap())
        version = tt["name"].getDebugName(5)
        tt.close()
        vs = variation_selectors(ttf) if src["keep_layout"] else []

        chunk_map: dict[int, set[int]] = {}
        for cp in cps:
            chunk_map.setdefault((cp // CHUNK_SIZE) * CHUNK_SIZE, set()).add(cp)
        print(f"{ttf.name}: {len(cps):,} cps, {len(chunk_map)} chunks, "
              f"{len(vs)} variation selectors, {version}")

        tasks = [
            (str(ttf), chunk_cps,
             str(FONTS_DIR / f"{src['prefix']}-{start:06x}.woff2"),
             src["keep_layout"], vs)
            for start, chunk_cps in sorted(chunk_map.items())
        ]
        with Pool(processes=args.jobs) as pool:
            for i, (name, size) in enumerate(pool.imap_unordered(_build_chunk, tasks), 1):
                if i % 40 == 0 or i == len(tasks):
                    print(f"  [{i}/{len(tasks)}] {name} {size // 1024} KB")

        rules = []
        for start in sorted(chunk_map):
            rules.append(
                "@font-face {\n"
                f"  font-family: '{src['family']}';\n"
                "  font-style: normal;\n"
                "  font-weight: 400;\n"
                "  font-display: swap;\n"
                f"  src: url('fonts/{src['prefix']}-{start:06x}.woff2') format('woff2');\n"
                f"  unicode-range: {unicode_range_str(start)};\n"
                "}"
            )
        sections.append(
            f"/* {src['family']} — {src['note']} */\n\n" + "\n\n".join(rules)
        )

    header = (
        "/* BabelStone Han Webfonts (Basic + Extra + PUA)\n"
        " * Upstream: https://github.com/babelstone/babelstonehan-ufo\n"
        " *   Basic/Extra: tag 20260707 (Version 17.0.2 BETA); PUA: tag PUAv1.478\n"
        " * Generated CSS; do not edit manually.\n"
        " * Chunk size: 256 codepoints.\n"
        " */\n\n"
    )
    CSS_PATH.write_text(header + "\n\n".join(sections) + "\n", encoding="utf-8")
    total = sum(s.count("@font-face") for s in sections)
    print(f"\nCSS -> {CSS_PATH} ({total} @font-face rules)")


if __name__ == "__main__":
    main()
