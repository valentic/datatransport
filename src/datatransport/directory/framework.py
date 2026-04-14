#!/usr/bin/env python
"""Directory Connect"""

##########################################################################
#
#   ProcessClient Directory connector 
#
#   Used by ProcessClients to connect to the XMLRPC directory service. 
#   It will block on startup until connection to the service is established.
#
#   2026-04-13  Todd Valentic
#               Refactor into BaseDirectory, Directory and standalone 
#
##########################################################################

from .base import BaseDirectory

class Directory(BaseDirectory):
    """Directory connector for use by ProcessClients"""

    def __init__(self, parent):
        url = parent.config.get("directory.url")
        super().__init__(url, parent.log, parent.wait, parent.is_running)

