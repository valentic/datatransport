#!/usr/bin/env python3
"""Transport XMLRPC Service"""

##########################################################################
#
#   Transport XLMRPC Service
#
#   This is the base class for the different XML-RPC based services
#   used in the transport network. It interfaces with the directory
#   service to bootstrap the local server.
#
#   2005-11-09  Todd Valentic
#               Initial implementation.
#
#   2006-01-22  Todd Valentic
#               Added intospection registration
#
#   2006-02-25  Todd Valentic
#               Added idle function and timeout.
#
#   2006-06-14  Todd Valentic
#               Use label in directory server for ident.
#
#   2006-07-17  Todd Valentic
#               Added try..except around request handle to catch
#                   connection breaks.
#
#   2016-07-10  Todd Valentic
#               Python 2.6+ has a more sophisticated serve_forver()
#                   loop that ensures system calls complete and thus
#                   results in the old implementation blocking forever.
#                   Now we handle both the older and newer versions.
#
#   2016-10-31  Todd Valentic
#               Modify previous change to work on Python 2.4 as well.
#
#   2016-11-08  Todd Valentic
#               Remove call to undefined shutdown() method.
#               Fix type in assignment for server_forever for < python 2.6
#
#   2017-01-10	Todd Valentic
# 		Restore call to shutdown() method - needed to exit,
# 		    otherwise we deadlock. The function is inherited
# 		    from SimpleXMLRPCServer
#
#   2017-06-08  Todd Valentic
#               Rename ident() function to prevent conflict with
#                   threading.Thread.ident when this class is mixed in with
#                   Thread. This problem showed up in Python 2.6+
#
#   2019-08-06  Todd Valentic
#               Add timeout to RequestHandler
#               Set allow_none
#
#   2020-10-09  Todd Valentic
#               Python3: xmlrpc.server
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#
#   2023-07-04  Todd Valentic
#               Convert from mixin class
#
##########################################################################

import threading
import xmlrpc.client

from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

from . import Directory

SimpleXMLRPCRequestHandler.timeout = 5


class XMLRPCServer(SimpleXMLRPCServer):
    """Data Transport XMLRPC Server"""

    # pylint: disable=too-many-arguments

    def __init__(
        self, parent, queue_size=20, port=None, label=None, callback=None, timeout=1
    ):
        self.parent = parent
        self.callback = callback
        self.timeout = timeout

        if port is None:
            # This is a normal service client

            self.directory = Directory(parent)

            servicename = parent.config.get("service.name")

            if not servicename:
                parent.abort("No service.name found")

            port = self.directory.get(servicename, "port")

            try:
                label = self.directory.get(servicename, "label")
            except xmlrpc.client.Fault:
                label = None

        self.allow_reuse_address = True
        self.request_queue_size = queue_size

        SimpleXMLRPCServer.__init__(
            self, ("", port), allow_none=True, logRequests=False
        )

        self.register_introspection_functions()
        self.register_function(self.my_ident, "ident")
        self.register_function(self.status)

        parent.log.info(f"Listening on port {port}")

        if label:
            self.servicelabel = label
        else:
            self.servicelabel = "No description available"

    def my_ident(self):
        """Service desciption"""
        return self.servicelabel

    def status(self):
        """Indicate active"""
        return 1

    def server_thread(self):
        """Run server in separate thread"""

        try:
            self.serve_forever()
        except:  # pylint: disable=bare-except
            pass
        finally:
            self.server_close()

    def main(self):
        """Run server"""

        self.parent.log.info("Starting operations")

        thread = threading.Thread(None, self.server_thread)
        thread.start()

        while self.parent.wait(self.timeout):
            if self.callback:
                self.callback()

        self.shutdown()
        thread.join()

        self.parent.log.info("Finished")
