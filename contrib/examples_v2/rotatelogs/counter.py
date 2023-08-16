#!/usr/bin/env python

############################################################################
#
#   Counter 
#
#   Write something to the log file 
#
#   History:
#   
#   1.0.0   2004-02-08  Todd Valentic   
#           Initial implementation
#
############################################################################

from    Transport   import ProcessClient

import  sys

class Counter(ProcessClient):

    def __init__(self,argv):
        ProcessClient.__init__(self,argv)

    def run(self):

        rate    = self.getDeltaTime('rate',1)
        offset  = self.getDeltaTime('offset',0)
        counter = 0

        while self.wait(rate,offset,sync=True): 
            self.log.info('Counter = %d' % counter)
            counter += 1

if __name__ == '__main__':
    Counter(sys.argv).run()

