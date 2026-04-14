#!/usr/bin/env python
"""Directory Connect"""

##########################################################################
#
#   XMLRPC Directory Connector
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
#   2026-04-13  Todd Valentic
#               Split into base, framework and standalone versions
#
##########################################################################

import http.client
import socket
import xmlrpc.client

from datatransport.utilities import xmlrpcdeferred

class TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, *args, **kw):
        super().__init__(*args, **kw)
        self.timeout = timeout

    def make_connection(self, host):
        # HTTPConnection with timeout
        return http.client.HTTPConnection(host, timeout=self.timeout)

class BaseDirectory:
    """Add methods to connect to the XMLRPC directory service"""

    def __init__(self, url, log, wait, is_running, timeout=15):
        self.log = log
        self.wait = wait
        self.is_running = is_running
        self.timeout = timeout

        self.directory = xmlrpc.client.ServerProxy(
            url, allow_none=True, use_builtin_types=True,
            transport=TimeoutTransport(timeout=timeout)
        )

        # Wait for the directory service to become ready

        self.wait_until_ready(self.directory, "directory")

    def wait_until_ready(self, service, label):
        """Wait until the service is ready"""

        ready = False
        report = True

        while not ready and self.is_running():
            try:
                service.ident()
                ready = True
            except Exception as e:
                if report:
                    self.log.info("Waiting for service '%s' to start", label)
                    report = False
                self.log.debug(e)
                self.wait(2)

        if ready:
            self.log.info("Service '%s' is ready", label)

    def connect(self, service, defer=False, **kw):
        """Connect to an XMLRPC service via the directory"""

        kwargs = {"allow_none": True, "use_builtin_types": True}

        if defer:
            kwargs["transport"] = xmlrpcdeferred.AsyncTransport()
        else:
            kwargs["transport"] = TimeoutTransport(timeout=self.timeout)

        kwargs.update(kw)

        url = self.directory.get(service, "url")
        server = xmlrpc.client.ServerProxy(url, **kwargs)
        hold = self.directory.get(service, "hold")

        if hold and not defer:
            self.wait_until_ready(server, service)
        else:
            self.log.info("Assuming service %s is ready", service)

        return server

    def get(self, service, option):
        """Proxy directory service get method"""
        return self.directory.get(service, option)

