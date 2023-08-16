#!/usr/bin/env python

from Transport.Components   import SyncPoller 

import sys

class Poller (SyncPoller):
    
    def __init__(self,argv):
        SyncPoller.__init__(self,argv,callback=self.process)

    def process(self,message): 
        body = message.get_payload() 
        self.log.info(body)

if __name__ == '__main__':
    Poller(sys.argv).run()

