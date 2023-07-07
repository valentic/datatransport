#!/usr/bin/env python
"""Access Mixin"""

#########################################################################
#
#   Access Mixin
#
#   This mixin provides access to a parent ProcessClient's
#   methods for configuration lookup and logging. It is used
#   by companion classes (usually running in a separate
#   thread). It is similar to ConfigComponent.
#
#   2005-11-12  Todd Valentic
#               Initial implementation.
#
#   2006-10-26  Todd Valentic
#               Added currentTime and utc
#
#   2020-01-16  Todd Valentic
#               Added isRunning, isStopped
#
#   2022-10-07  Todd Valentic
#               Update imports
#               currentTime -> current_time
#
#   SPDX-License-Identifier: GPL-3.0-or-later
#   Copyright (C) 1999-2022 Todd Valentic
#
#########################################################################

from . import Root


class AccessMixin(Root):
    """Connect a child class to common methods in the parent"""

    def __init__(self, parent, getters=True):
        if getters:
            for key in dir(parent):
                method = getattr(parent, key)
                if callable(method) and key.startswith("get"):
                    setattr(self, key, method)

        self.parent = parent
        self.log = parent.log
        self.abort = parent.abort
        self.wait = parent.wait
        self.put = parent.put
        self.options = parent.options
        self.current_time = parent.current_time
        self.utc = parent.utc
        self.is_running = parent.is_running
        self.is_stopped = parent.is_stopped
