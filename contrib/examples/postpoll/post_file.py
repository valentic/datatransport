#!/usr/bin/env python3

##########################################################################
#
#   File post example
#
#   Periodically post a file to a news group 
#
#   2022-10-10  Todd Valentic
#               Initial implementation
#
##########################################################################

from datatransport import ProcessClient
from datatransport import NewsPoster

import sys
import pathlib

class Client (ProcessClient):

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.news_poster = NewsPoster(self)

    def init(self):

        self.rate = self.get_rate('rate')
        self.text = self.get('text')

        self.log.info(f'Post message every {self.rate.period}')

    def main(self):

        filename = pathlib.Path('data.txt')

        while self.wait(self.rate):

            with filename.open(mode='w') as message:
                message.write(self.text)

            self.news_poster.post(str(filename))
            self.log.info('Posted %s' % filename)

            filename.unlink()

if __name__ == '__main__':
    Client(sys.argv).run()

