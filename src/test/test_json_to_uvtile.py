#!/usr/bin/env python3
import argparse
import numpy as np
import os
from PIL import Image
import shutil
import subprocess
import unittest

SAVE_RESULT = False


def run_script(*args):
    """Run oe_json_to_uvtile script"""
    result = subprocess.run(
        [
            "python3",
            "/Users/jryan/gibs_repos/onearth/src/vectorgen/oe_json_to_uvtile.py",
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
        if cls.tests_passed:
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


if __name__ == "__main__":
    unittest.main()
