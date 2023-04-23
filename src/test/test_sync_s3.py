#!/usr/bin/env python3

#
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

#
# Tests for oe_sync_s3_configs.py and oe_sync_s3_idx.py
#

import os
from subprocess import run
import subprocess
import sys
import unittest2 as unittest
import xmlrunner
from oe_test_utils import run_command
from optparse import OptionParser
from filecmp import dircmp
import boto3, botocore
import shutil
import time

TEST_BUCKET = "test_bucket"
TEST_FILES_DIR = "sync_s3_test_files/dirs_to_sync"
SYNC_DIR = "sync_s3_test_files/sync_files"
MOCK_DIR = "sync_s3_test_files/mock_s3"
MOCK_S3_URI = "http://localhost:5000"
client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
            endpoint_url=MOCK_S3_URI
            )

def upload_files(upload_dir):
    # "upload" files to mock s3
    fixtures_paths = [
        os.path.join(path,  filename)
        for path, _, files in os.walk(upload_dir)
        for filename in files
    ]
    for path in fixtures_paths:
        key = '/' + os.path.relpath(path, upload_dir)
        client.upload_file(Filename=path, Bucket=TEST_BUCKET, Key=key)

def clear_bucket(delete_bucket=False):
    s3 = boto3.resource(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        endpoint_url=MOCK_S3_URI
        )
    bucket = s3.Bucket(TEST_BUCKET)
    for key in bucket.objects.all():
        key.delete()
    if delete_bucket:
        bucket.delete()

def compare_directories(sync_dir_path, mock_dir_path, sync_script, check_diff_files=False):

    def compare_recursive(dir1, dir2):
        result_comp = dircmp(dir1, dir2)
        left_only = result_comp.left_only
        right_only = result_comp.right_only
        diff_files = result_comp.diff_files
        for common_dir in result_comp.common_dirs:
            new_dir1 = os.path.join(dir1, common_dir)
            new_dir2 = os.path.join(dir2, common_dir)
            sub_left_only, sub_right_only, sub_diff_files = compare_recursive(new_dir1, new_dir2)
            left_only.extend(sub_left_only)
            right_only.extend(sub_right_only)
            diff_files.extend(sub_diff_files)
        return left_only, right_only, diff_files

    left_only, right_only, diff_files = compare_recursive(sync_dir_path, mock_dir_path)
    success = True
    failure_msg = ""
    if len(left_only) > 0:
        success = False
        failure_msg += "\n{0} failed to delete the following file(s) from {1} that weren't in the S3 bucket:".format(sync_script, sync_dir_path)
        for filename in left_only:
            failure_msg += "\n- {0}".format(filename)
    if len(right_only) > 0:
        success = False
        failure_msg += "\n{0} failed to download the following file(s) from the S3 bucket to {1}:".format(sync_script, sync_dir_path)
        for filename in right_only:
            failure_msg += "\n- {0}".format(filename)
    if check_diff_files and len(diff_files) > 0:
        success = False
        failure_msg += "\n{0} failed to overwrite the following file(s) in {1} with files from the S3 bucket:".format(sync_script, sync_dir_path)
        for filename in diff_files:
            failure_msg += "\n- {0}".format(filename)
    return success, failure_msg

