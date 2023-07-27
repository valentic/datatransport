#!/usr/bin/env python
"""Pattern Template"""

###########################################################################
#
#   Pattern Template
#
#   This class provides a small template system for replacing content
#   in strings.
#
#   2001-10-11  Todd Valentic
#               Initial implementation.
#
#   2004-04-10  Todd Valentic
#               Use string methods vs string module
#               Use isinstance vs type module
#
#   2005-06-15  Todd Valentic
#               Added ability for value to be a dictionary.
#               Added setValue for caching of value parameter.
#
#   2012-02-10  Todd Valentic
#               Cache the value if given in the call.
#
#   2022-10-12  Todd Valentic
#               Python3 port
#               Use parse_slice (https://stackoverflow.com/a/68899290)
#               Rework implementation with regex instead of eval
#               setValue -> set_value
#
#   2023-07-26  Todd Valentic
#               Missing check for pattern 
#
#   SPDX-License-Identifier: GPL-3.0-or-later
#   Copyright (C) 1999-2022 Todd Valentic
#
###########################################################################

import re

from typing import Union

re_pattern = re.compile(r'(?<=<).*?(?=>)')
re_slice = re.compile(r'^.*\[(-?[\d]*):(-?[\d]*)[:]?(-?[\d]*)\]$')
re_index = re.compile(r'^.*\[(-?[\d]+)\]$')
re_key = re.compile(r'^.*\[\"(.+)\"\]$')

def parse_slice(string: str) -> slice:
    """
    Parse a string representation of a slice and return a slice object
    """
    # Matches one required colon, one optional colon, and up to three
    # positive or negative numbers between them (i.e. name[1:3])
    match = re_slice.match(string)
    if match:
        args = [int(s) if s else None for s in  match.group(1, 2, 3)]
        return slice(*args)
    raise ValueError("Could not parse slice")

def parse_index(string: str) -> int:
    """
    Parse a string representation of a list index and return an int
    """
    match = re_index.match(string)
    if match:
        return int(match.group(1))
    raise ValueError('Count not parse index')

def parse_key(string: str) -> str:
    """
    Parse a string representation of a dict key (i.e., name[key])
    """
    match = re_key.match(string)
    if match:
        return match.group(1)
    raise ValueError('Count not parse key')

def parse_patterns(string: str) -> list:
    """
    Return a unique list of patterns (<name>) found in the string
    """
    return list(set(re_pattern.findall(string)))

class PatternTemplate:
    """String pattern replacement"""

    def __init__(self, pattern: str, sep: str=None):
        self.pattern = pattern
        self.sep = sep
        self.value = None

    def set_value(self, value: Union[str, list, dict]) -> None:
        """Cache the value of the replacement string"""

        self.value = value

    def lookup_value(self, entry: str, value: Union[str, list, dict], sep: str='') -> str:
        """Look up the entry in the value str, list or dict"""

        if isinstance(value, (list, tuple)):

            try:
                idx = parse_index(entry)
                return value[idx]
            except ValueError:
                pass

            try:
                s = parse_slice(entry)
                return sep.join(value[s])
            except ValueError:
                pass

            return sep.join(value)

        if isinstance(value, dict):

            try:
                key = parse_key(entry)
                return value[key]
            except ValueError:
                pass

            return entry

        return value


    def __call__(self, src: str, value: str=None) -> str:
        """Replace <pattern> with value"""

        if value is not None:
            self.set_value(value)

        value = self.value

        if value is None:
            return src

        if self.sep:
            value = value.split(self.sep)

        for entry in parse_patterns(src):
            if not entry.startswith(self.pattern):
                continue
            v = self.lookup_value(entry, value, self.sep)
            src = src.replace(f'<{entry}>', str(v))

        return src
