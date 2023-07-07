#!/usr/bin/env python

############################################################################
#
#   Config  
#
#   This script tests config file access. 
#
#   History:
#   
#   1.0.0   2005-11-12  Todd Valentic   
#           Initial implementation
#
############################################################################

from    Transport   import ProcessClient

import  sys

class Config (ProcessClient):

    def __init__(self,argv):
        ProcessClient.__init__(self,argv)

    def run(self):

        self.log.info('missing: %s' % self.get('missing','OK: The default value'))
        self.log.info('default: %s' % self.get('value.default'))
        self.log.info('local:   %s' % self.get('value.local'))
        self.log.info('var:     %s' % self.get('value.label',vars={'name':'world'}))

        self.log.info('Finished')

if __name__ == '__main__':
    Config(sys.argv).run()

