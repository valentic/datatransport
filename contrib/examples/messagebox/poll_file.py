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
from datatransport import NewsPollMixin 
from datatransport import newstool
from datatransport.utilities import remove_file

import sys

class Client (ProcessClient, NewsPollMixin):

    def __init__(self, args):
        ProcessClient.__init__(self, args)
        NewsPollMixin.__init__(self, callback=self.process)

        self.log.info(f'Poll for messages')

    def process(self, message):

        filenames = newstool.save_files(message)
        self.log.info(f'Received files: {[str(f) for f in filenames]}')

        remove_file(filenames)

if __name__ == '__main__':
    Client(sys.argv).run()

