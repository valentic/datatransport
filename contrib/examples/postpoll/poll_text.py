#!/usr/bin/env python3
"""Text polling example"""

##########################################################################
#
#   Polling example
#
#   Periodically poll for messages from a news group
#
#   2022-10-10  Todd Valentic
#               Initial implementation
#
##########################################################################

import sys

from datatransport import ProcessClient
from datatransport import NewsPoller


class Client(ProcessClient):
    """Process client"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.poller = NewsPoller(self, callback=self.process)
        self.main = self.poller.main

        self.log.info("Poll for messages")

    def process(self, message):
        """Process handler"""

        text = message.get_payload()
        self.log.info('Received: "%s"', text)


if __name__ == "__main__":
    Client(sys.argv).run()
