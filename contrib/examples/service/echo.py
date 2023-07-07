#!/usr/bin/env python3
"""Demonstrate an XMLRPC Service"""

##########################################################################
#
#   Echo Service
#
#   Example service that simply echos back a message.
#
#   2022-11-02  Todd Valentic
#               Initial implementation
#
##########################################################################

import sys

from datatransport import ProcessClient
from datatransport import XMLRPCServer


class EchoService(ProcessClient):
    """Echo Service"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.xmlserver = XMLRPCServer(self)
        self.main = self.xmlserver.main

        self.xmlserver.register_function(self.emit)

    def emit(self, msg):
        """Return message to caller"""

        self.log.info("Emit message '%s'", msg)
        return msg


if __name__ == "__main__":
    EchoService(sys.argv).run()
