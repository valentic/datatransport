#!/usr/bin/env python
"""Test watchdog restart"""

############################################################################
#
#   Crasher
#
#   This script runs for awhile then dies to test the watchdog.
#   Assumes that the ServerMonitor/Watchdog is running.
#
#   History:
#
#   2002-12-16  Todd Valentic
#               Initial implementation
#
#   2005-01-09  Todd Valentic
#               Use DeltaTime for lifetime.
#
#   2022-11-04  Todd Valentic
#               Update for python3
#
############################################################################

import sys

from datatransport import ProcessClient


class Crasher(ProcessClient):
    """Process that unexpectedly dies"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

    def main(self):
        """Main loop"""

        lifetime = self.config.get_rate("lifetime", 10)

        while self.wait(lifetime):
            self.log.info("About to crash!")
            self.log.info("badness = %f", 1 / 0)


if __name__ == "__main__":
    Crasher(sys.argv).run()
