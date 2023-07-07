#!/usr/bin/env python2

############################################################################
#
#	Spawner	
#
#	This script runs child process at specified intervals 
#
#	History:
#	
#	1.0.0 	2002-12-19	Todd Valentic	
#			Initial implementation
#
############################################################################

from 	Transport	import ProcessClient

import	sys
import 	commands

class Spawner (ProcessClient):

	def __init__(self,argv):
		ProcessClient.__init__(self,argv)

	def run(self):

		rate	= self.getint('spawn.rate',10)
		cmd		= self.get('spawn.command','pwd')

		while self.running:

			self.log.info('Running command: %s' % cmd)

			try:
				status,output = commands.getstatusoutput(cmd)	
			except:
				self.log.exception('Problem starting child')
				self.abort('Exiting')

			self.log.info('  Status=%d' % status)
			self.log.info('  Output=%s' % output)

			self.wait(rate)

if __name__ == '__main__':
	Spawner(sys.argv).run()

