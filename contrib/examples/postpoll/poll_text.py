#!/usr/bin/env python3

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

from datatransport import ProcessClient
from datatransport import NewsPoller

import sys

class Client (ProcessClient):

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.poller = NewsPoller(self, callback=self.process)
        self.main = self.poller.main

        self.log.info(f'Poll for messages')

    def process(self, message):

        text = message.get_payload()
        self.log.info(f'Received "{text}"')

if __name__ == '__main__':
    Client(sys.argv).run()

