#!/usr/bin/env python3
"""Hello World example"""

##########################################################################
#
#   Hello World example
#
#   Periodically print a message to the log file.
#
#   2022-10-07  Todd Valentic
#               Initial implementation
#
##########################################################################

import sys

from datatransport import ProcessClient


class Client(ProcessClient):
    """Process Client"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.rate = self.config.get_rate("rate")
        self.text = self.config.get("text")

        self.log.info("Log message every: %s", self.rate.period)

    def main(self):
        """Main application"""

        while self.wait(self.rate):
            self.log.info(self.text)


if __name__ == "__main__":
    Client(sys.argv).run()
