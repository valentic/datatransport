#!/usr/bin/env python3

##########################################################################
#
#   MessageBox polling example
#
#   Periodically poll for messages from a news group 
#
#   2023-02-23  Todd Valentic
#               Initial implementation
#
##########################################################################

from datatransport import ProcessClient
from datatransport import MessageBoxPoller 

import sys

class Client (ProcessClient):

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.poller = MessageBoxPoller(self)

        self.log.info(f'Poll for messages')

    def process(self, message):

        text = message.get_payload()
        self.log.info(f'Received "{text}"')

    def run(self):

        self.log.info('Start')
        
        self.poller.run(self.process)

        self.log.info('Stop')

if __name__ == '__main__':
    Client(sys.argv).run()

