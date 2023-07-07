#!/usr/bin/env python2

############################################################################
#
#	CreateData	
#
#	This script creates test data files. 
#
#	History:
#	
#	1.0.0 	2002-12-12	Todd Valentic	
#			Initial implementation
#
############################################################################

from 	Transport	import ProcessClient

import	os
import	sys
import	random

class CreateData(ProcessClient):

	def __init__(self,argv):

		ProcessClient.__init__(self,argv)

		self.rate 	= self.getDeltaTime('rate',60)
		self.path	= self.get('output.path','')
		self.names	= self.get('output.names','').split()

		if self.names==[]:
			self.abort('You need to specify at least one output name (output.names)')

	def run(self):

		while self.running:

			for name in self.names:

				filename = os.path.join(self.path,name)

				path = os.path.dirname(filename)

				if path and not os.path.exists(path):
					try:
						os.makedirs(path)
					except:
						self.log.exception('Problem creating output path')
						self.abort('Exiting')
				
				try:
					numbytes = int(random.random()*10000)
					open(filename,'w').write('.'*numbytes)
					self.log.info('Created file: %s (%d bytes)'%(filename,numbytes))
				except:
					self.log.exception('Problem creating file')
	
				self.wait(self.rate)


if __name__ == '__main__':
	CreateData(sys.argv).run()

