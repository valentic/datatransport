#!/usr/bin/env python2


from Transport import ProcessClient
from Transport import NewsPollMixin

class CheckDate(ProcessClient,NewsPollMixin):

	def __init__(self,argv):
		ProcessClient.__init__(self,argv)
		NewsPollMixin.__init__(self,processFiles=self.process)

	def process(self,

if __name__ == '__main__':
	CheckDate(sys.argv).run()
