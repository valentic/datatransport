#!/usr/bin/env python
"""Directory Connect"""

##########################################################################
#
#   XMLRPC Directory Connect
#
#   Connect to the XMLRPC directory service. It will block on startup
#   until connection to the service is established.
#
#   2005-11-09  Todd Valentic
#               Initial implementation.
#
#   2006-07-07  Todd Valentic
#               Added wait at connect. This ensures services
#                   are running when needed.
#
#   2006-09-16  Todd Valentic
#               Added nowait option for foriegn services.
#
#   2006-10-20  Todd Valentic
#               Only print out connected message if waiting.
#
#   2007-04-14  Todd Valentic
#               Set allow_none in connect().
#
#   2009-03-17  Todd Valentic
#               Added async connection option.
#
#   2020-03-09  Todd Valentic
#               Python3: xmlrpc.client
# 		        Change async to defer (async is now a keyword in Python3)
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               Default to allow None and builtin types
#               No longer a mixin
#
##########################################################################

import xmlrpc.client

from .utilities import xmlrpcdeferred


class Directory:
    """Add methods to connect to the XMLRPC directory service"""

    def __init__(self, parent):
        self.parent = parent

        url = parent.config.get("directory.url")
        kwargs = {"allow_none": True, "use_builtin_types": True}
        self.directory = xmlrpc.client.ServerProxy(url, **kwargs)

        # Wait for the directory service to become ready

        self._waiton(self.directory, "directory")

    def _waiton(self, service, label):
        """Wait until the service is ready"""

        waiting = False
        parent = self.parent

        while parent.is_running():
            try:
                service.ident()
                if waiting:
                    parent.log.info(f"Service '{label}' is ready")
                break
            except:  # pylint: disable=bare-except
                waiting = True
                parent.log.info(f"Waiting for service '{label}' to start")
                parent.wait(2)

    def connect(self, service, defer=False, **kw):
        """Connect to an XMLRPC service via the directory"""

        args = {"allow_none": True, "use_builtin_types": True}

        if defer:
            args["transport"] = xmlrpcdeferred.AsyncTransport()

        args.update(kw)

        url = self.directory.get(service, "url")
        server = xmlrpc.client.ServerProxy(url, **args)
        hold = self.directory.get(service, "hold")

        if hold and not defer:
            self._waiton(server, service)
        else:
            self.parent.log.info(f"Assuming service {service} is ready")

        return server

    def get(self, service, option):
        """Proxy directory service get method"""
        return self.directory.get(service, option)

    def __call__(self, *pos, **kw):
        return self.connect(*pos, **kw)
