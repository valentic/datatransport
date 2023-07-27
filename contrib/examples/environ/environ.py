#!/usr/bin/env python
"""Test setting environment"""

############################################################################
#
#   Environ
#
#   This script displays the environment variables is sees at startup.
#
#   History:
#
#   2002-12-19  Todd Valentic
#               Initial implementation
#
#   2022-11-02  Todd Valentic
#               Python3 update
#
############################################################################

import os
import sys

from datatransport import ProcessClient


class DisplayEnviron(ProcessClient):
    """Display environment"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

    def init(self):
        super().init()

        self.print_environ()

    def print_environ(self):
        """Print environment to log"""

        self.log.info("Current Environment:")

        for key in sorted(os.environ):
            self.log.info("%s = %s", key, os.environ[key])

    def main(self):
        """Main loop"""

        while self.wait(60):
            pass


if __name__ == "__main__":
    DisplayEnviron(sys.argv).run()
