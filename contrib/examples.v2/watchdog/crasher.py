#!/usr/bin/env python2

############################################################################
#
#   Crasher 
#
#   This script runs for awhile then dies to test the watchdog.
#   Assumes that the ServerMonitor/Watchdog is running.
#
#   History:
#   
#   1.0.0   2002-12-16  Todd Valentic   
#           Initial implementation
#
#   1.0.1   2005-01-09  Todd Valentic
#           Use DeltaTime for lifetime.
#
############################################################################

from    Transport   import ProcessClient

import  sys

class Crasher(ProcessClient):

    def __init__(self,argv):
        ProcessClient.__init__(self,argv)

    def run(self):

        lifetime = self.getDeltaTime('lifetime',10)

        while self.wait(lifetime): 
            self.log.info('About to crash!')
            badness = 1/0

if __name__ == '__main__':
    Crasher(sys.argv).run()

