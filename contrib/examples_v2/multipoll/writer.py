#!/usr/bin/env python

from Transport 		import ProcessClient
from Transport		import NewsPostMixin

import sys

class Writer(ProcessClient,NewsPostMixin):
	
	def __init__(self,argv):
		ProcessClient.__init__(self,argv)
		NewsPostMixin.__init__(self)

		self.pollrate	= self.getDeltaTime('rate',60)
		self.message	= self.get('message')

	def run(self):

		while self.running:

			self.newsPoster.postText(self.message)
			self.log.info('Posted message')
			self.wait(self.pollrate)

if __name__ == '__main__':
	Writer(sys.argv).run()
	
