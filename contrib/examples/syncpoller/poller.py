#!/usr/bin/env python3
"""Example SyncPoller"""

import sys

from datatransport import ProcessClient
from datatransport.apps import SyncPoller 

class Poller(ProcessClient):
    """SyncPoller Process Client"""
    
    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.poller = SyncPoller(self, callback=self.process)
        self.main = self.poller.main

    def process(self, message): 
        """Process handler"""

        body = message.get_payload() 
        self.log.info(body)

if __name__ == '__main__':
    Poller(sys.argv).run()

