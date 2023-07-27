#!/usr/bin/env python
"""Service client example"""

##########################################################################
#
#   Example client calling a service
#
#   2022-11-02  Todd Valentic
#               Initial implementation
#
##########################################################################

import sys

from datatransport import ProcessClient
from datatransport import Directory


class EchoClient(ProcessClient):
    """Client calling the echo service"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.directory = Directory(self)

        self.rate = self.config.get_rate("rate", "10s")

        self.log.info('echo client')

        self.echo = self.directory.connect("echo")

    def run(self):
        self.log.info("Starting")
        try:
            self._run()
        except BaseException as err:
            self.log.exception(str(err))
        self.log.info("Stopping")

    def _run(self):
        """Main loop"""

        while self.wait(self.rate):
            result = self.echo.emit("Helloooooo")
            self.log.info("Call returned '%s'", result)


if __name__ == "__main__":
    EchoClient(sys.argv).run()
