#!/usr/bin/env python
"""Test log rotation"""

############################################################################
#
#   Counter
#
#   Write something to the log file
#
#   History:
#
#   2004-02-08  Todd Valentic
#               Initial implementation
#
#   2022-11-04  Todd Valentic
#               Update for Python3
#
############################################################################

import sys

from datatransport import ProcessClient


class Counter(ProcessClient):
    """Test program"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

    def main(self):
        """Main loop"""

        rate = self.config.get_rate("rate", 1)
        counter = 0

        while self.wait(rate):
            self.log.info("Counter = %d", counter)
            counter += 1


if __name__ == "__main__":
    Counter(sys.argv).run()
