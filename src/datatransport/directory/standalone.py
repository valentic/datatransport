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
#   2026-04-20  Todd Valentic
#               Use base class defaults
#
##########################################################################

import logging
import time
from .base import BaseDirectory


class Directory(BaseDirectory):
    """Directory connector for use by standalone applications"""

    def __init__(self, host="localhost", port=8411, **kwargs):
        super().__init__(f"http://{host}:{port}", **kwargs)


def connect(service_name, *pos, **kw):
    """Forward connect() call to StandaloneDirectory"""
    return Directory(*pos, **kw).connect(service_name)
