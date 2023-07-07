#!/usr/bin/env python3

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

from datatransport import ProcessClient

import sys

class Client (ProcessClient):

    def __init__(self, args):
        ProcessClient.__init__(self, args)

    def init(self):

        self.rate = self.get_rate('rate')
        self.text = self.get('text')

        self.log.info(f'Log message every {self.rate.period}')

    def main(self):

        while self.wait(self.rate):
            self.log.info(self.text)

if __name__ == '__main__':
    Client(sys.argv).run()

