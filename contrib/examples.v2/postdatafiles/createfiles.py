#!/usr/bin/env python

from Transport  import ProcessClient
from datetime   import datetime 

import sys
import os

class CreateFiles(ProcessClient):
	
	def __init__(self,argv):
		ProcessClient.__init__(self,argv)

		self.pollrate	= self.getDeltaTime('pollrate',60)
		self.path		= self.get('filename.path','.')
		self.filenames	= self.get('filenames','%Y%m%d-%H%M%S.txt').split()

	def run(self):

		while self.running:

			curdate	= datetime.now()

			for filename in self.filenames:
				filename = curdate.strftime(filename)
				filename = os.path.join(self.path,filename)

				dir = os.path.dirname(filename)
				if not os.path.exists(dir):
					os.makedirs(dir)

				file = open(filename,'w')
				file.write('%s\n' % datetime.now().strftime('%Y%m%d %H%M%S'))
				file.close()

				self.log.info('Created: %s' % filename)

			self.wait(self.pollrate)

if __name__ == '__main__':
	CreateFiles(sys.argv).run()
	
