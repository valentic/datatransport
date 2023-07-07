#!/usr/bin/env python
"""Remove files"""

########################################################################
#
#   remove_file
#
#   This is a small routine to remove files. It first tests to see if
#   the file exists and then tries to remove it. This approximates the
#   'rm -f' command. The input parameter can be a single filename or a
#   list of filenames. Each name can be a string, bytes or a pathlib
#   object.
#
#   2001-08-27  Todd Valentic
#               Initial implementation.
#
#   2001-10-11  Todd Valentic
#               Modified to handle a list of filenames.
#
#   2022-10-10  Todd Valentic
#               Python3 port
#               Support pathlib
#               removeFile -> remove_file
#
#   SPDX-License-Identifier: GPL-3.0-or-later
#   Copyright (C) 1999-2022 Todd Valentic
#
########################################################################

import pathlib

from collections.abc import Iterable
from typing import Union

def remove_file(filenames: Union[str, bytes, Iterable]) -> None:
    """
    Remove a filename or list of filenames. Ignore errors.
    """

    if isinstance(filenames, (str, bytes)):
        filenames = [filenames]
    elif not isinstance(filenames, Iterable):
        filenames = [filenames]

    for filename in filenames:
        path = pathlib.Path(str(filename))
        path.unlink(missing_ok=True)
