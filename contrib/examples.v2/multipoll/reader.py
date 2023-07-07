#!/usr/bin/env python

from Transport 		import ProcessClient
from Transport		import NewsPollMixin

import sys

class Reader(ProcessClient,NewsPollMixin):
	
	def __init__(self,argv):
		ProcessClient.__init__(self,argv)
		NewsPollMixin.__init__(self,callback=self.process)

	def process(self,message):
		
		body = message.get_payload()

		self.log.info('Message: %s' % body)

if __name__ == '__main__':
	Reader(sys.argv).run()
	
