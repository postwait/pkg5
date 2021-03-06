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

# Copyright 2010 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.

import testutils
if __name__ == "__main__":
        testutils.setup_environment("../../../proto")
import pkg5unittest

import unittest
import pkg.elf as elf
import os
import sys

class TestElf(pkg5unittest.Pkg5TestCase):

	def test_is_elf_object(self):
		""" ASSERT: is_elf_object correctly classifies a range of
		    elf objects and non-elf objects """

		if os.path.exists("/usr/bin/cat"):
			self.assertEqual(elf.is_elf_object("/usr/bin/cat"),
			    True)

		if os.path.exists("/etc/motd"):
			self.assertNotEqual(elf.is_elf_object("/etc/motd"),
			    True)

		if os.path.exists("/dev/ksyms"):
			self.assertEqual(elf.is_elf_object("/dev/ksyms"),
			    True)

		if os.path.exists("/usr/lib/libmlib.so"):
			self.assertEqual(
			    elf.is_elf_object("/usr/lib/libmlib.so"), True)

		if os.path.exists("/kernel/drv/sd"):
			self.assertEqual(elf.is_elf_object("/kernel/drv/sd"),
			    True)

		if os.path.exists("/kernel/drv/amd64/sd"):
			self.assertEqual(
			    elf.is_elf_object("/kernel/drv/amd64/sd"), True)

		if os.path.exists("/kernel/drv/sparcv9/sd"):
			self.assertEqual(
			    elf.is_elf_object("/kernel/drv/sparcv9/sd"), True)

		self.assertRaises(OSError, elf.is_elf_object, "/does/not/exist")

	def test_get_dynamic(self):
		if os.path.exists("/usr/bin/cat"):
			try:
				elf.get_dynamic("/usr/bin/cat")
			except:
				self.fail();

		if os.path.exists("/etc/motd"):
			self.assertRaises(elf.ElfError, elf.get_dynamic,
			    "/etc/motd")

		if os.path.exists("/usr/lib/libmlib.so"):
			elf.get_dynamic("/usr/lib/libmlib.so")

		if os.path.exists("/kernel/drv/sd"):
			elf.get_dynamic("/kernel/drv/sd")

		if os.path.exists("/kernel/drv/amd64/sd"):
			elf.get_dynamic("/kernel/drv/amd64/sd")

		if os.path.exists("/kernel/drv/sparcv9/sd"):
			elf.get_dynamic("/kernel/drv/sparcv9/sd")

		if os.path.exists("/usr/lib/crti.o"):
			elf.get_dynamic("/usr/lib/crti.o")

		if os.path.exists("/usr/kernel/drv/fssnap"):
			elf.get_dynamic("/usr/kernel/drv/fssnap")

		if os.path.exists("/usr/kernel/drv/amd64/fssnap"):
			elf.get_dynamic("/usr/kernel/drv/amd64/fssnap")

		if os.path.exists("/usr/kernel/drv/sparcv9/fssnap"):
			elf.get_dynamic("/usr/kernel/drv/sparcv9/fssnap")


		self.assertRaises(OSError, elf.get_dynamic, "/does/not/exist")

	def test_get_info(self):
		if os.path.exists("/usr/bin/cat"):
			try:
				elf.get_info("/usr/bin/cat")
			except:
				self.fail();

		if os.path.exists("/etc/motd"):
			self.assertRaises(elf.ElfError, elf.get_info,
			    "/etc/motd");

		if os.path.exists("/usr/lib/libmlib.so"):
			elf.get_info("/usr/lib/libmlib.so")

		if os.path.exists("/kernel/drv/sd"):
			elf.get_info("/kernel/drv/sd")

		if os.path.exists("/kernel/drv/amd64/sd"):
			elf.get_info("/kernel/drv/amd64/sd")

		if os.path.exists("/kernel/drv/sparcv9/sd"):
			elf.get_info("/kernel/drv/sparcv9/sd")

		if os.path.exists("/usr/lib/crti.o"):
			elf.get_info("/usr/lib/crti.o")

		if os.path.exists("/usr/kernel/drv/fssnap"):
			elf.get_info("/usr/kernel/drv/fssnap")

		if os.path.exists("/usr/kernel/drv/amd64/fssnap"):
			elf.get_info("/usr/kernel/drv/amd64/fssnap")

		if os.path.exists("/usr/kernel/drv/sparcv9/fssnap"):
			elf.get_info("/usr/kernel/drv/sparcv9/fssnap")

		self.assertRaises(OSError, elf.get_info, "/does/not/exist");
		

if __name__ == "__main__":
	unittest.main()
