#!/usr/bin/env python3
"""Directory Service"""

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
#   2023-07-27  Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import sys

from datatransport import ProcessClient
from datatransport import ConfigComponent
from datatransport import XMLRPCServer


class Service(ConfigComponent):
    """Service Component"""

    def __init__(self, name, config, parent, **kw):
        ConfigComponent.__init__(self, "service", name, config, parent, **kw)

        self.host = self.config.get("host", "localhost")
        self.port = self.config.get_int("port")
        self.scheme = self.config.get("scheme", "http")
        self.label = self.config.get("label")
        self.url = f"{self.scheme}://{self.host}:{self.port}"
        self.hold = self.config.get_boolean("hold", True)

        if not self.port:
            raise ValueError("No port specified")


class DirectoryService(ProcessClient):
    """Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        port = self.config.get_int("directory.port", 8411)

        self.xmlserver = XMLRPCServer(
            self, queue_size=100, port=port, label="Directory"
        )
        self.main = self.xmlserver.main

        self.xmlserver.register_function(self.list)
        self.xmlserver.register_function(self.lookup, "get")

        self.services = self.config.get_components("services", factory=Service)

        self.log.info("Services:")
        for service in self.services.values():
            self.log.info("  - %s (%s:%s)", service.label, service.host, service.port)

    def list(self):
        """List services"""

        return list(self.services)

    def lookup(self, name, key):
        """Lookup data on service component"""

        if name in self.services:
            return getattr(self.services[name], key)

        raise KeyError(f"Unknown service: {name}")


def main():
    DirectoryService(sys.argv).run()
