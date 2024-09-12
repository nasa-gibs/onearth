#!/usr/bin/env python3

from pathlib import Path

HERE = Path(__file__).parent

TO_COPY = [
    HERE / "RgbPngToPalPng.py",
    HERE / "colormap2vrt.py",
    HERE / "mrfgen.py",
    HERE / "oe_utils.py",  # lib used by some of the others
    HERE / "oe_validate_palette.py",
    HERE / "overtiffpacker.py",
]

for p in HERE.glob("*.so"):
    if p.name.startswith("RgbToPalLib."):
        # e.g. RgbToPalLib.cpython-310-x86_64-linux-gnu.so
        TO_COPY.append(p)

if __name__ == "__main__":
    import argparse
    import shutil

    parser = argparse.ArgumentParser()
    parser.add_argument("DIR", type=Path)
    args = parser.parse_args()

    dst_dir = args.DIR
    if not dst_dir.is_dir():
        print("error: install_dir must be an existing directory")
        raise SystemExit(2)

    for src in TO_COPY:
        dst = dst_dir / src.name
        shutil.copy2(src, dst)
        print(f"copied {src} to {dst_dir}")
