#!/usr/bin/env python3
"""Make Files"""

##########################################################################
#
#   Make test files
#
#   2023-08-13  Todd Valentic
#               Initial implementation
#
##########################################################################

import os
import sys

from pathlib import Path

from datatransport import ProcessClient
from datatransport import ConfigComponent
from datatransport.utilities import size_desc

class DataFile(ConfigComponent):

    def __init__(self, *p, **kw):
        ConfigComponent.__init__(self, 'datafile', *p, **kw)

        self.output_size = self.config.get_bytes('size', '1kb')
        self.output_name = self.config.get_path('filename', 'data.bin') 

    def process(self):
        """Create data file"""

        filename = Path(self.now().strftime(str(self.output_name)))

        filename.parent.mkdir(parents=True, exist_ok=True)

        with filename.open('wb') as output:
            output.write(os.urandom(self.output_size))

        self.log.info("Wrote %s (%s)", filename, size_desc(self.output_size))

class FileMaker(ProcessClient):
    
    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.datafiles = self.config.get_components('datafiles', factory=DataFile)  
        self.rate = self.config.get_rate('rate')

    def main(self):
        """Main application"""

        while self.wait(self.rate):
            
            for datafile in self.datafiles.values():
                datafile.process()


if __name__ == '__main__':
    FileMaker(sys.argv).run()

