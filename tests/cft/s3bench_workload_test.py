#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""S3bench test workload suit."""
import logging

import pytest

from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3 import s3_test_lib
from scripts.s3_bench import s3bench

S3_TEST_OBJ = s3_test_lib.S3TestLib()


class TestWorkloadS3Bench:
    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)

    @pytest.mark.tags("TEST-19471")
    def test_19471(self):
        """S3bench Workload test"""
        bucket_name = "test-bucket"
        workloads = [
            "1Kb", "4Kb", "8Kb", "16Kb", "32Kb", "64Kb", "128Kb", "256Kb", "512Kb",
            "1Mb", "4Mb", "8Mb", "16Mb", "32Mb", "64Mb", "128Mb", "256Mb", "512Mb",
            "1Gb", "4Gb", "8Gb", "16Gb"
        ]
        resp = s3bench.setup_s3bench()
        assert (resp, resp), "Could not setup s3bench."
        for workload in workloads:
            resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name, num_clients=1,
                                   num_sample=5, obj_name_pref="loadgen_test_", obj_size=workload,
                                   skip_cleanup=False, duration=None, verbose=True,
                                   log_file_prefix="TEST-19471")
            self.log.info(f"json_resp {resp[0]}\n Log Path {resp[1]}")
            assert not s3bench.check_log_file_error(resp[1],
                                                    ["with error ", "panic", "status code"]), \
                f"S3bench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"