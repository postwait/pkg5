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

#
# Copyright (c) 2009, 2010, Oracle and/or its affiliates. All rights reserved.
#

MIN_ELEMENTS_BOUNCE = 5      # During indexing the progress will be progressive if 
                                 # the number of indexing elements is greater then this, 
                                 # otherwise it will bounce

from pkg.client.progress import NullProgressTracker

class GuiProgressTracker(NullProgressTracker):

        def __init__(self, indent = False):
                NullProgressTracker.__init__(self)
                self.prev_pkg = None
                self.act_phase_last = None
                self.ind_started = False
                self.item_started = False
                self.indent = indent

        def cat_output_start(self):
                if self.indent:
                        self.update_details_text(_("Retrieving catalog '%s'...\n") % \
                            self.cat_cur_catalog, "level1")
                else:
                        self.update_details_text(_("Retrieving catalog '%s'...\n") % \
                            self.cat_cur_catalog)
                return

        def cat_output_done(self):
                return

        def cache_cats_output_start(self):
                if self.indent:
                        self.update_details_text(_("Caching catalogs ...\n"), "level1")
                else:
                        self.update_details_text(_("Caching catalogs ...\n"))
                return

        def cache_cats_output_done(self):
                return

        def load_cat_cache_output_start(self):
                if self.indent:
                        self.update_details_text(_("Loading catalog cache ...\n"),
                            "level1")
                else:
                        self.update_details_text(_("Loading catalog cache ...\n"))
                return

        def load_cat_cache_output_done(self):
                return

        def refresh_output_start(self):
                return

        def refresh_output_progress(self):
                if self.indent:
                        self.update_details_text(
                            _("Refreshing catalog %s\n") % self.refresh_cur_pub, "level1")
                else:
                        self.update_details_text(
                            _("Refreshing catalog %s\n") % self.refresh_cur_pub)
                return

        def refresh_output_done(self):
                if self.indent:
                        self.update_details_text(
                            _("Finished refreshing catalog %s\n") % self.refresh_cur_pub,
                            "level1")
                else:
                        self.update_details_text(
                            _("Finished refreshing catalog %s\n") % self.refresh_cur_pub)
                return

        def eval_output_start(self):
                return

        def eval_output_progress(self):
                '''Called by progress tracker each time some package was evaluated. The
                call is being done by calling progress tracker evaluate_progress() 
                function'''
                if self.prev_pkg != self.eval_cur_fmri:
                        self.prev_pkg = self.eval_cur_fmri
                        text = _("Evaluating: %s") % self.eval_cur_fmri.get_name()
                        self.update_label_text(text)
                        self.reset_label_text_after_delay()

        def eval_output_done(self):
                return

        def ver_output(self):
                return

        def ver_output_error(self, actname, errors):
                return

        def ver_output_done(self):
                return

        def dl_output(self):
                self.display_download_info()
                if self.prev_pkg != self.cur_pkg:
                        self.prev_pkg = self.cur_pkg
                        self.update_details_text(
                            _("Package %d of %d: %s\n") % (self.dl_cur_npkgs+1, 
                            self.dl_goal_npkgs, self.cur_pkg), "level1")

        def dl_output_done(self):
                self.update_details_text("\n")

        def act_output(self, force=False):
                if self.act_phase != self.act_phase_last:
                        self.act_phase_last = self.act_phase
                        self.update_label_text(self.act_phase)
                        self.update_details_text("%s\n" % self.act_phase, "level1")
                self.display_phase_info(self.act_phase, self.act_cur_nactions,
                    self.act_goal_nactions)
                return

        def act_output_done(self):
                return

        def ind_output(self, force=False):
                if self.ind_started != self.ind_phase:
                        self.ind_started = self.ind_phase
                        self.update_label_text(self.ind_phase)
                        self.update_details_text(
                            "%s\n" % (self.ind_phase), "level1")
                self.__indexing_progress()

        def ind_output_done(self):
                self.update_progress(self.ind_cur_nitems, self.ind_goal_nitems)

        def __indexing_progress(self):
                self.__generic_progress(self.ind_phase, self.ind_goal_nitems,
                    self.ind_cur_nitems)

        def __generic_progress(self, phase, goal_nitems, cur_nitems):
                #It doesn't look nice if the progressive is just for few elements
                if goal_nitems > MIN_ELEMENTS_BOUNCE:
                        self.display_phase_info(phase, cur_nitems-1, goal_nitems)
                else:
                        if not self.is_progress_bouncing():
                                self.start_bouncing_progress()

        def item_output(self, force=False):
                if self.item_started != self.item_phase:
                        self.item_started = self.item_phase
                        self.update_label_text(self.item_phase)
                        self.update_details_text(
                            "%s\n" % (self.item_phase), "level1")
                self.__item_progress()

        def __item_progress(self):
                self.__generic_progress(self.item_phase, self.item_goal_nitems,
                    self.item_cur_nitems)


        def item_output_done(self):
                self.update_progress(self.item_cur_nitems, self.item_goal_nitems)

        def update_progress(self, current_progress, total_progress):
                raise NotImplementedError("abstract method update_progress() not "
                    "implemented in superclass")

        def start_bouncing_progress(self):
                raise NotImplementedError("abstract method start_bouncing_progress() "
                    "not implemented in superclass")

        def is_progress_bouncing(self):
                raise NotImplementedError("abstract method is_progress_bouncing() "
                    "not implemented in superclass")

        def stop_bouncing_progress(self):
                raise NotImplementedError("abstract method stop_bouncing_progress() "
                    "not implemented in superclass")

        def display_download_info(self):
                raise NotImplementedError("abstract method display_download_info() "
                    "not implemented in superclass")

        def display_phase_info(self, phase_name, cur_n, goal_n):
                raise NotImplementedError("abstract method display_phase_info() "
                    "not implemented in superclass")

        def reset_label_text_after_delay(self):
                raise NotImplementedError(
                    "abstract method reset_label_text_after_delay() "
                    "not implemented in superclass")

        def update_label_text(self, text):
                raise NotImplementedError("abstract method update_label_text() "
                    "not implemented in superclass")

        def update_details_text(self, text, *tags):
                raise NotImplementedError("abstract method update_details_text() "
                    "not implemented in superclass")

