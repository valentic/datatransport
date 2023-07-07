#!/usr/bin/env python
"""datetime helper functions"""

##########################################################################
#
#   datetime helper functions.
#
#   Most of these functions are now available as built-in methods since
#   it was originally written. It remains here to allow for existing
#   code that uses it to run unchanged.
#
#   2004-12-27  Todd Valentic
#               Initial implementation
#
#   2005-04-07  Todd Valentic
#               Added parse_timedelta
#
#   2020-10-08  Todd Valentic
#               Updated for python3
#               Replaced a number of functions with built-ins
#               Use pytimeparse2
#
#   SPDX-License-Identifier: GPL-3.0-or-later
#   Copyright (C) 1999-2022 Todd Valentic
#
##########################################################################

from datetime import datetime, timedelta, timezone

import pytimeparse2 as pytimeparse

def datetime_as_seconds(dt: datetime):
    """Return POSIX timestamp"""

    return dt.timestamp()

def strptime(datestr: str, fmt: str, tzinfo: timezone=None):
    """datetime parsed from a string"""

    return datetime.strptime(datestr, fmt).replace(tzinfo=tzinfo)

def timedelta_as_seconds(td: timedelta):
    """Return timedelta as seconds"""

    return td.total_seconds()

def parse_timedelta(timestr: str):
    """timedelta parsed from a string"""

    return timedelta(seconds=pytimeparse.parse(timestr))
