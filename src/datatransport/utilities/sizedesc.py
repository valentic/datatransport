#!/usr/bin/env python
"""Human readable formatting for bytes"""

##########################################################################
#
#   Human-readable formatting of bytes, using binary (powers of 1024)
#   or metric (powers of 1000) representation. Based on Mitch McMabers
#   answer and code from this stackoverlow question:
#
#   https://stackoverflow.com/a/63839503/19095781
#
#   2001-08-27  Todd Valentic
#               Initial implementation
#
#   2022-10-12  Todd Valentic
#               Add header block
#               Rework code based on HumanBytes stackoverlow answer
#               Use snake case sizeDesc -> size_desc
#
#   SPDX-License-Identifier: GPL-3.0-or-later
#   Copyright (C) 1999-2022 Todd Valentic
#
##########################################################################

from typing import List, Union

METRIC_LABELS: List[str] = ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
BINARY_LABELS: List[str] = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]

# Predefined for speed

PRECISION_OFFSETS: List[float] = [0.5, 0.05, 0.005, 0.0005]
PRECISION_FORMATS: List[str] = ["{}{:.0f} {}", "{}{:.1f} {}", "{}{:.2f} {}", "{}{:.3f} {}"]

def size_desc(num: Union[int, float], metric: bool=False, precision: int=1) -> str:
    """
    Human-readable formatting of bytes, using binary (powers of 1024)
    or metric (powers of 1000) representation.
    """

    assert isinstance(num, (int, float)), "num must be an int or float"
    assert isinstance(metric, bool), "metric must be a bool"
    assert isinstance(precision, int) and 0 <= precision <= 3, \
        "precision must be an int (range 0-3)"

    unit_labels = METRIC_LABELS if metric else BINARY_LABELS
    last_label = unit_labels[-1]
    unit_step = 1000 if metric else 1024
    unit_step_thresh = unit_step - PRECISION_OFFSETS[precision]

    is_negative = num < 0
    if is_negative: # Faster than ternary assignment or always running abs().
        num = abs(num)

    for unit in unit_labels:
        if num < unit_step_thresh:
            # VERY IMPORTANT:
            # Only accepts the CURRENT unit if we're BELOW the threshold where
            # float rounding behavior would place us into the NEXT unit: F.ex.
            # when rounding a float to 1 decimal, any number ">= 1023.95" will
            # be rounded to "1024.0". Obviously we don't want ugly output such
            # as "1024.0 KiB", since the proper term for that is "1.0 MiB".
            break
        if unit != last_label:
            # We only shrink the number if we HAVEN'T reached the last unit.
            # NOTE: These looped divisions accumulate floating point rounding
            # errors, but each new division pushes the rounding errors further
            # and further down in the decimals, so it doesn't matter at all.
            num /= unit_step

    return PRECISION_FORMATS[precision].format("-" if is_negative else "", num, unit)
