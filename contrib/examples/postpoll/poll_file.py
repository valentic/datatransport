#!/usr/bin/env python3
"""File polling example"""

##########################################################################
#
#   Polling example (file attachment)
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
from datatransport import newstool
from datatransport.utilities import remove_file


class Client(ProcessClient):
    """Process client"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.poller = NewsPoller(self, callback=self.process)
        self.main = self.poller.main

        self.log.info("Poll for messages")

    def process(self, message):
        """Process handler"""

        filenames = newstool.save_files(message)
        self.log.info("Received files: %s", [str(f) for f in filenames])

        remove_file(filenames)


if __name__ == "__main__":
    Client(sys.argv).run()
