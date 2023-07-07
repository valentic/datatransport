#!/usr/bin/env python
"""Test watchdog restart"""

############################################################################
#
#   Crasher
#
#   This script crashs in __init__() to test the transport server's ability 
#   to capture and report stderr to the server's log.
#
#   History:
#
#   2023-07-06  Todd Valentic
#               Initial implementation
#
############################################################################

import sys

from datatransport import ProcessClient


class InitCrasher(ProcessClient):
    """Process that unexpectedly dies"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        raise IOError("Goes boom in __init__()")

if __name__ == "__main__":
    InitCrasher(sys.argv).run()
