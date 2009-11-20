#!/usr/bin/python
#
# CDDL HEADER START
#
# The contents of this file are subject to the terms of the
# Common Development and Distribution License (the "License").
# You may not use this file except in compliance with the License.
#
# You can obtain a copy of the license at usr/src/OPENSOLARIS.LICENSE
# or http://www.opensolaris.org/os/licensing.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# When distributing Covered Code, include this CDDL HEADER in each
# file and include the License file at usr/src/OPENSOLARIS.LICENSE.
# If applicable, add the following below this CDDL HEADER, with the
# fields enclosed by brackets "[]" replaced with your own identifying
# information: Portions Copyright [yyyy] [name of copyright owner]
#
# CDDL HEADER END
#

# Copyright 2009 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.

import testutils
if __name__ == "__main__":
        testutils.setup_environment("../../../proto")

import errno
import os
import sys
import shutil
import tempfile
import unittest

import pkg.file_layout.file_manager as file_manager
import pkg.file_layout.layout as layout

path_to_pub_util = "../util/publish"

class TestFileManager(testutils.CliTestCase):

        def setUp(self):
                self.pid = os.getpid()
                self.pwd = os.getcwd()

                self.__base_test_dir = os.path.join(tempfile.gettempdir(),
                    "ips.test.%d" % self.pid)

                self.__test_dir = os.path.join(self.__base_test_dir,
                    "migrate_test")

                try:
                        os.makedirs(self.__test_dir, 0755)
                except OSError, e:
                        if e.errno != errno.EEXIST:
                                raise e

        def tearDown(self):
                shutil.rmtree(self.__base_test_dir)

        @staticmethod
        def old_hash(s):
                return os.path.join(s[0:2], s[2:8], s)

        def touch_old_file(self, s):
                p = os.path.join(self.__test_dir, self.old_hash(s))
                if not os.path.exists(os.path.dirname(p)):
                        os.makedirs(os.path.dirname(p))
                fh = open(p, "wb")
                fh.write(s)
                fh.close()
                return p

        def update_file_layout(self, dir_path, exit=0):
                """ Run the script from the util directory."""
                cmdline = "%s/update_file_layout.py %s" % (path_to_pub_util,
                    dir_path)
                self.cmdline_run(cmdline, exit=exit)

        def test_1(self):
                """ Test that pkg.migrate correctly moves files from the old
                layout to the new layout correctly."""

                hashes = ["2be802388acdf0e17c1ea0855be5d29715290d01",
                    "0338a1ee2a98c7c9cedbff6e5a4a93a88ba05b72",
                    "ff9ea25633b995eeb4c0ae896b9f7586f8effceb",
                    "ff9ea25633b995eeb4c0ae896b9f7586f8effcec",
                    "a24ba602e0f43bac4eb6223de54a003c63d9b8d9"
                ]

                old_paths = [self.touch_old_file(h) for h in hashes]

                self.update_file_layout(self.__test_dir)
                for p in old_paths:
                        if os.path.exists(p):
                                raise RuntimeError("%s should not exist" % p)
                        if os.path.exists(os.path.dirname(p)):
                                raise RuntimeError("directory %s should not "
                                    "exist")
                l = layout.get_preferred_layout()
                for h in hashes:
                        if not os.path.exists(os.path.join(self.__test_dir,
                            l.lookup(h))):
                                raise RuntimeError("file for %s is missing" % h)

                self.update_file_layout(self.__test_dir)
                for h in hashes:
                        if not os.path.exists(os.path.join(self.__test_dir,
                            l.lookup(h))):
                                raise RuntimeError("file for %s is missing" % h)

        def test_opts(self):
                """Test command options work correctly and that migrating an
                empty directory performs as expected."""

                self.update_file_layout("", exit=2)
                self.update_file_layout("%s %s" %
                    (self.__test_dir, self.__test_dir), exit=2)
                self.update_file_layout("/foo/doesntexist/", exit=2)

                empty_dir = tempfile.mkdtemp(dir=self.__test_dir)
                self.update_file_layout(empty_dir)