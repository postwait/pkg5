#!/usr/bin/python2.4
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

import unittest
import os
import sys
import copy
import re
import shutil
import difflib
import time

import pkg.client.api as api
import pkg.client.api_errors as api_errors
import pkg.client.query_parser as query_parser
import pkg.client.progress as progress
import pkg.fmri as fmri
import pkg.portable as portable
import pkg.search_storage as ss

API_VERSION = 12
PKG_CLIENT_NAME = "pkg"

class TestApiSearchBasics(testutils.SingleDepotTestCase):

        example_pkg10 = """
            open example_pkg@1.0,5.11-0
            add dir mode=0755 owner=root group=bin path=/bin
            add dir mode=0755 owner=root group=bin path=/bin/example_dir
            add dir mode=0755 owner=root group=bin path=/usr/lib/python2.4/vendor-packages/OpenSSL
            add file /tmp/example_file mode=0555 owner=root group=bin path=/bin/example_path
            add set name=com.sun.service.incorporated_changes value="6556919 6627937"
            add set name=com.sun.service.random_test value=42 value=79
            add set name=com.sun.service.bug_ids value="4641790 4725245 4817791 4851433 4897491 4913776 6178339 6556919 6627937"
            add set name=com.sun.service.keywords value="sort null -n -m -t sort 0x86 separator"
            add set name=com.sun.service.info_url value=http://service.opensolaris.com/xml/pkg/SUNWcsu@0.5.11,5.11-1:20080514I120000Z
            add set description='FOOO bAr O OO OOO'
            add set name='weirdness' value='] [ * ?'
            close """

        example_pkg11 = """
            open example_pkg@1.1,5.11-0
            add dir mode=0755 owner=root group=bin path=/bin
            add file /tmp/example_file mode=0555 owner=root group=bin path=/bin/example_path11
            close """

        another_pkg10 = """
            open another_pkg@1.0,5.11-0
            add dir mode=0755 owner=root group=bin path=/bin
            add dir mode=0755 owner=root group=bin path=/bin/another_dir
            add file /tmp/example_file mode=0555 owner=root group=bin path=/bin/another_path
            add set name=com.sun.service.incorporated_changes value="6556919 6627937"
            add set name=com.sun.service.random_test value=42 value=79
            add set name=com.sun.service.bug_ids value="4641790 4725245 4817791 4851433 4897491 4913776 6178339 6556919 6627937"
            add set name=com.sun.service.keywords value="sort null -n -m -t sort 0x86 separator"
            add set name=com.sun.service.info_url value=http://service.opensolaris.com/xml/pkg/SUNWcsu@0.5.11,5.11-1:20080514I120000Z
            close """

        bad_pkg10 = """
            open bad_pkg@1.0,5.11-0
            add dir path=foo/ mode=0755 owner=root group=bin
            add dir path=/ mode=0755 owner=root group=bin
            close """

        space_pkg10 = """
            open space_pkg@1.0,5.11-0
            add file /tmp/example_file mode=0444 owner=nobody group=sys path='unique/with a space'
            add dir mode=0755 owner=root group=bin path=unique_dir
            close """

        cat_pkg10 = """
            open cat@1.0,5.11-0
            add set name=info.classification value=org.opensolaris.category.2008:System/Security
            close """

        cat2_pkg10 = """
            open cat2@1.0,5.11-0
            add set name=info.classification value="org.opensolaris.category.2008:Applications/Sound and Video"
            close """

        cat3_pkg10 = """
            open cat3@1.0,5.11-0
            add set name=info.classification value="org.opensolaris.category.2008:foo/bar/baz/bill/beam/asda"
            close """

        bad_cat_pkg10 = """
            open badcat@1.0,5.11-0
            add set name=info.classification value="TestBad1/TestBad2"
            close """

        bad_cat2_pkg10 = """
            open badcat2@1.0,5.11-0
            add set name=info.classification value="org.opensolaris.category.2008:TestBad1:TestBad2"
            close """

        res_remote_path = set([
            ("pkg:/example_pkg@1.0-0", "basename","file 820157a2043e3135f342b238129b556aade20347 chash=bfa46fc98d1ca97f1260090797d35a35e76096a3 group=bin mode=0555 owner=root path=bin/example_path pkg.csize=38 pkg.size=18")
        ])

        res_remote_bin = set([
            ("pkg:/example_pkg@1.0-0", "path", "dir group=bin mode=0755 owner=root path=bin")
        ])

        res_remote_openssl = set([
            ("pkg:/example_pkg@1.0-0", "basename", "dir group=bin mode=0755 owner=root path=usr/lib/python2.4/vendor-packages/OpenSSL")
        ])

        res_remote_bug_id = set([
            ("pkg:/example_pkg@1.0-0", "4851433", 'set name=com.sun.service.bug_ids value="4641790 4725245 4817791 4851433 4897491 4913776 6178339 6556919 6627937"')
        ])

        res_remote_inc_changes = set([
            ("pkg:/example_pkg@1.0-0", "6556919", 'set name=com.sun.service.incorporated_changes value="6556919 6627937"'),
            ("pkg:/example_pkg@1.0-0", "6556919", 'set name=com.sun.service.bug_ids value="4641790 4725245 4817791 4851433 4897491 4913776 6178339 6556919 6627937"')
              
        ])

        res_remote_random_test = set([
            ("pkg:/example_pkg@1.0-0", "42", "set name=com.sun.service.random_test value=42 value=79")
        ])

        res_remote_keywords = set([
            ("pkg:/example_pkg@1.0-0", "separator", 'set name=com.sun.service.keywords value="sort null -n -m -t sort 0x86 separator"')
        ])

        res_remote_wildcard = res_remote_path.union(set([
            ('pkg:/example_pkg@1.0-0', 'basename', 'dir group=bin mode=0755 owner=root path=bin/example_dir')
        ]))

        headers = ""

        res_remote_glob = set([
            ('pkg:/example_pkg@1.0-0', 'path', 'dir group=bin mode=0755 owner=root path=bin/example_dir'),
            ('pkg:/example_pkg@1.0-0', 'basename', 'dir group=bin mode=0755 owner=root path=bin/example_dir'),
            ('pkg:/example_pkg@1.0-0', 'path', 'file 820157a2043e3135f342b238129b556aade20347 chash=bfa46fc98d1ca97f1260090797d35a35e76096a3 group=bin mode=0555 owner=root path=bin/example_path pkg.csize=38 pkg.size=18')
        ]) | res_remote_path
                                

        res_remote_foo = set([
            ('pkg:/example_pkg@1.0-0', 'FOOO', 'set name=description value="FOOO bAr O OO OOO"')
        ])

        res_remote_bar = set([
            ('pkg:/example_pkg@1.0-0', 'bAr', 'set name=description value="FOOO bAr O OO OOO"')
        ])

        res_remote_star = set([
            ('pkg:/example_pkg@1.0-0', '*', 'set name=weirdness value="] [ * ?"')
        ])

        res_remote_mark = set([
            ('pkg:/example_pkg@1.0-0', '?', 'set name=weirdness value="] [ * ?"')
        ])

        res_remote_left_brace = set([
            ('pkg:/example_pkg@1.0-0', '[', 'set name=weirdness value="] [ * ?"')
        ])

        res_remote_right_brace = set([
            ('pkg:/example_pkg@1.0-0', ']', 'set name=weirdness value="] [ * ?"')    
        ])
        
        local_fmri_string = \
            ('pkg:/example_pkg@1.0-0', 'example_pkg', '')

        res_local_pkg = set([
                local_fmri_string
                ])

        res_local_path = copy.copy(res_remote_path)

        res_local_bin = copy.copy(res_remote_bin)

        res_local_bug_id = copy.copy(res_remote_bug_id)

        res_local_inc_changes = copy.copy(res_remote_inc_changes)

        res_local_random_test = copy.copy(res_remote_random_test)

        res_local_keywords = copy.copy(res_remote_keywords)

        res_local_wildcard = copy.copy(res_remote_wildcard)
        res_local_wildcard.add(local_fmri_string)

        res_local_glob = copy.copy(res_remote_glob)
        res_local_glob.add(local_fmri_string)

        res_local_foo = copy.copy(res_remote_foo)
        res_local_bar = copy.copy(res_remote_bar)

        res_local_openssl = copy.copy(res_remote_openssl)
        
        res_local_path_example11 = set([
            ("pkg:/example_pkg@1.1-0", "basename", "file 820157a2043e3135f342b238129b556aade20347 chash=bfa46fc98d1ca97f1260090797d35a35e76096a3 group=bin mode=0555 owner=root path=bin/example_path11 pkg.csize=38 pkg.size=18")
        ])

        res_local_bin_example11 = set([
            ("pkg:/example_pkg@1.1-0", "path", "dir group=bin mode=0755 owner=root path=bin")
        ])

        res_local_wildcard_example11 = set([
            ("pkg:/example_pkg@1.1-0", "basename", "file 820157a2043e3135f342b238129b556aade20347 chash=bfa46fc98d1ca97f1260090797d35a35e76096a3 group=bin mode=0555 owner=root path=bin/example_path11 pkg.csize=38 pkg.size=18"),
            ("pkg:/example_pkg@1.1-0", "example_pkg", "")
       ])

        res_local_pkg_example11 = set([
            ("pkg:/example_pkg@1.1-0", "example_pkg", "")
        ])

        res_cat_pkg10 = set([
            ('pkg:/cat@1.0-0', 'System/Security', 'set name=info.classification value=org.opensolaris.category.2008:System/Security')
        ])

        res_cat2_pkg10 = set([
            ('pkg:/cat2@1.0-0', 'Applications/Sound and Video', 'set name=info.classification value="org.opensolaris.category.2008:Applications/Sound and Video"')
        ])

        res_cat3_pkg10 = set([
            ('pkg:/cat3@1.0-0', 'foo/bar/baz/bill/beam/asda', 'set name=info.classification value=org.opensolaris.category.2008:foo/bar/baz/bill/beam/asda')
        ])

        res_space_with_star = set([
            ('pkg:/space_pkg@1.0-0', 'basename', 'file 820157a2043e3135f342b238129b556aade20347 chash=bfa46fc98d1ca97f1260090797d35a35e76096a3 group=sys mode=0444 owner=nobody path="unique/with a space" pkg.csize=38 pkg.size=18')
        ])

        res_space_space_star = set([
            ('pkg:/space_pkg@1.0-0', 'basename', 'file 820157a2043e3135f342b238129b556aade20347 chash=bfa46fc98d1ca97f1260090797d35a35e76096a3 group=sys mode=0444 owner=nobody path="unique/with a space" pkg.csize=38 pkg.size=18'), ('pkg:/space_pkg@1.0-0', 'path', 'file 820157a2043e3135f342b238129b556aade20347 chash=bfa46fc98d1ca97f1260090797d35a35e76096a3 group=sys mode=0444 owner=nobody path="unique/with a space" pkg.csize=38 pkg.size=18')
        ])

        res_space_unique = set([
            ('pkg:/space_pkg@1.0-0', 'basename', 'dir group=bin mode=0755 owner=root path=unique_dir')
        ])

        misc_files = ['/tmp/example_file']

        # This is a copy of the 3.81%2C5.11-0.89%3A20080527T163123Z version of
        # SUNWgmake from ipkg with the file and liscense actions changed so
        # that they all take /tmp/example file when sending.
        bug_983_manifest = """
open SUNWgmake@3.81,5.11-0.89
add dir group=sys mode=0755 owner=root path=usr
add dir group=bin mode=0755 owner=root path=usr/bin
add dir group=bin mode=0755 owner=root path=usr/gnu
add dir group=bin mode=0755 owner=root path=usr/gnu/bin
add link path=usr/gnu/bin/make target=../../bin/gmake
add dir group=sys mode=0755 owner=root path=usr/gnu/share
add dir group=bin mode=0755 owner=root path=usr/gnu/share/man
add dir group=bin mode=0755 owner=root path=usr/gnu/share/man/man1
add link path=usr/gnu/share/man/man1/make.1 target=../../../../share/man/man1/gmake.1
add dir group=bin mode=0755 owner=root path=usr/sfw
add dir group=bin mode=0755 owner=root path=usr/sfw/bin
add link path=usr/sfw/bin/gmake target=../../bin/gmake
add dir group=bin mode=0755 owner=root path=usr/sfw/share
add dir group=bin mode=0755 owner=root path=usr/sfw/share/man
add dir group=bin mode=0755 owner=root path=usr/sfw/share/man/man1
add link path=usr/sfw/share/man/man1/gmake.1 target=../../../../share/man/man1/gmake.1
add dir group=sys mode=0755 owner=root path=usr/share
add dir group=bin mode=0755 owner=root path=usr/share/info
add dir group=bin mode=0755 owner=root path=usr/share/man
add dir group=bin mode=0755 owner=root path=usr/share/man/man1
add file /tmp/example_file elfarch=i386 elfbits=32 elfhash=68cca393e816e6adcbac1e8ffe9c618de70413e0 group=bin mode=0555 owner=root path=usr/bin/gmake pkg.size=18
add file /tmp/example_file group=bin mode=0444 owner=root path=usr/share/info/make.info pkg.size=18
add file /tmp/example_file group=bin mode=0444 owner=root path=usr/share/info/make.info-1 pkg.size=18
add file /tmp/example_file group=bin mode=0444 owner=root path=usr/share/info/make.info-2 pkg.size=18
add file /tmp/example_file group=bin mode=0444 owner=root path=usr/share/man/man1/gmake.1 pkg.size=18
add license /tmp/example_file license=SUNWgmake.copyright pkg.size=18 transaction_id=1211931083_pkg%3A%2FSUNWgmake%403.81%2C5.11-0.89%3A20080527T163123Z
add depend fmri=pkg:/SUNWcsl@0.5.11-0.89 type=require
add set name=description value="gmake - GNU make"
add legacy arch=i386 category=system desc="GNU make - A utility used to build software (gmake) 3.81" hotline="Please contact your local service provider" name="gmake - GNU make" pkg=SUNWgmake vendor="Sun Microsystems, Inc." version=11.11.0,REV=2008.04.29.02.08
close
"""

        res_bug_983 = set([
            ("pkg:/SUNWgmake@3.81-0.89", "basename", "link path=usr/sfw/bin/gmake target=../../bin/gmake"),
            ('pkg:/SUNWgmake@3.81-0.89', 'basename', 'file 820157a2043e3135f342b238129b556aade20347 chash=bfa46fc98d1ca97f1260090797d35a35e76096a3 elfarch=i386 elfbits=32 elfhash=68cca393e816e6adcbac1e8ffe9c618de70413e0 group=bin mode=0555 owner=root path=usr/bin/gmake pkg.csize=38 pkg.size=18'),
            ('pkg:/SUNWgmake@3.81-0.89', 'gmake', 'set name=description value="gmake - GNU make"')
        ])


        def setUp(self):
                for p in self.misc_files:
                        f = open(p, "w")
                        # Write the name of the file into the file, so that
                        # all files have differing contents.
                        f.write(p + "\n")
                        f.close()
                testutils.SingleDepotTestCase.setUp(self)
                tp = self.get_test_prefix()
                self.testdata_dir = os.path.join(tp, "search_results")
                os.mkdir(self.testdata_dir)
                self._dir_restore_functions = [self._restore_dir,
                    self._restore_dir_preserve_hash]

        def tearDown(self):
                testutils.SingleDepotTestCase.tearDown(self)
                for p in self.misc_files:
                        os.remove(p)
                shutil.rmtree(self.testdata_dir)

        def _check(self, proposed_answer, correct_answer):
                if correct_answer == proposed_answer:
                        return True
                else:
                        print "Proposed Answer: " + str(proposed_answer)
                        print "Correct Answer : " + str(correct_answer)
                        if isinstance(correct_answer, set) and \
                            isinstance(proposed_answer, set):
                                print >> sys.stderr, "Missing: " + \
                                    str(correct_answer - proposed_answer)
                                print >> sys.stderr, "Extra  : " + \
                                    str(proposed_answer - correct_answer)
                        self.assert_(correct_answer == proposed_answer)

        @staticmethod
        def _replace_act(act):
                if act.startswith('set name=fmri'):
                        return ''
                else:
                        return act.strip()
                        
        @staticmethod
        def _extract_action_from_res(it):
                return (
                    (fmri.PkgFmri(str(pkg_name)).get_short_fmri(), piece,
                    TestApiSearchBasics._replace_act(act))
                    for query_num, auth, (version, return_type,
                    (pkg_name, piece, act))
                    in it
                )
                        
        def _search_op(self, api_obj, remote, token, test_value,
            case_sensitive=False, return_actions=True, num_to_return=None,
            start_point=None):
                search_func = api_obj.local_search
                if remote:
                        search_func = api_obj.remote_search
                query = api.Query(token, case_sensitive, return_actions,
                    num_to_return, start_point)
                res = set(self._extract_action_from_res(search_func([query])))
                self._check(set(res), test_value)

        def _search_op_slow(self, api_obj, remote, token, test_value,
            case_sensitive=False, return_actions=True, num_to_return=None,
            start_point=None):
                search_func = api_obj.local_search
                if remote:
                        search_func = api_obj.remote_search
                query = api.Query(token, case_sensitive, return_actions,
                    num_to_return, start_point)
                tmp = search_func([query])
                res = []
                try:
                        for i in tmp:
                                res.append(i)
                except api_errors.SlowSearchUsed:
                        pass
                res = self._extract_action_from_res(res)
                self._check(set(res), test_value)


                
        def _run_remote_tests(self, api_obj):
                # Set to 1 since searches can't currently be performed
                # package name unless it's set inside the
                # manifest which happens at install time on
                # the client side.
                self._search_op(api_obj, True, "example_pkg", set())
                self._search_op(api_obj, True, "example_path",
                    self.res_remote_path)
                self._search_op(api_obj, True, "example*",
                    self.res_remote_wildcard)
                self._search_op(api_obj, True, "/bin", self.res_remote_bin)
                self._search_op(api_obj, True, "4851433",
                    self.res_remote_bug_id)
                self._search_op(api_obj, True, "6556919",
                    self.res_remote_inc_changes)
                self._search_op(api_obj, True, "6556?19",
                    self.res_remote_inc_changes)
                self._search_op(api_obj, True, "42",
                    self.res_remote_random_test) 
                self._search_op(api_obj, True, "separator",
                    self.res_remote_keywords)
                self._search_op(api_obj, True, "*example*",
                    self.res_remote_glob)
                self._search_op(api_obj, True, "fooo", self.res_remote_foo)
                self._search_op(api_obj, True, "fo*", self.res_remote_foo)
                self._search_op(api_obj, True, "bar", self.res_remote_bar)
                self._search_op(api_obj, True, "openssl",
                    self.res_remote_openssl)
                self._search_op(api_obj, True, "OPENSSL",
                    self.res_remote_openssl)
                self._search_op(api_obj, True, "OpEnSsL",
                    self.res_remote_openssl)
                self._search_op(api_obj, True, "OpEnS*",
                    self.res_remote_openssl)

                # These tests are included because a specific bug
                # was found during development. This prevents regression back
                # to that bug. Exit status of 1 is expected because the
                # token isn't in the packages.
                self._search_op(api_obj, True, "a_non_existent_token", set())
                
        def _run_local_tests(self, api_obj):
                outfile = os.path.join(self.testdata_dir, "res")

                # This finds something because the client side
                # manifest has had the name of the package inserted
                # into it.

                self._search_op(api_obj, False, "example_pkg",
                    self.res_local_pkg)
                self._search_op(api_obj, False, "example_path",
                    self.res_local_path)
                self._search_op(api_obj, False, "example*",
                    self.res_local_wildcard)
                self._search_op(api_obj, False, "/bin", self.res_local_bin)
                self._search_op(api_obj, False, "4851433",
                    self.res_local_bug_id)
                self._search_op(api_obj, False, "6556919",
                    self.res_local_inc_changes)
                self._search_op(api_obj, False, "65569??",
                    self.res_local_inc_changes)
                self._search_op(api_obj, False, "42",
                    self.res_local_random_test)
                self._search_op(api_obj, False, "separator",
                    self.res_local_keywords)
                self._search_op(api_obj, False, "*example*",
                    self.res_local_glob)
                self._search_op(api_obj, False, "fooo", self.res_local_foo)
                self._search_op(api_obj, False, "fo*", self.res_local_foo)
                self._search_op(api_obj, False, "bar", self.res_local_bar)
                self._search_op(api_obj, False, "openssl",
                    self.res_local_openssl)
                self._search_op(api_obj, False, "OPENSSL",
                    self.res_local_openssl)
                self._search_op(api_obj, False, "OpEnSsL",
                    self.res_local_openssl)
                self._search_op(api_obj, False, "OpEnS*",
                    self.res_local_openssl)

                # These tests are included because a specific bug
                # was found during development. These tests prevent regression
                # back to that bug. Exit status of 1 is expected because the
                # token isn't in the packages.
                self._search_op(api_obj, False, "a_non_existent_token", set())

        def _run_degraded_local_tests(self, api_obj):
                outfile = os.path.join(self.testdata_dir, "res")

                # This finds something because the client side
                # manifest has had the name of the package inserted
                # into it.

                self._search_op_slow(api_obj, False, "example_pkg",
                    self.res_local_pkg)
                self._search_op_slow(api_obj, False, "example_path",
                    self.res_local_path)
                self._search_op_slow(api_obj, False, "example*",
                    self.res_local_wildcard)
                self._search_op_slow(api_obj, False, "/bin", self.res_local_bin)
                self._search_op_slow(api_obj, False, "4851433",
                    self.res_local_bug_id)
                self._search_op_slow(api_obj, False, "6556919",
                    self.res_local_inc_changes)
                self._search_op_slow(api_obj, False, "65569??",
                    self.res_local_inc_changes)
                self._search_op_slow(api_obj, False, "42",
                    self.res_local_random_test)
                self._search_op_slow(api_obj, False, "separator",
                    self.res_local_keywords)
                self._search_op_slow(api_obj, False, "*example*",
                    self.res_local_glob)
                self._search_op_slow(api_obj, False, "fooo", self.res_local_foo)
                self._search_op_slow(api_obj, False, "fo*", self.res_local_foo)
                self._search_op_slow(api_obj, False, "bar", self.res_local_bar)
                self._search_op_slow(api_obj, False, "openssl",
                    self.res_local_openssl)
                self._search_op_slow(api_obj, False, "OPENSSL",
                    self.res_local_openssl)
                self._search_op_slow(api_obj, False, "OpEnSsL",
                    self.res_local_openssl)
                self._search_op_slow(api_obj, False, "OpEnS*",
                    self.res_local_openssl)

                # These tests are included because a specific bug
                # was found during development. These tests prevent regression
                # back to that bug. Exit status of 1 is expected because the
                # token isn't in the packages.
                self._search_op_slow(api_obj, False, "a_non_existent_token",
                    set())

                
        def _run_local_tests_example11_installed(self, api_obj):
                outfile = os.path.join(self.testdata_dir, "res")

                # This finds something because the client side
                # manifest has had the name of the package inserted
                # into it.

                self._search_op(api_obj, False, "example_pkg",
                    self.res_local_pkg_example11)
                self._search_op(api_obj, False, "example_path", set())
                self._search_op(api_obj, False, "example_path11",
                    self.res_local_path_example11)
                self._search_op(api_obj, False, "example*",
                    self.res_local_wildcard_example11)
                self._search_op(api_obj, False, "/bin",
                    self.res_local_bin_example11)

        def _run_local_empty_tests(self, api_obj):
                self._search_op(api_obj, False, "example_pkg", set())
                self._search_op(api_obj, False, "example_path", set())
                self._search_op(api_obj, False, "example*", set())
                self._search_op(api_obj, False, "/bin", set())

        def _run_remote_empty_tests(self, api_obj):
                self._search_op(api_obj, True, "example_pkg", set())
                self._search_op(api_obj, True, "example_path", set())
                self._search_op(api_obj, True, "example*", set())
                self._search_op(api_obj, True, "/bin", set())
                self._search_op(api_obj, True, "*unique*", set())

        @staticmethod
        def _restore_dir(index_dir, index_dir_tmp):
                shutil.rmtree(index_dir)
                shutil.move(index_dir_tmp, index_dir)

        @staticmethod
        def _restore_dir_preserve_hash(index_dir, index_dir_tmp):
                tmp_file = "full_fmri_list.hash"
                portable.remove(os.path.join(index_dir_tmp, tmp_file))
                shutil.move(os.path.join(index_dir, tmp_file),
                            index_dir_tmp)
                fh = open(os.path.join(index_dir_tmp, ss.MAIN_FILE), "r")
                fh.seek(0)
                fh.seek(9)
                ver = fh.read(1)
                fh.close()
                fh = open(os.path.join(index_dir_tmp, tmp_file), "r+")
                fh.seek(0)
                fh.seek(9)
                # Overwrite the existing version number.
                # By definition, the version 0 is never used.
                fh.write("%s" % ver)
                shutil.rmtree(index_dir)
                shutil.move(index_dir_tmp, index_dir)

        def _get_index_dirs(self):
                index_dir = os.path.join(self.img_path, "var","pkg","index")
                index_dir_tmp = index_dir + "TMP"
                return index_dir, index_dir_tmp

        @staticmethod
        def _overwrite_version_number(file_path):
                fh = open(file_path, "r+")
                fh.seek(0)
                fh.seek(9)
                # Overwrite the existing version number.
                # By definition, the version 0 is never used.
                fh.write("0")
                fh.close()

        @staticmethod
        def _overwrite_on_disk_format_version_number(file_path):
                fh = open(file_path, "r+")
                fh.seek(0)
                fh.seek(16)
                # Overwrite the existing version number.
                # By definition, the version 0 is never used.
                fh.write("9")
                fh.close()

        @staticmethod
        def _overwrite_on_disk_format_version_number_with_letter(file_path):
                fh = open(file_path, "r+")
                fh.seek(0)
                fh.seek(16)
                # Overwrite the existing version number.
                # By definition, the version 0 is never used.
                fh.write("a")
                fh.close()

        @staticmethod
        def _replace_on_disk_format_version(dir):
                file_path = os.path.join(dir, ss.BYTE_OFFSET_FILE)
                fh = open(file_path, "r")
                lst = fh.readlines()
                fh.close()
                fh = open(file_path, "w")
                fh.write(lst[0])
                for l in lst[2:]:
                        fh.write(l)
                fh.close()

        @staticmethod
        def _overwrite_hash(ffh_path):
                fh = open(ffh_path, "r+")
                fh.seek(0)
                fh.seek(20)
                fh.write("*")
                fh.close()

        def _check_no_index(self):
                ind_dir, ind_dir_tmp = self._get_index_dirs()
                if os.listdir(ind_dir):
                        self.assert_(0)
                if os.path.exists(ind_dir_tmp):
                        self.assert_(0)

        @staticmethod
        def _do_install(api_obj, pkg_list, **kwargs):
                api_obj.plan_install(pkg_list, [], **kwargs)
                TestApiSearchBasics._do_finish(api_obj)

        @staticmethod
        def _do_uninstall(api_obj, pkg_list, **kwargs):
                api_obj.plan_uninstall(pkg_list, False, **kwargs)
                TestApiSearchBasics._do_finish(api_obj)

        @staticmethod
        def _do_image_update(api_obj, **kwargs):
                api_obj.plan_update_all(sys.argv[0], **kwargs)
                TestApiSearchBasics._do_finish(api_obj)

        @staticmethod
        def _do_finish(api_obj):
                api_obj.prepare()
                api_obj.execute_plan()
                api_obj.reset()

        def test_remote(self):
                """Test remote search."""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)
                
                self._run_remote_tests(api_obj)
                
        def test_local_0(self):
                """Install one package, and run the search suite."""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                self._do_install(api_obj, ["example_pkg"])

                self._run_local_tests(api_obj)

        def test_degraded_local(self):
                """Install one package, and run the search suite."""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                self._do_install(api_obj, ["example_pkg"])

                index_dir = os.path.join(self.img_path, "var","pkg","index")
                shutil.rmtree(index_dir)

                self._run_degraded_local_tests(api_obj)

                
        def test_repeated_install_uninstall(self):
                """Install and uninstall a package. Checking search both
                after each change to the image."""
                # During development, the index could become corrupted by
                # repeated installing and uninstalling a package. This
                # tests if that has been fixed.
                repeat = 3

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                self._do_install(api_obj, ["example_pkg"])
                self._do_uninstall(api_obj, ["example_pkg"])

                for i in range(1, repeat):
                        self._do_install(api_obj, ["example_pkg"])
                        self._run_local_tests(api_obj)
                        self._do_uninstall(api_obj, ["example_pkg"])
                        api_obj.reset()
                        self._run_local_empty_tests(api_obj)

        def test_local_image_update(self):
                """Test that the index gets updated by image-update and
                that rebuilding the index works after updating the
                image. Specifically, this tests that rebuilding indexes with
                gaps in them works correctly."""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                self._do_install(api_obj, ["example_pkg"])

                self.pkgsend_bulk(durl, self.example_pkg11)

                self._do_image_update(api_obj)

                self._run_local_tests_example11_installed(api_obj)

                api_obj.rebuild_search_index()

                self._run_local_tests_example11_installed(api_obj)

        def test_bug_983(self):
                """Test for known bug 983."""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.bug_983_manifest)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                self._search_op(api_obj, True, "gmake", self.res_bug_983)

        def test_low_mem(self):
                """Test to check codepath used in low memory situations."""
                os.environ["PKG_INDEX_MAX_RAM"] = "0"
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.pkgsend_bulk(durl, self.bug_983_manifest)
                self.pkgsend_bulk(durl, self.bug_983_manifest)

                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                self._run_remote_tests(api_obj)
                self._search_op(api_obj, True, "gmake", self.res_bug_983)

        def test_missing_files(self):
                # working on this test case
                """Test to check for stack trace when files missing.
                Bug 2753"""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)

                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)
                self._do_install(api_obj, ["example_pkg"])
                
                index_dir = os.path.join(self.img_path, "var","pkg","index")

                for d in query_parser.TermQuery._global_data_dict.values():
                        orig_fn = d.get_file_name()
                        orig_path = os.path.join(index_dir, orig_fn)
                        dest_fn = orig_fn + "TMP"
                        dest_path = os.path.join(index_dir, dest_fn)
                        portable.rename(orig_path, dest_path)
                        self.assertRaises(api_errors.InconsistentIndexException,
                            self._search_op, api_obj, False, "example_pkg", [])
                        portable.rename(dest_path, orig_path)
                        self._search_op(api_obj, False, "example_pkg",
                            self.res_local_pkg)
                        
        def test_mismatched_versions(self):
                """Test to check for stack trace when files missing.
                Bug 2753"""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)
                self._do_install(api_obj, ["example_pkg"])
                
                index_dir = os.path.join(self.img_path, "var","pkg","index")

                for d in query_parser.TermQuery._global_data_dict.values():
                        orig_fn = d.get_file_name()
                        orig_path = os.path.join(index_dir, orig_fn)
                        dest_fn = orig_fn + "TMP"
                        dest_path = os.path.join(index_dir, dest_fn)
                        shutil.copy(orig_path, dest_path)
                        self._overwrite_version_number(orig_path)
                        api_obj.reset()
                        self.assertRaises(api_errors.InconsistentIndexException,
                            self._search_op, api_obj, False, "example_pkg", [])
                        portable.rename(dest_path, orig_path)
                        self._search_op(api_obj, False, "example_pkg",
                            self.res_local_pkg)
                        self._overwrite_version_number(orig_path)
                        self._do_uninstall(api_obj, ["example_pkg"])
                        self._search_op(api_obj, False, "example_pkg", set())
                        self._overwrite_version_number(orig_path)
                        self._do_install(api_obj, ["example_pkg"])
                        api_obj.reset()
                        self._search_op(api_obj, False, "example_pkg",
                            self.res_local_pkg)
                        
                ffh = ss.IndexStoreSetHash(ss.FULL_FMRI_HASH_FILE)
                ffh_path = os.path.join(index_dir, ffh.get_file_name())
                dest_path = ffh_path + "TMP"
                shutil.copy(ffh_path, dest_path)
                self._overwrite_hash(ffh_path)
                self.assertRaises(api_errors.IncorrectIndexFileHash,
                    self._search_op, api_obj, False, "example_pkg", set())
                portable.rename(dest_path, ffh_path)
                self._search_op(api_obj, False, "example_pkg",
                    self.res_local_pkg)
                self._overwrite_hash(ffh_path)
                self._do_uninstall(api_obj, ["example_pkg"])
                self._search_op(api_obj, False, "example_pkg", set())
                
        def test_bug_2989_1(self):
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)

                for f in self._dir_restore_functions:
                        self.image_create(durl)
                        progresstracker = progress.NullProgressTracker()
                        api_obj = api.ImageInterface(self.get_img_path(),
                            API_VERSION, progresstracker, lambda x: False,
                            PKG_CLIENT_NAME)
                        api_obj.rebuild_search_index()

                        index_dir, index_dir_tmp = self._get_index_dirs()

                        shutil.copytree(index_dir, index_dir_tmp)
                
                        self._do_install(api_obj, ["example_pkg"])

                        f(index_dir, index_dir_tmp)

                        self._do_uninstall(api_obj, ["example_pkg"])

                        self.image_destroy()

        def test_bug_2989_2(self):
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.pkgsend_bulk(durl, self.another_pkg10)

                for f in self._dir_restore_functions:

                        self.image_create(durl)
                        progresstracker = progress.NullProgressTracker()
                        api_obj = api.ImageInterface(self.get_img_path(),
                            API_VERSION, progresstracker, lambda x: False,
                            PKG_CLIENT_NAME)
                        self._do_install(api_obj, ["example_pkg"])

                        index_dir, index_dir_tmp = self._get_index_dirs()
                
                        shutil.copytree(index_dir, index_dir_tmp)

                        self._do_install(api_obj, ["another_pkg"])

                        f(index_dir, index_dir_tmp)

                        self._do_uninstall(api_obj, ["another_pkg"])

                        self.image_destroy()
                
        def test_bug_2989_3(self):
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.pkgsend_bulk(durl, self.example_pkg11)

                for f in self._dir_restore_functions:
                
                        self.image_create(durl)
                        progresstracker = progress.NullProgressTracker()
                        api_obj = api.ImageInterface(self.get_img_path(),
                            API_VERSION, progresstracker, lambda x: False,
                            PKG_CLIENT_NAME)
                        self._do_install(api_obj, ["example_pkg@1.0,5.11-0"])

                        index_dir, index_dir_tmp = self._get_index_dirs()

                        shutil.copytree(index_dir, index_dir_tmp)

                        self._do_install(api_obj, ["example_pkg"])

                        f(index_dir, index_dir_tmp)
                        
                        self._do_uninstall(api_obj, ["example_pkg"])

                        self.image_destroy()

        def test_bug_2989_4(self):
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.another_pkg10)
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.pkgsend_bulk(durl, self.example_pkg11)

                for f in self._dir_restore_functions:
                
                        self.image_create(durl)
                        progresstracker = progress.NullProgressTracker()
                        api_obj = api.ImageInterface(self.get_img_path(),
                            API_VERSION, progresstracker, lambda x: False,
                            PKG_CLIENT_NAME)
                        self._do_install(api_obj, ["another_pkg"])
                
                        index_dir, index_dir_tmp = self._get_index_dirs()
                        
                        shutil.copytree(index_dir, index_dir_tmp)

                        self._do_install(api_obj, ["example_pkg@1.0,5.11-0"])

                        f(index_dir, index_dir_tmp)

                        self._do_image_update(api_obj)

                        self.image_destroy()

        def test_local_case_sensitive(self):
                """Test local case sensitive search"""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                self._do_install(api_obj, ["example_pkg"])
                self._search_op(api_obj, False, "fooo", set(), True)
                self._search_op(api_obj, False, "fo*", set(), True)
                self._search_op(api_obj, False, "bar", set(), True)
                self._search_op(api_obj, False, "FOOO", self.res_local_foo,
                    True)
                self._search_op(api_obj, False, "bAr", self.res_local_bar, True)

        def test_weird_patterns(self):
                """Test strange patterns to ensure they're handled correctly"""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                self._search_op(api_obj, True, "[*]", self.res_remote_star)
                self._search_op(api_obj, True, "[?]", self.res_remote_mark)
                self._search_op(api_obj, True, "[[]",
                    self.res_remote_left_brace)
                self._search_op(api_obj, True, "[]]",
                    self.res_remote_right_brace)
                self._search_op(api_obj, True, "FO[O]O", self.res_remote_foo)
                self._search_op(api_obj, True, "FO[?O]O", self.res_remote_foo)
                self._search_op(api_obj, True, "FO[*O]O", self.res_remote_foo)
                self._search_op(api_obj, True, "FO[]O]O", self.res_remote_foo)

        def test_bug_2849(self):
                """Checks if things with spaces break the indexer."""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.space_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                self._do_install(api_obj, ["space_pkg"])
                time.sleep(1)
                
                self.pkgsend_bulk(durl, self.space_pkg10)

                self.pkg("refresh")
                self._do_install(api_obj, ["space_pkg"])
                
                remote = False
                self._search_op(api_obj, remote, 'with', set())
                self._search_op(api_obj, remote, 'with*',
                    self.res_space_with_star)
                self._search_op(api_obj, remote, '*space',
                    self.res_space_space_star)
                self._search_op(api_obj, remote, 'space', set())
                self._search_op(api_obj, remote, 'unique_dir',
                    self.res_space_unique)
                remote = True
                self._search_op(api_obj, remote, 'with', set())
                self._search_op(api_obj, remote, 'with*',
                    self.res_space_with_star)
                self._search_op(api_obj, remote, '*space',
                    self.res_space_space_star)
                self._search_op(api_obj, remote, 'space', set())
                self.pkgsend_bulk(durl, self.space_pkg10)
                self._search_op(api_obj, remote, 'with', set())
                self._search_op(api_obj, remote, 'with*',
                    self.res_space_with_star)
                self._search_op(api_obj, remote, '*space',
                    self.res_space_space_star)
                self._search_op(api_obj, remote, 'space', set())
                self._search_op(api_obj, remote, 'unique_dir',
                    self.res_space_unique)

        def test_bug_2863(self):
                """Test local case sensitive search"""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                self._check_no_index()
                self._do_install(api_obj, ["example_pkg"], update_index=False)
                self._check_no_index()
                api_obj.rebuild_search_index()
                self._run_local_tests(api_obj)
                self._do_uninstall(api_obj, ["example_pkg"], update_index=False)
                # Running empty test because search will notice the index
                # does not match the installed packages and complain.
                self.assertRaises(api_errors.IncorrectIndexFileHash,
                    self._search_op, api_obj, False, "example_pkg", set())
                api_obj.rebuild_search_index()
                self._run_local_empty_tests(api_obj)
                self._do_install(api_obj, ["example_pkg"])
                self._run_local_tests(api_obj)
                self.pkgsend_bulk(durl, self.example_pkg11)
                self._do_image_update(api_obj, update_index=False)
                # Running empty test because search will notice the index
                # does not match the installed packages and complain.
                self.assertRaises(api_errors.IncorrectIndexFileHash,
                    self._search_op, api_obj, False, "example_pkg", set())
                api_obj.rebuild_search_index()
                self._run_local_tests_example11_installed(api_obj)
                self._do_uninstall(api_obj, ["example_pkg"], update_index=False)
                # Running empty test because search will notice the index
                # does not match the installed packages and complain.
                self.assertRaises(api_errors.IncorrectIndexFileHash,
                    self._search_op, api_obj, False, "example_pkg", set())
                api_obj.rebuild_search_index()
                self._run_local_empty_tests(api_obj)

        def test_bug_4048_1(self):
                """Checks whether the server deals with partial indexing."""
                durl = self.dc.get_depot_url()
                depotpath = self.dc.get_repodir()
                tmp_dir = os.path.join(depotpath, "index", "TMP")
                os.mkdir(tmp_dir)
                self.pkgsend_bulk(durl, self.example_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)
                self._run_remote_empty_tests(api_obj)
                os.rmdir(tmp_dir)
                offset = 2
                depot_logfile = os.path.join(self.get_test_prefix(),
                    self.id(), "depot_logfile%d" % offset)
                tmp_dc = self.start_depot(12000 + offset, depotpath,
                    depot_logfile, refresh_index=True)
                time.sleep(1)
                self._run_remote_tests(api_obj)
                tmp_dc.kill()

        def test_bug_4048_2(self):
                """Checks whether the server deals with partial indexing."""
                durl = self.dc.get_depot_url()
                depotpath = self.dc.get_repodir()
                tmp_dir = os.path.join(depotpath, "index", "TMP")
                os.mkdir(tmp_dir)
                self.pkgsend_bulk(durl, self.space_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)
                self._run_remote_empty_tests(api_obj)
                os.rmdir(tmp_dir)
                self.pkgsend_bulk(durl, self.example_pkg10)
                time.sleep(1)
                self._run_remote_tests(api_obj)
                self._search_op(api_obj, True, "unique_dir",
                    self.res_space_unique)
                self._search_op(api_obj, True, "with*",
                    self.res_space_with_star)

        def test_bug_4239(self):
                """Tests whether categories are indexed and searched for
                correctly."""

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.cat_pkg10)
                self.pkgsend_bulk(durl, self.cat2_pkg10)
                self.pkgsend_bulk(durl, self.cat3_pkg10)
                self.pkgsend_bulk(durl, self.bad_cat_pkg10)
                self.pkgsend_bulk(durl, self.bad_cat2_pkg10)
                self.image_create(durl)
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)

                def _run_cat_tests(self, remote):
                        self._search_op(api_obj, remote, "System",
                            self.res_cat_pkg10, case_sensitive=False)
                        self._search_op(api_obj, remote, "Security",
                            self.res_cat_pkg10, case_sensitive=False)
                        self._search_op(api_obj, remote, "System/Security",
                            self.res_cat_pkg10, case_sensitive=False)

                def _run_cat2_tests(self, remote):
                        self._search_op(api_obj, remote, "Applications",
                            self.res_cat2_pkg10, case_sensitive=False)
                        self._search_op(api_obj, True, "Sound",
                            self.res_cat2_pkg10, case_sensitive=False)
                        self._search_op(api_obj, remote, "'Sound and Video'",
                            self.res_cat2_pkg10, case_sensitive=False)
                        self._search_op(api_obj, remote, "Sound*",
                            self.res_cat2_pkg10, case_sensitive=False)
                        self._search_op(api_obj, remote, "*Video",
                            self.res_cat2_pkg10, case_sensitive=False)
                        self._search_op(api_obj, remote,
                            "'Applications/Sound and Video'",
                            self.res_cat2_pkg10, case_sensitive=False)
                def _run_cat3_tests(self, remote):
                        self._search_op(api_obj, remote, "foo",
                            self.res_cat3_pkg10,case_sensitive=False)
                        self._search_op(api_obj, remote, "baz",
                            self.res_cat3_pkg10, case_sensitive=False)
                        self._search_op(api_obj, remote, "asda",
                            self.res_cat3_pkg10, case_sensitive=False)
                        self._search_op(api_obj, remote,
                            "foo/bar/baz/bill/beam/asda", self.res_cat3_pkg10,
                            case_sensitive=False)

                remote = True
                _run_cat_tests(self, remote)
                _run_cat2_tests(self, remote)
                _run_cat3_tests(self, remote)

                remote = False
                self._do_install(api_obj, ["cat"])
                _run_cat_tests(self, remote)

                self._do_install(api_obj, ["cat2"])
                _run_cat2_tests(self, remote)
                
                self._do_install(api_obj, ["cat3"])
                _run_cat3_tests(self, remote)
                
                self._do_install(api_obj, ["badcat"])
                self._do_install(api_obj, ["badcat2"])
                _run_cat_tests(self, remote)
                _run_cat2_tests(self, remote)
                _run_cat3_tests(self, remote)


class TestApiSearchMulti(testutils.ManyDepotTestCase):

        example_pkg10 = """
            open example_pkg@1.0,5.11-0
            close """

        def setUp(self):
                testutils.ManyDepotTestCase.setUp(self, 2)

                durl1 = self.dcs[1].get_depot_url()
                durl2 = self.dcs[2].get_depot_url()
                self.pkgsend_bulk(durl2, self.example_pkg10)

                self.image_create(durl1, prefix = "test1")
                self.pkg("set-publisher -O " + durl2 + " test2")

        def test_bug_2955(self):
                """See http://defect.opensolaris.org/bz/show_bug.cgi?id=2955"""
                progresstracker = progress.NullProgressTracker()
                api_obj = api.ImageInterface(self.get_img_path(), API_VERSION,
                    progresstracker, lambda x: False, PKG_CLIENT_NAME)
                TestApiSearchBasics._do_install(api_obj, ["example_pkg"])
                api_obj.rebuild_search_index()
                TestApiSearchBasics._do_uninstall(api_obj, ["example_pkg"])

if __name__ == "__main__":
        unittest.main()