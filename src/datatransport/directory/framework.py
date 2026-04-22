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
#   2026-04-20  Todd Valentic
#               Pass additional kwargs to base
#
##########################################################################

from .base import BaseDirectory


class Directory(BaseDirectory):
    """Directory connector for use by ProcessClients"""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent.config.get("directory.url"),
            log=parent.log,
            wait=parent.wait,
            is_running=parent.is_running,
            **kwargs,
        )
