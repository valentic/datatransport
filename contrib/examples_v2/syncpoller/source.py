#!/usr/bin/env python

from Transport  import ProcessClient
from Transport  import NewsPostMixin
from datetime   import datetime

import sys

class Source (ProcessClient,NewsPostMixin):
    
    def __init__(self,argv):
        ProcessClient.__init__(self,argv)
        NewsPostMixin.__init__(self)

        self.rate = self.getDeltaTime('post.rate',60)

        self.log.info('rate: %s' % self.rate)

    def run(self):

        while self.wait(self.rate,sync=True):   
            self.newsPoster.postText('[%s] %s' % (self.name,datetime.now()))
            self.log.info('Posted message')

if __name__ == '__main__':
    Source(sys.argv).run()

