#!/usr/bin/env python

##########################################################################
#
#   Directory Service
#
#   The directory is used to return information about the
#   various services. It is used primarily in bootstraping
#   by client programs. Based on AMISR directory service.
#
#   2005-11-08  Todd Valentic
#               Initial implementation.
#
#   2006-06-14  Todd Valentic
#               Add label to XMLRPCServerMixin call
#
#   2006-09-16  Todd Valentic
#               Added hold to Service.
#
#   2007-08-19  Todd Valentic
#               Allow directory port to be set.
#
#   2013-01-30  Todd Valentic
#               Make sure port has a value.
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#
##########################################################################

import os
import sys

from datatransport import ProcessClient
from datatransport import ConfigComponent
from datatransport import XMLRPCServer


class Service(ConfigComponent):
    def __init__(self, name, config, parent, **kw):
        ConfigComponent.__init__(self, "service", name, config, parent, **kw)

        self.host = self.get("host", "localhost")
        self.port = self.get_int("port")
        self.label = self.get("label")
        self.url = "http://%s:%s" % (self.host, self.port)
        self.hold = self.get_boolean("hold", True)

        if not self.port:
            raise ValueError("No port specified")


class DirectoryService(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        port = self.get_int("directory.port", 8411)

        self.xmlserver = XMLRPCServer(self, 
            queue_size=100, port=port, label="Directory"
        )
        self.main = self.xmlserver.main

        self.xmlserver.register_function(self.list)
        self.xmlserver.register_function(self.lookup, "get")

        self.services = self.get_components("services", factory=Service)

        self.log.info("Services:")
        for service in self.services.values():
            self.log.info(f"  - {service.label} ({service.host}:{service.port})")

    def list(self):
        return list(self.services)

    def lookup(self, name, key):

        if name in self.services:
            return getattr(self.services[name], key)

        raise KeyError("Unknown service: %s" % name)


def main():
    DirectoryService(sys.argv).run()
