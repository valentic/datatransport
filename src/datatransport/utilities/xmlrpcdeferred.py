#!/usr/bin/env python

###################################################################
#
#   Asynchronous XML-RPC client
#
#   This code is a modified version of that posted by A.M. Kichling
#   in the pygtk mailing list [1]. While his was using GTK's async
#   IO handling, I needed something based on asyncore. The changes
#   are pretty small.
#
#   The basic idea is that we provide a custom transport object
#   to the XML-RPC client interface. When the XML-RPC call is 
#   made, instead of reading back the results in a blocking socket,
#   we schedule a "deferred" object. These objects are similar
#   to what Twisted provides, and in this case, they are asyncore
#   dispatcher objects. The main polling loop runs until all of
#   scheduled objects have finished. You can call asyncore.loop()
#   and block or you can have it return periodically if you need
#   to do other work in the meantime.
#
#   The result of the XML-RPC call is accessed through the value
#   property. If the call is complete, it will return the results.
#   If an exception was detected, it will be raised instead.
#
#   When searching for approaches to this problem, I found reference
#   to updating xmlrpc's transport with the more modern
#   HTTPConnection [2]. I haven't implmented this yet. Do we need
#   to do it?
#
#   [1] http://www.mail-archive.com/pygtk@daa.com.au/msg12971.html
#   [2] http://itkovian.net/base/transport-class-pythons-xml-rpc-lib
#
#   2009-03-17  Todd Valentic
#               Initial implementation.
#
#   2020-10-09  Todd Valentic
#               Python3: xmlrpc.client
#
###################################################################

import asyncore
import xmlrpc.client
import socket

class XMLRPCDeferred(asyncore.dispatcher):
    """Object representing the delayed result of an XML-RPC request.

    .is_ready: bool
      True when the result is received; False before then.
    .value : any
      Once is_ready=True, this attribute contains the result of the
      request. If this value is an instance of the xmlrpc.client.Fault
      class, then some exception occurred during the request's
      processing. You can use the getValue() method to extract
      the value and raise an exception if a Fault is found.
      
    """
    
    def __init__ (self, transport, http):
        asyncore.dispatcher.__init__(self,http._conn.sock) 

        self.transport = transport
        self.http = http
        self._value = None
        self.is_ready = False

    def writable (self):
        return False

    def readable (self):
        return not self.is_ready

    def handle_close (self):
        self.close()

    def handle_read (self):

        # We assume that the entire reply is ready.
        # Switch back to blocking so we can pick up all the parts.

        self.socket.setblocking(1)
        errcode, errmsg, headers = self.http.getreply()

        if errcode != 200:
            raise ProtocolError(
                host + handler,
                errcode, errmsg,
                headers
                )

        try:
            result = xmlrpc.client.Transport._parse_response(
                        self.transport,
                        self.http.getfile(), 
                        None)[0]
        except xmlrpc.client.Fault(exc):
            result = exc
            
        self.__value = result
        self.is_ready = True
        self.close()

    def __len__ (self):
        # XXX egregious hack!!!
        # The code in xmlrpc.client.ServerProxy calls len() on the object
        # returned by the transport, and if it's of length 1 returns
        # the contained object.  Therefore, this __len__ method
        # returns a completely fake length of 2.
        return 2 

    def get_value (self):
        # if the value is an XML-RPC fault, raise an exception.

        if not self.is_ready:
            raise IOError('Result not ready')

        if isinstance(self.__value,xmlrpc.client.Fault):
            raise xmlrpc.client.Fault(self.__value)

        return self.__value

    def set_value (self,value):
        self.__value = value

    value = property(get_value,set_value)
    
        
class AsyncTransport (xmlrpc.client.Transport):

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        self.send_request(h, handler, request_body)
        self.send_host(h, host)
        self.send_user_agent(h)
        self.send_content(h, request_body)

        self.verbose = verbose

        return XMLRPCDeferred(self, h)


if __name__ == '__main__':

    hosts = ['firewall']

    for udu in range(1,9):
        hosts.append('udu%d.face1' % udu)
    
    results = []

    for host in hosts:

        url = 'http://%s.amisr.net:8200' % host
        t = AsyncTransport()
        s = xmlrpc.client.ServerProxy(url,t)
        results.append(s.network_scan())

    print('queries are launched, waiting to finish...')

    asyncore.loop()

    hosts = {}

    for result in results:
        hosts.update(result.value)

    for host in sorted(hosts):
        try:
            hostname = socket.gethostbyaddr(host)[0].replace('.amisr.net','')
        except:
            hostname = ''
        print('[%s]  %-16s  %s' % (hosts[host],host,hostname))