class TestSyncS3(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.sync_dir_path = os.path.join(os.getcwd(), SYNC_DIR)
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        # Start moto_server. Not using `run_command()` here because moto_server hangs when `universal_newlines=True`
        cmd = "moto_server s3 -p 5000"
        moto_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)
        # set up mock s3 bucket
        try:
            s3 = boto3.resource(
                "s3",
                region_name="us-east-1",
                aws_access_key_id="testing",
                aws_secret_access_key="testing",
                endpoint_url=MOCK_S3_URI
                )
            s3.meta.client.head_bucket(Bucket=TEST_BUCKET)
        except botocore.exceptions.ClientError:
            pass
        else:
            err = "{bucket} should not exist.".format(bucket=TEST_BUCKET)
            raise EnvironmentError(err)
        client.create_bucket(Bucket=TEST_BUCKET)

        # create directory to test syncing with
        os.mkdir(self.sync_dir_path)      
    
    # Test syncing an empty directory with an S3 bucket containing configs.
    # Passes if the configs are downloaded.
    def test_sync_configs_download_to_empty(self):
        mock_dir_name = "test_configs"
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_s3_configs.py")
        self.assertTrue(success, failure_msg)

    # Test syncing a directory of configs with an S3 bucket containing some configs
    # that the directory lacks.
    # Passes if the directory's missing configs are downloaded.
    def test_sync_configs_download(self):
        test_dir_name = "test_configs_download"
        mock_dir_name = "test_configs"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        for filename in os.listdir(test_dir_path):
            shutil.copy2(os.path.join(test_dir_path, filename), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_s3_configs.py")
        self.assertTrue(success, failure_msg)
    
    # Test syncing a directory of configs with an S3 bucket that doesn't contain
    # some of the configs in the directory.
    # Passes if the directory's extra configs are deleted.
    def test_sync_configs_delete(self):
        test_dir_name = "test_configs_delete"
        mock_dir_name = "test_configs"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        for filename in os.listdir(test_dir_path):
            shutil.copy2(os.path.join(test_dir_path, filename), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_s3_configs.py")
        self.assertTrue(success, failure_msg)

    # Test syncing a directory of configs with an S3 bucket containing some configs
    # that the directory lacks and not containing other configs that the directory has.
    # Passes if the directory's missing configs are downloaded and its extra configs are deleted.
    def test_sync_configs_download_delete(self):
        test_dir_name = "test_configs_download_delete"
        mock_dir_name = "test_configs"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        for filename in os.listdir(test_dir_path):
            shutil.copy2(os.path.join(test_dir_path, filename), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_s3_configs.py")
        self.assertTrue(success, failure_msg)
    
    # Test using the `-n` argument to perform a "dry run" of the S3 syncing without
    # actually downloading or deleting any config files from the directory.
    # Passes if the directory remains unchanged after the command is run.
    def test_sync_configs_dry_run(self):
        test_dir_name = "test_configs_download_delete"
        mock_dir_name = "test_configs"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        for filename in os.listdir(test_dir_path):
            shutil.copy2(os.path.join(test_dir_path, filename), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py -n -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        # this time ensure that the directory's contents haven't changed
        success, _ = compare_directories(self.sync_dir_path, test_dir_path, "oe_sync_s3_configs.py")
        failure_msg = "{0} has been altered. The directory should not be altered when -n (or --dry-run) are used when running oe_sync_s3_configs.py.".format(self.sync_dir_path)
        self.assertTrue(success, failure_msg)
    
    # Test syncing a directory of configs with an S3 bucket such that the directory's configs
    # are overwritten by the configs in the S3 bucket.
    # Passes if the contents of the directory's configs match those of the configs in the S3 bucket.
    def test_sync_configs_force(self):
        test_dir_name = "test_configs_force"
        mock_dir_name = "test_configs"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        for filename in os.listdir(test_dir_path):
            shutil.copy2(os.path.join(test_dir_path, filename), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py -f -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_s3_configs.py", check_diff_files=True)
        self.assertTrue(success, failure_msg)
    
    # Test syncing an empty directory with an S3 bucket containing idx files.
    # Passes if the idx files are downloaded.
    def test_sync_idx_download_to_empty(self):
        mock_dir_name = "test_idx"
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_idx.py")
        self.assertTrue(success, failure_msg)
    
    # Test syncing a directory with an S3 bucket containing some idx files
    # that already exist in the directory and some that do not.
    # Passes if the missing idx files are downloaded.
    def test_sync_idx_download(self):
        test_dir_name = "test_idx_download"
        mock_dir_name = "test_idx"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        shutil.rmtree(self.sync_dir_path)
        shutil.copytree(os.path.join(test_dir_path), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_idx.py")
        self.assertTrue(success, failure_msg)
    
    # Test syncing a directory of IDX files with an S3 bucket that doesn't contain
    # some of the IDX files in the directory.
    # Passes if the directory's extra IDX files are deleted.
    def test_sync_idx_delete(self):
        test_dir_name = "test_idx_delete"
        mock_dir_name = "test_idx"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        shutil.rmtree(self.sync_dir_path)
        shutil.copytree(os.path.join(test_dir_path), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_idx.py")
        self.assertTrue(success, failure_msg)
    
    # Test syncing a directory of IDX files with an S3 bucket containing some IDX files
    # that the directory lacks and not containing other IDX files that the directory has.
    # Passes if the directory's missing IDX files are downloaded and its extra IDX files are deleted.
    def test_sync_idx_download_delete(self):
        test_dir_name = "test_idx_download_delete"
        mock_dir_name = "test_idx"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        shutil.rmtree(self.sync_dir_path)
        shutil.copytree(os.path.join(test_dir_path), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_idx.py")
        self.assertTrue(success, failure_msg)

    # Test using the `-n` argument to perform a "dry run" of the S3 syncing without
    # actually downloading or deleting any IDX files from the directory.
    # Passes if the directory remains unchanged.
    def test_sync_idx_dry_run(self):
        test_dir_name = "test_idx_download_delete"
        mock_dir_name = "test_idx"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        shutil.rmtree(self.sync_dir_path)
        shutil.copytree(os.path.join(test_dir_path), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py -n -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        # this time ensure that the directory's contents haven't changed
        success, _ = compare_directories(self.sync_dir_path, test_dir_path, "oe_sync_s3_idx.py")
        failure_msg = "{0} has been altered. The directory should not be altered when -n (or --dry-run) are used when running oe_sync_s3_idx.py.".format(self.sync_dir_path)
        self.assertTrue(success, failure_msg)
    
    # Test syncing a directory of IDX files with an S3 bucket such that the directory's IDX files
    # are overwritten by the IDX files in the S3 bucket using `-f` (`--force`).
    # For this case, the filenames in sync_s3_files/dirs_to_sync/test_idx_force all match the filenames
    # of the files in the S3 bucket (sync_s3_files/mock_s3/test_idx), however, all of the file contents are
    # really just copies of the contents of SMAP_Brightness_Temp-2021194000000.idx.
    # These files should be overwritten with their correct contents after syncing with the S3 bucket.
    # Passes if the contents of the directory's files matches the contents of the files in the S3 bucket.
    def test_sync_idx_force(self):
        test_dir_name = "test_idx_force"
        mock_dir_name = "test_idx"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        shutil.rmtree(self.sync_dir_path)
        shutil.copytree(os.path.join(test_dir_path), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py -f -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_s3_idx.py", check_diff_files=True)
        self.assertTrue(success, failure_msg)

    # Test syncing a directory of IDX files with an S3 bucket such that the directory's IDX files
    # that share the same name as files in the S3 bucket but have unique contents (i.e. checksum mismatch)
    # are overwritten by the IDX files in the S3 bucket using `-c` (`--checksum`).
    # For this case, the filenames in sync_s3_files/dirs_to_sync/test_idx_force all match the filenames
    # of the files in the S3 bucket (sync_s3_files/mock_s3/test_idx), however, the contents of the files
    # in espg4326/AMSUA_NOAA16_Brightness_Temp_Channel_1/2001 are really just copies of the contents
    # of SMAP_Brightness_Temp-2021194000000.idx.
    # These files should be overwritten with their correct contents after syncing with the S3 bucket.
    # Passes if the contents of the directory's files matches the contents of the files in the S3 bucket.
    def test_sync_idx_checksum(self):
        test_dir_name = "test_idx_checksum"
        mock_dir_name = "test_idx"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        shutil.rmtree(self.sync_dir_path)
        shutil.copytree(os.path.join(test_dir_path), self.sync_dir_path)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py -c -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success, failure_msg = compare_directories(self.sync_dir_path, mock_dir_path, "oe_sync_idx.py", check_diff_files=True)
        self.assertTrue(success, failure_msg)

    """
    # Test syncing a directory of configs with an empty S3 bucket.
    # Passes if the configs are all deleted from the directory.
    def test_sync_configs_delete_all(self):
        test_dir_name = "test_configs_delete"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        for filename in os.listdir(test_dir_path):
            shutil.copy2(os.path.join(test_dir_path, filename), self.sync_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_configs.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success = True
        failure_msg = "\noe_sync_s3_configs.py failed to delete the following file(s) from {0} that weren't in the S3 bucket:".format(self.sync_dir_path)
        for _, _, files in os.walk(self.sync_dir_path):
            for name in files:
                success = False
                failure_msg += "\n- {0}".format(name)
        self.assertTrue(success, failure_msg)
    """

    """
    # Test syncing a directory of IDX files with an empty S3 bucket.
    # Passes if the directory's IDX files are deleted.
    def test_sync_idx_delete_all(self):
        test_dir_name = "test_idx_delete"
        test_dir_path = os.path.join(os.getcwd(), TEST_FILES_DIR, test_dir_name)
        shutil.rmtree(self.sync_dir_path)
        shutil.copytree(os.path.join(test_dir_path), self.sync_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success = True
        failure_msg = "\noe_sync_s3_idx.py failed to delete the following file(s) from {0} that weren't in the S3 bucket:".format(self.sync_dir_path)
        for _, _, files in os.walk(self.sync_dir_path):
            for name in files:
                success = False
                failure_msg += "\n- {0}".format(name)
        self.assertTrue(success, failure_msg)
    """
    
    @classmethod
    def tearDown(self):
        clear_bucket()
        shutil.rmtree(self.sync_dir_path)
        os.mkdir(self.sync_dir_path)
    
    @classmethod
    def tearDownClass(self):
        os.rmdir(self.sync_dir_path)
        clear_bucket(True)
        
if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option(
        '-o',
        '--output',
        action='store',
        type='string',
        dest='outfile',
        default='test_sync_s3_results.xml',
        help='Specify XML output file (default is test_sync_s3_results.xml')
    parser.add_option(
        '-s',
        '--start_server',
        action='store_true',
        dest='start_server',
        help='Load test configuration into Apache and quit (for debugging)')
    (options, args) = parser.parse_args()

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestSyncS3.setUpClass()
        sys.exit(
            'Apache has been loaded with the test configuration. No tests run.'
        )

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output=f))
