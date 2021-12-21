#!/usr/bin/env python3

# Copyright (c) 2002-2016, California Institute of Technology.
# All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#   1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#   2. Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#   3. Neither the name of the California Institute of Technology (Caltech), its operating division the Jet Propulsion Laboratory (JPL),
#      the National Aeronautics and Space Administration (NASA), nor the names of its contributors may be used to
#      endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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

def compare_directories(sync_dir_path, mock_dir_path, sync_script):
    result_comp = dircmp(sync_dir_path, mock_dir_path)
    success = True
    failure_msg = ""
    if len(result_comp.left_only) > 0:
        success = False
        failure_msg += "\n{0} failed to delete the following file(s) from {1} that weren't in the S3 bucket:".format(sync_script, sync_dir_path)
        for filename in result_comp.left_only:
            failure_msg += "\n- {0}".format(filename)
    if len(result_comp.right_only) > 0:
        success = False
        failure_msg += "\n{0} failed to download the following file(s) from the S3 bucket to {1}:".format(sync_script, sync_dir_path)
        for filename in result_comp.right_only:
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
    
    # Test syncing a directory of configs with an S3 bucket containing some configs
    # that the directory lacks.
    # Passes if the configs are downloaded.
    def test_sync_configs_download(self):
        mock_dir_name = "test_configs"
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
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
    # actually downloading or deleting any files from the directory.
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
    
    # Test syncing a directory of configs with an S3 bucket containing some configs
    # that the directory lacks and not containing other configs that the directory has.
    # Passes if the directory's missing configs are downloaded and its extra configs are deleted.
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
        result_comp = dircmp(self.sync_dir_path, mock_dir_path)
        success = len(result_comp.same_files) == len(result_comp.right_list)
        failure_msg = "Running oe_sync_s3_configs.py with -f (--force) failed to overwrite configs in {0} that share the same name as configs in the S3 bucket.".format(self.sync_dir_path)
        self.assertTrue(success, failure_msg)
    """
    # Test syncing a directory of configs with an S3 bucket containing some idx files
    # that the directory lacks.
    # Passes if the configs are downloaded.
    def test_sync_idx_download(self):
        mock_dir_name = "test_idx"
        mock_dir_path = os.path.join(os.getcwd(), MOCK_DIR, mock_dir_name)
        upload_files(mock_dir_path)
        cmd = "python3 /home/oe2/onearth/src/scripts/oe_sync_s3_idx.py -b {0} -d {1} -s {2}".format(TEST_BUCKET, self.sync_dir_path, MOCK_S3_URI)
        run_command(cmd)
        # check results
        success = True
        failure_msg = ""
        result_comp = dircmp(self.sync_dir_path, mock_dir_path)
        print(result_comp.left_list)
        self.assertTrue(success, failure_msg)
    """
    # TODO config checksums

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
        failure_msg = ""
        remaining_files = os.listdir(self.sync_dir_path)
        if len(remaining_files) > 0:
            success = False
            failure_msg += "\noe_sync_s3_configs.py failed to delete the following file(s) from {0} that weren't in the S3 bucket:".format(self.sync_dir_path)
            for filename in remaining_files:
                failure_msg += "\n- {0}".format(filename)
        self.assertTrue(success, failure_msg)
    """
    
    @classmethod
    def tearDown(self):
        clear_bucket()
        for filename in os.listdir(self.sync_dir_path):
            os.remove(os.path.join(self.sync_dir_path, filename))
    
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
        help='Specify XML output file (default is test_mod_mrf_results.xml')
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
