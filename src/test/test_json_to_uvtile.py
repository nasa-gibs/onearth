#!/usr/bin/env python3
import argparse
import numpy as np
import os
from PIL import Image
import rasterio
import shutil
import subprocess
import sys
import unittest
import xmlrunner

def run_script(*args):
    """Run oe_json_to_uvtile script"""
    result = subprocess.run(
        [
            "python3",
            "/usr/bin/oe_json_to_uvtile",
            *args,
        ],
        capture_output=True,
        text=True,
    )
    return result


def mse(img1, img2, dtype=np.float32):
    """Compute Mean Squared Error between test and reference images."""
    arr1 = np.array(img1, dtype=dtype)
    arr2 = np.array(img2, dtype=dtype)
    return np.mean((arr1 - arr2) ** 2)


class TestUsage(unittest.TestCase):
    def test_usage(self):
        """Test with no args (should fail)."""
        result = run_script()
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage", result.stderr)


class TestOscar(unittest.TestCase):

    test_data_path = os.path.join(os.getcwd(), "vectorgen_test_data")
    # identical to test_data_path, but could be different later
    reference_data_path = os.path.join(os.getcwd(), "vectorgen_test_data")
    main_artifact_path = os.path.join(os.getcwd(), "json_uvtile_oscar_artifacts")
    tests_passed = True

    @classmethod
    def setUpClass(cls):
        oscar_input_gz = os.path.join(
            cls.test_data_path,
            "test_geojson",
            "oscar_currents_final_uv_20200101_compress.json.gz",
        )
        cls.oscar_input = os.path.join(
            cls.test_data_path,
            "test_geojson",
            "oscar_currents_final_uv_20200101_compress.json",
        )

        if not os.path.exists(cls.oscar_input) and os.path.exists(oscar_input_gz):
            # Decompress oscar geojson file before running tests
            # The file is stored compressed due to its large size (for a git repo, at least)
            unzip_result = subprocess.run(["gunzip", oscar_input_gz])
            if unzip_result.returncode != 0:
                raise RuntimeError(
                    f"unable to unzip input test file: {oscar_input_gz}, {unzip_result.stderr}"
                )
            print(f"decompressed oscar data to {cls.oscar_input}")

        os.makedirs(cls.main_artifact_path, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.oscar_input = os.path.join(
            cls.test_data_path,
            "test_geojson",
            "oscar_currents_final_uv_20200101_compress.json",
        )
        if cls.tests_passed and not SAVE_RESULTS:
            if os.path.exists(cls.oscar_input):
                subprocess.run(["gzip", "-9", cls.oscar_input])
            shutil.rmtree(cls.main_artifact_path)

    def run(self, result=None):
        """Override run method to track test failures."""
        result = super().run(result)
        if not result.wasSuccessful():
            self.__class__.tests_passed = False  # Mark as failed
        return result

    def test_simple(self):
        """Test running oe_json_to_uvtile with only the input argument.
        All further tests exercise the -o option."""
        # First test is idiosyncratic because the output is placed in the
        # test input dir (default behavior without -o)
        artifact_path = os.path.join(
            self.test_data_path,
            "test_geojson",
            "oscar_currents_final_uv_20200101_compress.png",
        )

        oscar_result = run_script(self.oscar_input)
        self.assertEqual(
            oscar_result.returncode,
            0,
            f"command retcode = {oscar_result.returncode}: {oscar_result.stderr}",
        )
        self.assertEqual(
            os.path.exists(artifact_path),
            True,
            f"output file not found: {artifact_path}",
        )
        # clean up the artifact from the test input directory
        os.remove(artifact_path)

    def test_oscar_out(self):
        """Test oscar input with --output argument, comparing images this time."""
        artifact_path = os.path.join(
            self.main_artifact_path,
            "oscar_currents_final_uv_20200101.png",
        )
        reference_path = os.path.join(self.reference_data_path, "test_oscar.png")
        oscar_result = run_script(self.oscar_input, "-o", artifact_path)
        self.assertEqual(
            oscar_result.returncode,
            0,
            f"command retcode = {oscar_result.returncode}: {oscar_result.stderr}",
        )
        self.assertEqual(
            os.path.exists(artifact_path),
            True,
            f"output file not found: {artifact_path}",
        )
        imgtest = Image.open(artifact_path).convert("RGB")
        imgref = Image.open(reference_path).convert("RGB")
        self.assertEqual(
            imgtest.size,
            imgref.size,
            f"image dimensions do not match: {imgtest.size} (test), {imgref.size} (ref)",
        )
        # Compare rasters with MSE because compression reduces precision of input geojson
        error = mse(imgtest, imgref, dtype=np.uint8)
        self.assertLess(
            error, 0.01, f"test image is too different from reference, MSE: {error}"
        )

    def test_resolution_override(self):
        """Test using the --resolution option."""
        artifact_path = os.path.join(
            self.main_artifact_path, "oscar_currents_final_uv_20200101_res_override.png"
        )
        # You can pick any resolution override you like; 1.0 is often easy to see if it changes.
        # This test primarily ensures that the script runs without error using --resolution
        oscar_result = run_script(
            self.oscar_input,
            "-o",
            artifact_path,
            "--resolution",
            "1.0",
        )
        self.assertEqual(
            oscar_result.returncode,
            0,
            f"command retcode = {oscar_result.returncode}: {oscar_result.stderr}",
        )
        self.assertTrue(
            os.path.exists(artifact_path),
            f"output file not found: {artifact_path}",
        )

    def test_tiff_format(self):
        """Test generating a TIFF (32-bit float) by using --format tiff."""
        artifact_path = os.path.join(
            self.main_artifact_path,
            "oscar_currents_final_uv_20200101_float.tif",
        )
        oscar_result = run_script(
            self.oscar_input,
            "-o",
            artifact_path,
            "--format",
            "tiff",
        )
        self.assertEqual(
            oscar_result.returncode,
            0,
            f"command retcode = {oscar_result.returncode}: {oscar_result.stderr}",
        )
        self.assertTrue(
            os.path.exists(artifact_path),
            f"output TIFF file not found: {artifact_path}",
        )
        # Load the TIFF and see if it has a float dtype
        # Pillow does not support this type of floating point tiff
        with rasterio.open(artifact_path) as img:
            float_array = img.read(1)
        self.assertIn(
            float_array.dtype,
            ("float", "float32", "float64"),
            f"Expected a float dtype for TIFF, got {float_array.dtype}",
        )

    def test_invalid_format(self):
        """Test passing an invalid --format to ensure it fails."""
        # This should fail with returncode=2 and show usage or an error message
        oscar_result = run_script(
            self.oscar_input,
            "--format",
            "abc123",  # invalid
        )
        self.assertEqual(
            oscar_result.returncode,
            2,
            f"command retcode = {oscar_result.returncode}, expected 2 for invalid format",
        )
        self.assertIn("error", oscar_result.stderr.lower())
        self.assertIn("usage", oscar_result.stderr.lower())


if __name__ == "__main__":
    # Parse options before running tests
    parser = argparse.ArgumentParser()
    xml_fname = "test_json_to_uvtile_results.xml"
    parser.add_argument("--output", metavar="FILE", default=xml_fname,
                      help=f"Specify XML output file (default is {xml_fname})")
    parser.add_argument("--save-results", action="store_true", help="Save test artifacts in staging area")
    args, unittest_args = parser.parse_known_args()

    SAVE_RESULTS = args.save_results
    with open(xml_fname, "wb") as f:
        unittest.main(argv=[sys.argv[0]] + unittest_args, testRunner=xmlrunner.XMLTestRunner(output=f))
