#!/usr/bin/env python

##############################################################
#
#   ConfigComponents Demonstration
#
#   1.0.0   2004-02-01  Todd Valentic
#           Initial implementation.
#
##############################################################

from Transport import ProcessClient
from Transport import ConfigComponent
from Transport import NewsPostMixin

import sys

class Watch(ConfigComponent,NewsPostMixin):

    def __init__(self,name,parent):
        ConfigComponent.__init__(self,'watch',name,parent)
        NewsPostMixin.__init__(self)

        self.path    = self.get('path','.')
        self.label   = self.get('label','')
        self.host    = self.get('host','')
        self.option  = self.get('option','')
        self.desc    = self.get('desc','')
        self.subject = self.get('subject','')

        self.log.info('Component: %s' % name)
        self.log.info('  path:    %s' % self.path)
        self.log.info('  label:   %s' % self.label)
        self.log.info('  host:    %s' % self.host)
        self.log.info('  option:  %s' % self.option)
        self.log.info('  desc:    %s' % self.desc)
        self.log.info('  subject: %s' % self.subject)

class Demo(ProcessClient):

    def __init__(self,args):
        ProcessClient.__init__(self,args)

        self.components = self.getComponents('watches',Watch)

    def run(self):
        self.exit()

if __name__ == '__main__':
    Demo(sys.argv).run()

