#!/usr/bin/env python
"""Create parent directories along a path, setting mode if needed"""

#####################################################################
#
#   Create parent directories along a path, setting mode if needed
#
#   2001-12-02  Todd Valentic
#		        Explicity call chmod to fix some issues with umask
#
#   2022-10-12  Todd Valentic
#               Python3 port
#               Use pathlib
#               No longer set group (better done with group setid)
#               Use snake case
#
#   SPDX-License-Identifier: GPL-3.0-or-later
#   Copyright (C) 1999-2022 Todd Valentic
#
#####################################################################

from typing import Union
from pathlib import Path

def make_path(filename: Union[str, Path], mode: int=None) -> None:
    """Create parent directories"""

    for path in reversed(Path(filename).absolute().parents):
        if not path.exists():
            path.mkdir()
            if mode:
                path.chmod(mode)
