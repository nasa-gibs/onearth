#!/usr/bin/env python3

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Compare files between two directories.
For PNG and JPEG files, compare pixel differences and create difference images using Pillow.
For CSV and SVG files, compare contents exactly.
For other files, compare binary contents.
"""

import os
import sys
from pathlib import Path
import re
from PIL import Image, ImageChops

DEBUG = False

def get_file_type(path):
    """Detect the actual file type using the file extension and, for TIFFs, check for LERC compression."""
    if not os.path.exists(path):
        return None
    ext = os.path.splitext(path)[1].lower()
    if ext == '.png':
        return 'image/png'
    elif ext in ('.jpg', '.jpeg'):
        return 'image/jpeg'
    elif ext in ('.tif', '.tiff'):
        # Check for LERC compression in TIFF
        try:
            from osgeo import gdal
            ds = gdal.Open(path)
            if ds:
                md = ds.GetMetadata('IMAGE_STRUCTURE')
                if md.get('COMPRESSION', '').upper() == 'LERC':
                    return 'image/lerc'
        except ImportError:
            pass
        return 'image/tiff'
    elif ext == '.lerc':
        return 'image/lerc'
    elif ext == '.csv':
        return 'text/csv'
    elif ext == '.svg':
        return 'image/svg+xml'
    elif ext in ('.txt', '.md', '.py', '.json', '.xml', '.yaml', '.yml'):
        return 'text/' + ext[1:]
    else:
        return ''

def compare_images(original_path, updated_path, diff_dir, ext):
    if DEBUG:
        print(f"[DEBUG] Comparing images: {original_path} vs {updated_path}")
    if not os.path.exists(original_path):
        if DEBUG:
            print(f"[DEBUG] ORIGINAL file missing: {original_path}")
        return f"ORIGINAL file missing: {original_path}"
    if not os.path.exists(updated_path):
        if DEBUG:
            print(f"[DEBUG] UPDATED file missing: {updated_path}")
        return f"UPDATED file missing: {updated_path}"
    try:
        img1 = Image.open(original_path).convert('RGB')
        img2 = Image.open(updated_path).convert('RGB')
        if DEBUG:
            print(f"[DEBUG] Image 1 size: {img1.size}, Image 2 size: {img2.size}")
            print(f"[DEBUG] Image 1 first pixel: {img1.getpixel((0,0))}, Image 2 first pixel: {img2.getpixel((0,0))}")
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Error opening images: {e}")
        # Fallback: try text compare
        try:
            with open(original_path, 'r', encoding='utf-8') as f1, open(updated_path, 'r', encoding='utf-8') as f2:
                original_content = f1.read()
                updated_content = f2.read()
                if original_content == updated_content:
                    if DEBUG:
                        print("[DEBUG] Fallback text compare: IDENTICAL")
                    return "IDENTICAL (text)"
                else:
                    if DEBUG:
                        print("[DEBUG] Fallback text compare: DIFFERENT")
                    return "DIFFERENT: text contents do not match (fallback)"
        except Exception as text_e:
            if DEBUG:
                print(f"[DEBUG] Could not open as text: {text_e}")
            # Fallback: binary compare
            try:
                with open(original_path, 'rb') as f1, open(updated_path, 'rb') as f2:
                    if f1.read() == f2.read():
                        if DEBUG:
                            print("[DEBUG] Fallback binary compare: IDENTICAL")
                        return "IDENTICAL (binary)"
                    else:
                        if DEBUG:
                            print("[DEBUG] Fallback binary compare: DIFFERENT")
                        return "DIFFERENT: file contents do not match (binary fallback)"
            except Exception as bin_e:
                if DEBUG:
                    print(f"[DEBUG] Could not open as binary: {bin_e}")
                return f"Error opening files as image, text, or binary: {bin_e}"
    if img1.size != img2.size:
        if DEBUG:
            print("[DEBUG] Different dimensions")
        return f"Different dimensions: ORIGINAL={img1.size}, UPDATED={img2.size}"
    diff = ImageChops.difference(img1, img2)
    bbox = diff.getbbox()
    if DEBUG:
        print(f"[DEBUG] Diff bbox: {bbox}")
    if bbox is None:
        if DEBUG:
            print("[DEBUG] Images are IDENTICAL")
        return "IDENTICAL"
    else:
        diff_pixels = sum(1 for pixel in diff.getdata() if pixel[:3] != (0, 0, 0))
        if DEBUG:
            print(f"[DEBUG] Pixel diff count: {diff_pixels}")
        diff_path = os.path.join(diff_dir, f"diff_{os.path.basename(original_path)}")
        enhanced_diff = diff.copy().convert('RGB')
        enhanced_diff.save(diff_path)
        return f"DIFFERENT: {diff_pixels} pixels changed (diff saved to {diff_path})"

def compare_text(original_path, updated_path):
    if not os.path.exists(original_path):
        return f"ORIGINAL file missing: {original_path}"
    if not os.path.exists(updated_path):
        return f"UPDATED file missing: {updated_path}"
    with open(original_path, 'r', encoding='utf-8') as f1, open(updated_path, 'r', encoding='utf-8') as f2:
        original_content = f1.read()
        updated_content = f2.read()
        if original_content == updated_content:
            return "IDENTICAL"
        else:
            return "DIFFERENT: text contents do not match"

def compare_svg(original_path, updated_path, diff_dir):
    # First, compare as text
    text_result = compare_text(original_path, updated_path)
    # Now, try to render both SVGs to PNG and compare as images
    try:
        import cairosvg
        from PIL import Image
        import io
        with open(original_path, 'r', encoding='utf-8') as f:
            svg1 = f.read()
        with open(updated_path, 'r', encoding='utf-8') as f:
            svg2 = f.read()
        png1 = cairosvg.svg2png(bytestring=svg1.encode('utf-8'))
        png2 = cairosvg.svg2png(bytestring=svg2.encode('utf-8'))
        img1 = Image.open(io.BytesIO(png1)).convert('RGB')
        img2 = Image.open(io.BytesIO(png2)).convert('RGB')
        diff = ImageChops.difference(img1, img2)
        bbox = diff.getbbox()
        if bbox is None:
            image_result = "IDENTICAL (rendered image)"
        else:
            diff_pixels = sum(1 for pixel in diff.getdata() if pixel[:3] != (0, 0, 0))
            diff_path = os.path.join(diff_dir, f"diff_{os.path.basename(original_path)}.png")
            diff_img = diff.copy().convert('RGB')
            diff_img.save(diff_path)
            image_result = f"DIFFERENT (rendered image): {diff_pixels} pixels changed (diff saved to {diff_path})"
    except ImportError:
        image_result = "[WARN] cairosvg not installed, skipping SVG image comparison"
    except Exception as e:
        image_result = f"[WARN] SVG image comparison failed: {e}"
    return f"SVG text: {text_result}\nSVG image: {image_result}"

def compare_lerc_images(original_path, updated_path, diff_dir):
    try:
        from osgeo import gdal
        import numpy as np
        arr1 = None
        arr2 = None
        ds1 = gdal.Open(original_path)
        ds2 = gdal.Open(updated_path)
        if ds1 is None or ds2 is None:
            return f"Error opening LERC images with GDAL"
        arr1 = ds1.GetRasterBand(1).ReadAsArray()
        arr2 = ds2.GetRasterBand(1).ReadAsArray()
        if arr1.shape != arr2.shape:
            return f"Different dimensions: {arr1.shape} vs {arr2.shape}"
        diff = np.abs(arr1 - arr2)
        diff_pixels = np.count_nonzero(diff)
        if diff_pixels == 0:
            return "IDENTICAL"
        else:
            # Optionally, save a diff image (as PNG)
            try:
                from PIL import Image
                import numpy as np
                norm = (diff > 0).astype(np.uint8) * 255
                diff_img = Image.fromarray(norm)
                diff_path = os.path.join(diff_dir, f"diff_{os.path.basename(original_path)}.png")
                diff_img.save(diff_path)
                return f"DIFFERENT: {diff_pixels} pixels changed (diff saved to {diff_path})"
            except Exception:
                return f"DIFFERENT: {diff_pixels} pixels changed (diff image not saved)"
    except ImportError:
        return None  # Signal to fallback to binary
    except Exception as e:
        return f"Error comparing LERC images: {e}"

def main():
    import argparse
    global DEBUG
    parser = argparse.ArgumentParser(description="Compare files between two directories. Images: pixel diff (using Pillow), CSV/SVG: text, others: binary.")
    parser.add_argument('original_dir', nargs='?', help="Original results directory")
    parser.add_argument('updated_dir', nargs='?', help="Updated results directory")
    parser.add_argument('--diff-dir', default=None, help="Directory to save difference images (default: <updated_dir>_diff)")
    parser.add_argument('--debug', action='store_true', help="Enable debug output")
    args = parser.parse_args()

    DEBUG = args.debug

    original_dir = args.original_dir
    updated_dir = args.updated_dir
    diff_dir = args.diff_dir or (updated_dir + '_diff')
    os.makedirs(diff_dir, exist_ok=True)

    updated_files = [f for f in os.listdir(updated_dir) if os.path.isfile(os.path.join(updated_dir, f))]

    print(f"Comparing {len(updated_files)} files...")
    print("=" * 80)

    identical_count = 0
    different_count = 0
    missing_count = 0
    # Main summary counts
    image_identical_count = 0  # Only non-SVG images
    image_different_count = 0  # Only non-SVG images
    svg_fully_identical = 0
    svg_partial_image_only = 0
    svg_partial_text_only = 0
    svg_fully_different = 0
    partially_identical_count = 0
    for filename in sorted(updated_files):
        original_path = os.path.join(original_dir, filename)
        updated_path = os.path.join(updated_dir, filename)
        original_type = get_file_type(original_path)
        updated_type = get_file_type(updated_path)
        # Prefer updated_type if available
        file_type = updated_type or original_type or ''
        result = None
        if file_type == 'image/png':
            result = compare_images(original_path, updated_path, diff_dir, 'png')
            if "IDENTICAL" in result:
                image_identical_count += 1
            else:
                image_different_count += 1
        elif file_type == 'image/jpeg':
            result = compare_images(original_path, updated_path, diff_dir, 'jpeg')
            if "IDENTICAL" in result:
                image_identical_count += 1
            else:
                image_different_count += 1
        elif file_type == 'image/tiff':
            result = compare_images(original_path, updated_path, diff_dir, 'tiff')
            if "IDENTICAL" in result:
                image_identical_count += 1
            else:
                image_different_count += 1
        elif file_type == 'image/lerc':
            result = compare_lerc_images(original_path, updated_path, diff_dir)
            if result is None:
                # GDAL not available, fallback to binary
                if DEBUG:
                    print(f"[DEBUG] GDAL not available, falling back to binary comparison for LERC: {original_path}, {updated_path}")
                try:
                    with open(original_path, 'rb') as f1, open(updated_path, 'rb') as f2:
                        if f1.read() == f2.read():
                            result = "IDENTICAL (binary fallback)"
                            image_identical_count += 1
                        else:
                            result = "DIFFERENT: file contents do not match (binary fallback)"
                            image_different_count += 1
                except Exception as e:
                    result = f"Error opening files as LERC or binary: {e}"
            else:
                if "IDENTICAL" in result:
                    image_identical_count += 1
                else:
                    image_different_count += 1
        elif file_type == 'text/csv' or filename.lower().endswith('.csv'):
            result = compare_text(original_path, updated_path)
        elif file_type == 'image/svg+xml' or filename.lower().endswith('.svg'):
            result = compare_svg(original_path, updated_path, diff_dir)
            # Parse SVG result for summary counts
            text_identical = False
            image_identical = False
            text_different = False
            image_different = False
            for line in result.splitlines():
                if line.startswith('SVG text: IDENTICAL'):
                    text_identical = True
                if line.startswith('SVG text: DIFFERENT'):
                    text_different = True
                if line.startswith('SVG image: IDENTICAL'):
                    image_identical = True
                if line.startswith('SVG image: DIFFERENT'):
                    image_different = True
            if text_identical and image_identical:
                print(f"✓ {filename}: SVG text and image identical")
                svg_fully_identical += 1
            elif text_identical and not image_identical:
                print(f"~ {filename}: SVG text identical, image different")
                svg_partial_text_only += 1
            elif image_identical and not text_identical:
                print(f"~ {filename}: SVG image identical, text different")
                svg_partial_image_only += 1
            elif text_different and image_different:
                print(f"Δ {filename}: SVG text and image different")
                svg_fully_different += 1
            continue
        elif file_type.startswith('text/'):
            result = compare_text(original_path, updated_path)
        else:
            # Fallback: binary compare
            if not os.path.exists(original_path):
                result = f"ORIGINAL file missing: {original_path}"
            elif not os.path.exists(updated_path):
                result = f"UPDATED file missing: {updated_path}"
            else:
                with open(original_path, 'rb') as f1, open(updated_path, 'rb') as f2:
                    if f1.read() == f2.read():
                        result = "IDENTICAL"
                    else:
                        result = "DIFFERENT: file contents do not match"
        if "IDENTICAL" in result:
            print(f"✓ {filename}: {result}")
            identical_count += 1
        elif "missing" in result.lower():
            print(f"✗ {filename}: {result}")
            missing_count += 1
        else:
            print(f"Δ {filename}: {result}")
            different_count += 1

    # Calculate summary counts
    total_svg = svg_fully_identical + svg_partial_image_only + svg_partial_text_only + svg_fully_different
    identical_count = image_identical_count + svg_fully_identical
    partially_identical_count = svg_partial_image_only + svg_partial_text_only
    different_count = image_different_count + svg_fully_different
    total_comparisons = len(updated_files)

    print("=" * 80)
    print(f"Summary:")
    print(f"  Identical: {identical_count} ({image_identical_count} images, {svg_fully_identical} SVGs)")
    print(f"  Partially Identical: {partially_identical_count} ({svg_partial_image_only} SVGs image only, {svg_partial_text_only} SVGs text only)")
    print(f"  Different: {different_count} ({image_different_count} images, {svg_fully_different} SVGs)")
    print(f"  Missing: {missing_count}")
    print(f"  Total comparisons: {total_comparisons}")

    if different_count > 0:
        print(f"\nDifference images saved to: {diff_dir}")

if __name__ == "__main__":
    main() 