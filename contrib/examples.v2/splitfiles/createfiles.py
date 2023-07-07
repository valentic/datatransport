#!/usr/bin/env python2

from Transport 		import ProcessClient
from datetime		import datetime 

import sys
import os

class CreateFiles(ProcessClient):
	
	def __init__(self,argv):
		ProcessClient.__init__(self,argv)

		self.pollrate	= self.getDeltaTime('pollrate',60)
		self.path		= self.get('filename.path','.')
		self.filenames	= self.get('filenames','%Y%m%d-%H%M%S.dat').split()
		self.size		= self.getBytes('filename.size',10)
		self.small		= self.getint('small',1)

	def run(self):

		while self.running:

			curdate	= datetime.now()

			for filename in self.filenames:
				filename = curdate.strftime(filename)
				filename = os.path.join(self.path,filename)

				dir = os.path.dirname(filename)
				if not os.path.exists(dir):
					os.makedirs(dir)

				if self.small:
					file = open(filename,'wb')
					for k in range(self.size):
						file.write(chr(ord('0')+(k%10)))
					file.close()

				else:

					os.system('dd if=/dev/zero of=%s bs=%d count=1' % \
								(filename,self.size))

				self.log.info('Created: %s' % filename)

			self.wait(self.pollrate)

if __name__ == '__main__':
	CreateFiles(sys.argv).run()
	
