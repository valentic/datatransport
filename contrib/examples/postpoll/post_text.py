#!/usr/bin/env python3

##########################################################################
#
#   Posting example
#
#   Periodically post a message to a news group 
#
#   2022-10-10  Todd Valentic
#               Initial implementation
#
##########################################################################

from datatransport import ProcessClient
from datatransport import NewsPoster 

import sys

class Client(ProcessClient):

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)

    def init(self):

        self.rate = self.get_rate('rate')
        self.text = self.get('text')

        self.log.info(f'Post message every {self.rate.period}')

    def main(self):
        super().init()

        while self.wait(self.rate):
            self.news_poster.post_text(self.text)
            self.log.info('Posted message')

if __name__ == '__main__':
    Client(sys.argv).run()

