#!/usr/bin/env python3
"""Request generator"""

##########################################################################
#
#   Generate group control request messages
#
#   2023-07-27  Todd Valentic
#               Initial implementation
#
##########################################################################

import sys

from datatransport import ProcessClient
from datatransport import NewsPoster

class RequestGenerator(ProcessClient):
    """Process client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.poster = NewsPoster(self)
        self.rate = self.config.get_rate('rate', 60)

    def main(self):
        
        states = ['start', 'stop']
        state = 0

        while self.wait(self.rate):
            msg = f"{states[state]}=hello"
            self.poster.post_text(msg)
            self.log.info('Posted %s', msg) 
            state = (state+1) % len(states)

if __name__ == '__main__':
    RequestGenerator(sys.argv).run()

