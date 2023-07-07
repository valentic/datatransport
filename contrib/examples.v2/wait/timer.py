#!/usr/bin/env python2

############################################################################
#
#   Timer   
#
#   Test wait() timing. 
#
#   History:
#   
#   1.0.0   2005-09-19  Todd Valentic   
#           Initial implementation
#
############################################################################

from    Transport   import ProcessClient

import  sys

class Timer(ProcessClient):

    def __init__(self,argv):
        ProcessClient.__init__(self,argv)

    def run(self):

        rate   = self.getDeltaTime ('poll.rate',60)
        sync   = self.getboolean   ('poll.sync',True)
        offset = self.getDeltaTime ('poll.offset',0)

        while self.running:
            self.log.info('Waiting')
            self.wait(rate,offset=offset,sync=sync)
            self.log.info('  mark')

if __name__ == '__main__':
    Timer(sys.argv).run()

