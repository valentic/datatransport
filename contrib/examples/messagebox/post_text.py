#!/usr/bin/env python3

##########################################################################
#
#   MessageBox Posting example
#
#   Periodically post a message to a messagebox 
#
#   2023-02-22  Todd Valentic
#               Initial implementation
#
##########################################################################

from datatransport import ProcessClient
from datatransport import MessageBoxPoster 

import sys

class Client (ProcessClient):

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.poster = MessageBoxPoster(self)

        self.rate = self.get_rate('rate')
        self.text = self.get('text')

        self.log.info(f'Post message every {self.rate.period}')

    def run(self):

        self.log.info('Start')

        while self.wait(self.rate):
            self.poster.post_text(self.text)
            self.log.info('Posted message')

        self.log.info('Stop')

if __name__ == '__main__':
    Client(sys.argv).run()

