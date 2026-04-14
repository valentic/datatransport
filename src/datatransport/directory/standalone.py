#!/usr/bin/env python
"""Standalong Directory Connect"""

##########################################################################
#
#   XMLRPC Directory Connector for standalone applications 
#
#   Connect to the XMLRPC directory service. It will block on startup
#   until connection to the service is established.
#
#   2026-04-13  Todd Valentic
#               Initial implementation.
#
##########################################################################

import logging
import time
from .base import BaseDirectory

class Directory(BaseDirectory):
    """Directory connector for use by standalone applications"""

    def __init__(self, host="localhost", port=8411, log=None, wait=time.sleep, is_running=None):
        url = f"http://{host}:{port}"
        if log is None:
            log = logging.getLogger()
        wait = wait 
        if is_running is None:
            is_running = lambda: True
        super().__init__(url, log, wait, is_running)

def connect(service_name, *pos, **kw):
    """Forward connect() call to StandaloneDirectory"""
    return Directory(*pos, **kw).connect(service_name)

