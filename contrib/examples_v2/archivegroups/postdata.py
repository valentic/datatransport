#!/usr/bin/env python2

from Transport 		import ProcessClient
from Transport 		import NewsPostMixin
from Transport.Util	import removeFile
from mx 			import DateTime

import sys
import os

class PostData(ProcessClient,NewsPostMixin):
	
	def __init__(self,argv):
		ProcessClient.__init__(self,argv)
		NewsPostMixin.__init__(self)

		self.pollrate	= self.getint('pollrate',60)
		self.filenames	= self.get('filenames','msg.txt').split()

	def run(self):
		
		counter=0

		while self.running:

			curdate	= DateTime.now()

			postnames = []

			for filename in self.filenames:

				filename = curdate.strftime(filename)
				name,ext = os.path.splitext(filename)

				message = 'Index: %d\n' % counter

				name,ext = os.path.splitext(filename)

				if ext=='.zip':
					open(name,'w').write(message)
					os.system('zip -o -qq %s %s' % (filename,name))
					os.remove(name)
				elif ext=='.gz':
					open(name,'w').write(message)
					os.system('gzip -f %s' % name)
				elif ext=='.bz2':
					open(name,'w').write(message)
					os.system('bzip2 -f %s' % name)
				else:
					open(filename,'w').write(message)

				postnames.append(filename)

			counter+=1

			self.log.info('Posting files: %s' % postnames)

			self.newsPoster.post(postnames)
			removeFile(postnames)

			self.wait(self.pollrate)

if __name__ == '__main__':
	PostData(sys.argv).run()
	
