#!/usr/bin/env python
"""Test confif parser get_bytes"""

##########################################################################
#
#   Test get_bytes config settings
#
#   2022-11-02  Todd Valentic
#               Initial implementation
#
##########################################################################

import sys

from datatransport import ProcessClient


class Demo(ProcessClient):
    """Test program"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        for key in self.options():
            if key.startswith('test.'):
                try:
                    self.log.info("%s: %s", key, self.config.get_bytes(key))
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.log.error('Problem parsing %s: %s', key, e)

if __name__ == "__main__":
    Demo(sys.argv).run()
