#!/usr/bin/env python

from Transport	import ProcessClient

import sys

class Demo (ProcessClient):

	def __init__(self,args):
		ProcessClient.__init__(self,args)

		self.log.info('space.none:    %d' % self.getBytes('space.none'))
		self.log.info('space.bytes:   %d' % self.getBytes('space.bytes'))
		self.log.info('space.kbytes:  %d' % self.getBytes('space.kbytes'))
		self.log.info('space.mbytes:  %d' % self.getBytes('space.mbytes'))
		self.log.info('space.gbytes:  %d' % self.getBytes('space.gbytes'))
		
		self.log.info('nospace.none:    %d' % self.getBytes('nospace.none'))
		self.log.info('nospace.bytes:   %d' % self.getBytes('nospace.bytes'))
		self.log.info('nospace.kbytes:  %d' % self.getBytes('nospace.kbytes'))
		self.log.info('nospace.mbytes:  %d' % self.getBytes('nospace.mbytes'))
		self.log.info('nospace.gbytes:  %d' % self.getBytes('nospace.gbytes'))

		self.log.info('bad.none:    %d' % self.getBytes('bad.none'))
		self.log.info('bad.bytes:   %d' % self.getBytes('bad.bytes'))
		self.log.info('bad.kbytes:  %d' % self.getBytes('bad.kbytes'))
		self.log.info('bad.mbytes:  %d' % self.getBytes('bad.mbytes'))

	def run(self):

		while self.wait(60):
			pass

if __name__ == '__main__':
	Demo(sys.argv).run()
