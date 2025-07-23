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
Tests for image_compare.py.
"""

import os
import shutil
import tempfile
import unittest
import subprocess
import xmlrunner
from PIL import Image

IMAGE_COMPARE_PATH = "/usr/bin/image_compare.py"
DEBUG = False

class TestImageCompareScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp()
        cls.diff_dir = os.path.join(cls.test_dir, 'diff')
        os.makedirs(cls.diff_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir)

    @staticmethod
    def create_image(path, color, size=(10, 10), fmt='PNG'):
        mode = 'RGB' if fmt.upper() == 'JPEG' else 'RGBA'
        img = Image.new(mode, size, color)
        img.save(path, format=fmt)

    @staticmethod
    def create_text_file(path, content):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    @staticmethod
    def create_binary_file(path, content):
        with open(path, 'wb') as f:
            f.write(content)

    def run_image_compare(self, orig_dir, upd_dir, diff_dir=None):
        args = ["python3", IMAGE_COMPARE_PATH, orig_dir, upd_dir]
        if diff_dir:
            args += ["--diff-dir", diff_dir]
        result = subprocess.run(args, capture_output=True, text=True)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        print("RETURNCODE:", result.returncode)
        if result.returncode != 0:
            print(f"[ERROR] image_compare.py exited with code {result.returncode}")
        return result
    
    def test_identical_png(self):
        orig_dir = os.path.join(self.test_dir, 'orig_png')
        upd_dir = os.path.join(self.test_dir, 'upd_png')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.png')
        upd_file = os.path.join(upd_dir, 'test.png')
        self.create_image(orig_file, 'red')
        shutil.copy(orig_file, upd_file)
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        self.assertIn('IDENTICAL', result.stdout)
    
    def test_different_png(self):
        orig_dir = os.path.join(self.test_dir, 'orig_png2')
        upd_dir = os.path.join(self.test_dir, 'upd_png2')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.png')
        upd_file = os.path.join(upd_dir, 'test.png')
        self.create_image(orig_file, 'red')
        self.create_image(upd_file, 'blue')
        # Debug: check that files are actually different
        with open(orig_file, 'rb') as f1, open(upd_file, 'rb') as f2:
            orig_bytes = f1.read()
            upd_bytes = f2.read()
            assert orig_bytes != upd_bytes, "Test setup error: PNG files are not different!"
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        self.assertIn('DIFFERENT', result.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.diff_dir, f'diff_{os.path.basename(orig_file)}')))
    
    def test_identical_jpeg(self):
        orig_dir = os.path.join(self.test_dir, 'orig_jpeg')
        upd_dir = os.path.join(self.test_dir, 'upd_jpeg')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.jpg')
        upd_file = os.path.join(upd_dir, 'test.jpg')
        self.create_image(orig_file, 'red', fmt='JPEG')
        shutil.copy(orig_file, upd_file)
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        self.assertIn('IDENTICAL', result.stdout)

    def test_different_jpeg(self):
        orig_dir = os.path.join(self.test_dir, 'orig_jpeg2')
        upd_dir = os.path.join(self.test_dir, 'upd_jpeg2')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.jpg')
        upd_file = os.path.join(upd_dir, 'test.jpg')
        self.create_image(orig_file, 'red', fmt='JPEG')
        self.create_image(upd_file, 'blue', fmt='JPEG')
        with open(orig_file, 'rb') as f1, open(upd_file, 'rb') as f2:
            orig_bytes = f1.read()
            upd_bytes = f2.read()
            assert orig_bytes != upd_bytes, "Test setup error: JPEG files are not different!"
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        self.assertIn('DIFFERENT', result.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.diff_dir, f'diff_{os.path.basename(orig_file)}')))

    def test_identical_tiff(self):
        orig_dir = os.path.join(self.test_dir, 'orig_tiff')
        upd_dir = os.path.join(self.test_dir, 'upd_tiff')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.tif')
        upd_file = os.path.join(upd_dir, 'test.tif')
        self.create_image(orig_file, 'red', fmt='TIFF')
        shutil.copy(orig_file, upd_file)
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        self.assertIn('IDENTICAL', result.stdout)

    def test_different_tiff(self):
        orig_dir = os.path.join(self.test_dir, 'orig_tiff2')
        upd_dir = os.path.join(self.test_dir, 'upd_tiff2')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.tif')
        upd_file = os.path.join(upd_dir, 'test.tif')
        self.create_image(orig_file, 'red', fmt='TIFF')
        self.create_image(upd_file, 'blue', fmt='TIFF')
        with open(orig_file, 'rb') as f1, open(upd_file, 'rb') as f2:
            orig_bytes = f1.read()
            upd_bytes = f2.read()
            assert orig_bytes != upd_bytes, "Test setup error: TIFF files are not different!"
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        self.assertIn('DIFFERENT', result.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.diff_dir, f'diff_{os.path.basename(orig_file)}')))

    def test_text_compare_identical(self):
        orig_dir = os.path.join(self.test_dir, 'orig_txt')
        upd_dir = os.path.join(self.test_dir, 'upd_txt')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.txt')
        upd_file = os.path.join(upd_dir, 'test.txt')
        self.create_text_file(orig_file, 'hello world')
        self.create_text_file(upd_file, 'hello world')
        result = self.run_image_compare(orig_dir, upd_dir)
        self.assertIn('IDENTICAL', result.stdout)

    def test_text_compare_different(self):
        orig_dir = os.path.join(self.test_dir, 'orig_txt2')
        upd_dir = os.path.join(self.test_dir, 'upd_txt2')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.txt')
        upd_file = os.path.join(upd_dir, 'test.txt')
        self.create_text_file(orig_file, 'hello world')
        self.create_text_file(upd_file, 'goodbye world')
        result = self.run_image_compare(orig_dir, upd_dir)
        self.assertIn('DIFFERENT', result.stdout)

    def test_binary_compare_identical(self):
        orig_dir = os.path.join(self.test_dir, 'orig_bin')
        upd_dir = os.path.join(self.test_dir, 'upd_bin')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.bin')
        upd_file = os.path.join(upd_dir, 'test.bin')
        self.create_binary_file(orig_file, b'\x00\x01\x02')
        self.create_binary_file(upd_file, b'\x00\x01\x02')
        result = self.run_image_compare(orig_dir, upd_dir)
        self.assertIn('IDENTICAL', result.stdout)

    def test_binary_compare_different(self):
        orig_dir = os.path.join(self.test_dir, 'orig_bin2')
        upd_dir = os.path.join(self.test_dir, 'upd_bin2')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.bin')
        upd_file = os.path.join(upd_dir, 'test.bin')
        self.create_binary_file(orig_file, b'\x00\x01\x02')
        self.create_binary_file(upd_file, b'\x00\x01\x03')
        result = self.run_image_compare(orig_dir, upd_dir)
        self.assertIn('DIFFERENT', result.stdout)

    def test_corrupt_image_fallback(self):
        orig_dir = os.path.join(self.test_dir, 'orig_corrupt')
        upd_dir = os.path.join(self.test_dir, 'upd_corrupt')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.png')
        upd_file = os.path.join(upd_dir, 'test.png')
        # Use valid UTF-8 text so fallback is text and files are identical
        self.create_text_file(orig_file, 'identical text')
        self.create_text_file(upd_file, 'identical text')
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        self.assertIn('IDENTICAL (text)', result.stdout)

    def test_corrupt_image_fallback_different(self):
        orig_dir = os.path.join(self.test_dir, 'orig_corrupt2')
        upd_dir = os.path.join(self.test_dir, 'upd_corrupt2')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.png')
        upd_file = os.path.join(upd_dir, 'test.png')
        # Use valid but different UTF-8 text so fallback is text and files are different
        self.create_text_file(orig_file, 'text one')
        self.create_text_file(upd_file, 'text two')
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        self.assertIn('DIFFERENT: text contents do not match (fallback)', result.stdout)

    def test_corrupt_image_fallback_binary_identical(self):
        orig_dir = os.path.join(self.test_dir, 'orig_corrupt_bin')
        upd_dir = os.path.join(self.test_dir, 'upd_corrupt_bin')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.png')
        upd_file = os.path.join(upd_dir, 'test.png')
        # Use non-UTF-8 binary data so fallback is binary and files are identical
        self.create_binary_file(orig_file, b'\xff\xfe\xfd')
        self.create_binary_file(upd_file, b'\xff\xfe\xfd')
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        self.assertIn('IDENTICAL (binary)', result.stdout)

    def test_corrupt_image_fallback_binary_different(self):
        orig_dir = os.path.join(self.test_dir, 'orig_corrupt_bin2')
        upd_dir = os.path.join(self.test_dir, 'upd_corrupt_bin2')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.png')
        upd_file = os.path.join(upd_dir, 'test.png')
        # Use non-UTF-8 binary data so fallback is binary and files are different
        self.create_binary_file(orig_file, b'\xff\xfe\xfd')
        self.create_binary_file(upd_file, b'\x00\x01\x02')
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        self.assertIn('DIFFERENT: file contents do not match (binary fallback)', result.stdout)

    def test_svg_identical(self):
        orig_dir = os.path.join(self.test_dir, 'orig_svg')
        upd_dir = os.path.join(self.test_dir, 'upd_svg')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.svg')
        upd_file = os.path.join(upd_dir, 'test.svg')
        svg_content = '<svg width="10" height="10" xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10" fill="red"/></svg>'
        self.create_text_file(orig_file, svg_content)
        self.create_text_file(upd_file, svg_content)
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        # Should report identical for both text and image in the summary line
        self.assertIn('✓ test.svg: SVG text and image identical', result.stdout)

    def test_svg_different(self):
        orig_dir = os.path.join(self.test_dir, 'orig_svg2')
        upd_dir = os.path.join(self.test_dir, 'upd_svg2')
        os.makedirs(orig_dir, exist_ok=True)
        os.makedirs(upd_dir, exist_ok=True)
        orig_file = os.path.join(orig_dir, 'test.svg')
        upd_file = os.path.join(upd_dir, 'test.svg')
        svg_red = '<svg width="10" height="10" xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10" fill="red"/></svg>'
        svg_blue = '<svg width="10" height="10" xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10" fill="blue"/></svg>'
        self.create_text_file(orig_file, svg_red)
        self.create_text_file(upd_file, svg_blue)
        result = self.run_image_compare(orig_dir, upd_dir, self.diff_dir)
        # Should report different for both text and image in the summary line
        self.assertIn('Δ test.svg: SVG text and image different', result.stdout)

if __name__ == '__main__':
    import sys
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_image_compare_results.xml',
                      help='Specify XML output file (default is test_image_compare_results.xml)')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Output verbose debugging messages')
    (options, args) = parser.parse_args()

    DEBUG = options.debug

    # Remove extra args so unittest doesn't get confused
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print(f'\nStoring test results in "{options.outfile}"')
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f),
            verbosity=2
        ) 