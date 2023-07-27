#!/usr/bin/env python
"""Create test data files"""

############################################################################
#
#   CreateData
#
#   This script creates test data files.
#
#   History:
#
#   2002-12-12  Todd Valentic
#               Initial implementation
#
#   2022-11-04  Todd Valentic
#               Update for Python3
#
############################################################################

import random
import sys

from datatransport import ProcessClient
from datatransport.utilities import make_path


class CreateData(ProcessClient):
    """Data Source"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

    def init(self):
        super().init()

        self.rate = self.config.get_rate("rate", 60)
        self.path = self.config.get_path("output.path")
        self.names = self.config.get_list("output.names")
        self.maxbytes = self.config.get_bytes("output.maxsize", "10KB")

        if not self.names:
            self.abort("No output names (output.names)")

    def main(self):
        """Main loop"""

        while self.wait(self.rate):

            for name in self.names:

                filename = self.path / name

                make_path(filename)

                try:
                    numbytes = int(random.random() * self.maxbytes)
                    payload = "." * numbytes
                    filename.write_text(payload)
                    self.log.info("Created file: %s (%d bytes)", filename, numbytes)
                except: # pylint: disable=bare-except
                    self.log.exception("Problem creating file")


if __name__ == "__main__":
    CreateData(sys.argv).run()
