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

def get_file_type(path):
    """Detect the actual file type using the file extension."""
    if not os.path.exists(path):
        return None
    ext = os.path.splitext(path)[1].lower()
    if ext == '.png':
        return 'image/png'
    elif ext in ('.jpg', '.jpeg'):
        return 'image/jpeg'
    elif ext in ('.tif', '.tiff'):
        return 'image/tiff'
    elif ext == '.csv':
        return 'text/csv'
    elif ext == '.svg':
        return 'image/svg+xml'
    elif ext in ('.txt', '.md', '.py', '.json', '.xml', '.yaml', '.yml'):
        return 'text/' + ext[1:]
    else:
        return ''

def compare_images(original_path, updated_path, diff_dir, ext):
    """Compare two images using Pillow. ext should be 'png', 'jpeg', or 'tiff'.
    If image open fails, try text compare, then binary compare."""
    if not os.path.exists(original_path):
        return f"ORIGINAL file missing: {original_path}"
    if not os.path.exists(updated_path):
        return f"UPDATED file missing: {updated_path}"
    try:
        img1 = Image.open(original_path).convert('RGBA')
        img2 = Image.open(updated_path).convert('RGBA')
    except Exception as e:
        print(f"[WARN] Could not open as image: {original_path} or {updated_path}: {e}")
        # Try text compare
        try:
            with open(original_path, 'r', encoding='utf-8') as f1, open(updated_path, 'r', encoding='utf-8') as f2:
                original_content = f1.read()
                updated_content = f2.read()
                if original_content == updated_content:
                    return "IDENTICAL (text)"
                else:
                    return "DIFFERENT: text contents do not match (fallback)"
        except Exception as text_e:
            print(f"[WARN] Could not open as text: {original_path} or {updated_path}: {text_e}")
            # Fallback: binary compare
            try:
                with open(original_path, 'rb') as f1, open(updated_path, 'rb') as f2:
                    if f1.read() == f2.read():
                        return "IDENTICAL (binary)"
                    else:
                        return "DIFFERENT: file contents do not match (binary fallback)"
            except Exception as bin_e:
                return f"Error opening files as image, text, or binary: {bin_e}"
    if img1.size != img2.size:
        return f"Different dimensions: ORIGINAL={img1.size}, UPDATED={img2.size}"
    diff = ImageChops.difference(img1, img2)
    bbox = diff.getbbox()
    if bbox is None:
        return "IDENTICAL"
    else:
        # Count nonzero pixels (any channel difference)
        diff_pixels = sum(1 for pixel in diff.getdata() if pixel[:3] != (0, 0, 0))
        diff_path = os.path.join(diff_dir, f"diff_{os.path.basename(original_path)}")
        # Enhance diff for visibility (optional: multiply difference)
        enhanced_diff = diff.copy()
        enhanced_diff = enhanced_diff.convert('RGB')
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

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compare files between two directories. Images: pixel diff (using Pillow), CSV/SVG: text, others: binary.")
    parser.add_argument('original_dir', nargs='?', help="Original results directory")
    parser.add_argument('updated_dir', nargs='?', help="Updated results directory")
    parser.add_argument('--diff-dir', default=None, help="Directory to save difference images (default: <updated_dir>_diff)")
    args = parser.parse_args()

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
        elif file_type == 'image/jpeg':
            result = compare_images(original_path, updated_path, diff_dir, 'jpeg')
        elif file_type == 'image/tiff':
            result = compare_images(original_path, updated_path, diff_dir, 'tiff')
        elif file_type == 'text/csv' or filename.lower().endswith('.csv'):
            result = compare_text(original_path, updated_path)
        elif file_type == 'image/svg+xml' or filename.lower().endswith('.svg'):
            result = compare_text(original_path, updated_path)
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

    print("=" * 80)
    print(f"Summary:")
    print(f"  Identical: {identical_count}")
    print(f"  Different: {different_count}")
    print(f"  Missing: {missing_count}")
    print(f"  Total: {len(updated_files)}")

    if different_count > 0:
        print(f"\nDifference images saved to: {diff_dir}")

if __name__ == "__main__":
    main() 