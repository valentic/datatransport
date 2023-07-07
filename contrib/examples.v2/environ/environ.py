#!/usr/bin/env python

############################################################################
#
#	Environ	
#
#	This script displays the environment variables is sees at startup. 
#
#	History:
#	
#	1.0.0 	2002-12-19	Todd Valentic	
#			Initial implementation
#
############################################################################

from 	Transport	import ProcessClient

import	sys
import	os

class Environ (ProcessClient):

	def __init__(self,argv):
		ProcessClient.__init__(self,argv)

		self.printEnviron()

	def printEnviron(self):

		self.log.info('Current Environment:')

		keys = os.environ.keys()
		keys.sort()

		for key in keys:
			self.log.info('%s = %s' % (key,os.environ[key]))

	def run(self):

		while self.wait(60): 
			pass

if __name__ == '__main__':
	Environ(sys.argv).run()

