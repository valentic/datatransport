#!/usr/bin/env python
"""ConfigComponent"""

##########################################################################
#
#   ConfigComponent
#
#   DataTransport version of the Sapphire ConfigComponent.
#
#   2023-06-28  Todd Valentic
#               Initial implementation. Based on transport v2 version.
#
##########################################################################

from functools import partial
from .accessmixin import AccessMixin

import sapphire_config as sapphire


class ComponentLog:
    """Prefix log entries with the component name"""

    def __init__(self, name, log):
        self.name = name
        self.log = log

    def __getattr__(self, name):
        def inner(msg, *args):
            fn = getattr(self.log, name)
            fn(f"[{self.name}] {msg}", *args)

        return inner


class ConfigComponent(sapphire.Component, AccessMixin):
    """Component class for config file entries"""

    # pylint: disable=too-many-arguments

    def __init__(self, prefix, name, config, parent, **kw):
        sapphire.Component.__init__(self, prefix, name, config, parent, **kw)
        AccessMixin.__init__(self, parent)

        self.log = ComponentLog(f"{prefix}.{name}", parent.log)

        self.config.get_components = partial(self.config.get_components, parent=self)
