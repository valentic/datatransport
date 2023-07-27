#!/usr/bin/env python
"""Test process spawning from client"""

############################################################################
#
#   Spawner
#
#   This script runs child process at specified intervals
#
#   History:
#
#   2002-12-19  Todd Valentic
#               Initial implementation
#
#   2022-11-04  Todd Valentic
#               Update for python3
#
############################################################################

import subprocess
import sys

from datatransport import ProcessClient


class Spawner(ProcessClient):
    """Spawn parent process"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

    def main(self):
        """Main loop"""

        rate = self.config.get_rate("spawn.rate", 10)
        cmd = self.config.get("spawn.command", "pwd")

        while self.wait(rate):

            self.log.info("Running command: %s", cmd)

            try:
                status, output = subprocess.getstatusoutput(cmd)
            except Exception: # pylint: disable=broad-exception-caught
                self.log.exception("Problem starting child")
                self.abort("Exiting")

            self.log.info("  Status=%d", status)
            self.log.info("  Output=%s", output)


if __name__ == "__main__":
    Spawner(sys.argv).run()
