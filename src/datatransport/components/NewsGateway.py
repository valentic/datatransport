#!/usr/bin/env python3
"""Newsgroup Gateway Component"""

#########################################################################
#
#   News group gateway service
#
#   This service provides an XML-RPC gateway to news groups.
#   The contents of the latest available message in a group
#   are cached and made available to client programs.
#
#   2007-04-07  Todd Valentic
#               Initial implementation.
#
#   2007-12-06	Todd Valentic
#               Make read() return a JSON representation of the message.
#
#   2009-11-24  Todd Valentic
#               Use currentTime instead of datetime.now()
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               NewsPoller
#
#   2023-07-26  Todd Valentic
#               Updated for transport3 / python3
#
#########################################################################

import pickle
import shelve
import sys

from threading import Thread, Lock
from datetime import datetime
from datetime import timedelta

from datatransport import ProcessClient
from datatransport import XMLRPCServerMixin
from datatransport import NewsPoller
from datatransport import AccessMixin


def synchronized(lock):
    """Lock decorator"""

    def wrap(f):
        def new_function(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()

        return new_function

    return wrap


class Data(AccessMixin):
    """Data cache"""

    lock = Lock()

    def __init__(self, parent):
        AccessMixin.__init__(self, parent)
        self.messages = shelve.open("cache")

    @synchronized(lock)
    def write(self, message):
        """Store message into cache"""

        newsgroup = message["Newsgroups"]
        self.messages[newsgroup] = self.write_handler(newsgroup, message)
        self.messages.sync()

    def write_handler(self, newsgroup, message):
        """What to cache"""
        return message

    @synchronized(lock)
    def clear(self):
        """Clear the cache"""

        self.messages.clear()
        self.messages.sync()

    @synchronized(lock)
    def read(self, newsgroup):
        """Read entry from cache"""
     
     return self.messages[newsgroup]

    @synchronized(lock)
    def list(self):
        """List cache"""
      
      return self.messages.keys()

    @synchronized(lock)
    def get_string(self, newsgroup):
        """Reture message as string"""
       
       return self.messages[newsgroup].as_string()

    @synchronized(lock)
    def unpickle(self, newsgroup):
        """Unpickle message"""
        
        return pickle.loads(self.messages[newsgroup].get_payload())


class Server(Thread, AccessMixin):
    """XMLRPC Server Interface"""

    def __init__(self, parent, data):
        Thread.__init__(self)
        AccessMixin.__init__(self, parent)

        self.xmlserver = XMLRPCServerMixin(self)
        self.main = self.xmlserver.main

        self.setDaemon(True)

        self.data = data

        self.xmlserver.register_function(self.read, "read")
        self.xmlserver.register_function(self.data.unpickle, "unpickle")
        self.xmlserver.register_function(self.data.list, "list")
        self.xmlserver.register_function(self.data.get_string, "message")

        self.add_handlers()

    def add_handlers(self):
        """Used by derived classes to add handlers"""
        return

    def read(self, newsgroup):
        """Read message from newsgroup"""

        message = self.data.read(newsgroup)
        headers = {}
        for key, value in message.items():
            headers[key] = value
        return {"headers": headers, "body": message.get_payload()}


class NewsGateway(ProcessClient):
    """Process Client"""

    def __init__(self, dataFactory, serverFactory, argv):
        ProcessClient.__init__(self, argv)

        self.news_poller = NewsPoller(self, callback=self.process, idle=self.idle)
        self.main = self.news_poller.main

        self.data = dataFactory(self)
        self.timeout = self.config.get_timedelta("timeout")
        self.in_timeout = False

        if self.timeout:
            self.log.info("Timeout set to %s", self.timeout)
            self.next_time = self.now() + self.timeout
        else:
            self.log.info("No timeout set")

        serverFactory(self, self.data).start()

    def process(self, message):
        """Process handler"""

        self.log.info("Set from %s", message["Newsgroups"])
        self.data.write(message)

        if self.timeout:
            self.next_time = self.now() + self.timeout
            self.in_timeout = False

    def idle(self):
        """Idle handler"""

        if self.in_timeout:
            return

        if self.timeout and self.now() > self.next_time:
            self.log.info("timeout reached, clearing values")
            self.data.clear()
            self.in_timeout = True


def main():
    NewsGateway(Data, Server, sys.argv).run()
