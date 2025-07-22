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
For PNG and JPEG files, compare pixel differences and create difference images.
For CSV and SVG files, compare contents exactly.
For other files, compare binary contents.
"""

import os
import subprocess
import sys
from pathlib import Path
import re

def run_command(cmd):
    """Run a command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def get_file_type(path):
    """Detect the actual file type using the 'file' command."""
    if not os.path.exists(path):
        return None
    result = run_command(f"file --mime-type -b {path}")
    if result[0] == 0:
        return result[1].strip()
    return None

def compare_images(original_path, updated_path, diff_dir, ext):
    """Compare two images using ImageMagick. ext should be 'png' or 'jpeg'."""
    if not os.path.exists(original_path):
        return f"ORIGINAL file missing: {original_path}"
    if not os.path.exists(updated_path):
        return f"UPDATED file missing: {updated_path}"
    # Get basic image info
    original_info = run_command(f"identify {original_path}")
    updated_info = run_command(f"identify {updated_path}")
    if original_info[0] != 0 or updated_info[0] != 0:
        return f"Error getting image info: {original_info[2]} {updated_info[2]}"
    # Extract dimensions from identify output (format: 'filename PNG WxH WxH+0+0 ...' or 'filename JPEG WxH ...')
    dim_match = re.compile(r'(PNG|JPEG) (\d+x\d+)')
    original_dim_match = dim_match.search(original_info[1])
    updated_dim_match = dim_match.search(updated_info[1])
    if not original_dim_match or not updated_dim_match:
        return f"Error parsing dimensions: ORIGINAL='{original_info[1]}', UPDATED='{updated_info[1]}'"
    original_dims = original_dim_match.group(2)
    updated_dims = updated_dim_match.group(2)
    if original_dims != updated_dims:
        return f"Different dimensions: ORIGINAL={original_dims}, UPDATED={updated_dims}"
    # Compare pixel differences
    diff_cmd = f"compare {original_path} {updated_path} -metric AE null:"
    diff_result = run_command(diff_cmd)
    diff_value = diff_result[2].strip()
    try:
        pixel_diff = float(diff_value)
        if pixel_diff == 0:
            return "IDENTICAL"
        else:
            diff_path = os.path.join(diff_dir, f"diff_{os.path.basename(original_path)}")
            diff_img_cmd = f"compare {original_path} {updated_path} -compose src-over {diff_path}"
            run_command(diff_img_cmd)
            return f"DIFFERENT: {pixel_diff} pixels changed (diff saved to {diff_path})"
    except ValueError:
        return f"Error parsing difference: {diff_value}"

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
    parser = argparse.ArgumentParser(description="Compare files between two directories. Images: pixel diff, CSV/SVG: text, others: binary.")
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