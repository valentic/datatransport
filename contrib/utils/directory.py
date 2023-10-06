###################################################################
#
#   Stand alone access to transport directory services
#
#   2005-11-11  Todd Valentic
#               Initial implementation.
#
#   2023-10-06  Todd Valentic
#               Updated for python3 / transport3
#
###################################################################

import xmlrpc.client

class Directory:
    """Connect to xmlrpc directory service"""

    def __init__(self,host='localhost', port=8411, service=None):

        kwargs = {"allow_none": True, "use_builtin_types": True}

        url = 'http://%s:%d' % (host,port)
        self.directory = xmlrpc.client.ServerProxy(url, **kwargs)

        if service:
            self.directory = self.connect(service)

    def list(self):
        return self.directory.list()

    def connect(self, service, **kwargs):
        """Connect to a service via the directory"""

        args = {"allow_none": True, "use_builtin_types": True}

        args.update(kwargs)

        url = self.directory.get(service, "url")
        server  = xmlrpc.client.ServerProxy(url, **args)

        return server

        

