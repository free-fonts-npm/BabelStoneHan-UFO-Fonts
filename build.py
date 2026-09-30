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
        "url": f"{RELEASE_BASE}/v18.0.1/BabelStoneHanBasic.ttf",
        "file": "BabelStoneHanBasic.ttf",
        "tag": "v18.0.1",
        "prefix": "BabelStoneHanBasic",
        "family": "BabelStone Han Basic",
        "keep_layout": True,
        "note": "BMP: URO, Ext A, compatibility ideographs; GSUB/GPOS/IVS kept",
    },
    {
        "url": f"{RELEASE_BASE}/v18.0.1/BabelStoneHanExtra.ttf",
        "file": "BabelStoneHanExtra.ttf",
        "tag": "v18.0.1",
        "prefix": "BabelStoneHanExtra",
        "family": "BabelStone Han Extra",
        "keep_layout": True,  # no GSUB upstream, but keep the cmap14 IVS path
        "note": "Supplementary planes: Ext B-J; IVS kept",
    },
    {
        "url": f"{RELEASE_BASE}/PUAv1.484/BabelStoneHanPUA.ttf",
        "file": "BabelStoneHanPUA.ttf",
        "tag": "PUAv1.484",
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


def vs_only_bases(ttf_path: Path) -> set[int]:
    """Base codepoints reachable only through a variation sequence.

    Basic's cmap14 maps e.g. <U+20122, U+FE00> (the standardized variant for
    compatibility ideograph U+2F803) to its own glyph, but U+20122 itself is
    not in Basic's cmap. Those bases get no regular chunk, so they need a
    dedicated one or browsers never try Basic for them.
    """
    tt = TTFont(str(ttf_path), lazy=True)
    mapped = set(tt.getBestCmap())
    bases: set[int] = set()
    for table in tt["cmap"].tables:
        if table.format == 14:
            for pairs in table.uvsDict.values():
                bases.update(b for b, g in pairs if g is not None and b not in mapped)
    tt.close()
    return bases


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


def codepoint_ranges_str(cps: set[int]) -> str:
    runs: list[list[int]] = []
    for cp in sorted(cps):
        if runs and cp == runs[-1][1] + 1:
            runs[-1][1] = cp
        else:
            runs.append([cp, cp])
    return ", ".join(
        f"U+{a:04X}" if a == b else f"U+{a:04X}-{b:04X}" for a, b in runs
    )


def font_face(family: str, file: str, unicode_range: str) -> str:
    return (
        "@font-face {\n"
        f"  font-family: '{family}';\n"
        "  font-style: normal;\n"
        "  font-weight: 400;\n"
        "  font-display: swap;\n"
        f"  src: url('fonts/{file}') format('woff2');\n"
        f"  unicode-range: {unicode_range};\n"
        "}"
    )


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
        svs_bases = vs_only_bases(ttf) if vs else set()

        chunk_map: dict[int, set[int]] = {}
        for cp in cps:
            chunk_map.setdefault((cp // CHUNK_SIZE) * CHUNK_SIZE, set()).add(cp)
        print(f"{ttf.name}: {len(cps):,} cps, {len(chunk_map)} chunks, "
              f"{len(vs)} variation selectors, "
              f"{len(svs_bases)} VS-only bases, {version}")

        tasks = [
            (str(ttf), chunk_cps,
             str(FONTS_DIR / f"{src['prefix']}-{start:06x}.woff2"),
             src["keep_layout"], vs)
            for start, chunk_cps in sorted(chunk_map.items())
        ]
        svs_file = f"{src['prefix']}-svs.woff2"
        if svs_bases:
            tasks.append((str(ttf), svs_bases, str(FONTS_DIR / svs_file),
                          src["keep_layout"], vs))
        with Pool(processes=args.jobs) as pool:
            for i, (name, size) in enumerate(pool.imap_unordered(_build_chunk, tasks), 1):
                if i % 40 == 0 or i == len(tasks):
                    print(f"  [{i}/{len(tasks)}] {name} {size // 1024} KB")

        rules = [
            font_face(src["family"], f"{src['prefix']}-{start:06x}.woff2",
                      unicode_range_str(start))
            for start in sorted(chunk_map)
        ]
        if svs_bases:
            # Exact codepoints rather than 256 blocks: only pages that use one
            # of these bases fetch this file; a bare base (no VS) still falls
            # through to the next family since this chunk has no cmap entry.
            rules.append(font_face(src["family"], svs_file,
                                   codepoint_ranges_str(svs_bases)))
        sections.append(
            f"/* {src['family']} — {src['note']} */\n\n" + "\n\n".join(rules)
        )

    header = (
        "/* BabelStone Han Webfonts (Basic + Extra + PUA)\n"
        " * Upstream: https://github.com/babelstone/babelstonehan-ufo\n"
        " *   Basic/Extra: tag v18.0.1 (Version 18.0.1); PUA: tag PUAv1.484\n"
        " * Generated CSS; do not edit manually.\n"
        " * Chunk size: 256 codepoints.\n"
        " */\n\n"
    )
    CSS_PATH.write_text(header + "\n\n".join(sections) + "\n", encoding="utf-8")
    total = sum(s.count("@font-face") for s in sections)
    print(f"\nCSS -> {CSS_PATH} ({total} @font-face rules)")


if __name__ == "__main__":
    main()
