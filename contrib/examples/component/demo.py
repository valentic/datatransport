#!/usr/bin/env python
"""Test Config Components"""

##############################################################
#
#   ConfigComponents Demonstration
#
#   2004-02-01  Todd Valentic
#               Initial implementation.
#
#   2022-11-04  Todd Valentic
#               Updated for Python3
#
##############################################################

import sys

from datatransport import ProcessClient
from datatransport import ConfigComponent
from datatransport import NewsPoster


class Watch(ConfigComponent):
    """Component Class"""

    def __init__(self, name, config, parent, **kw):
        ConfigComponent.__init__(self, "watch", name, config, parent, **kw)

        self.news_poster = NewsPoster(self)

        self.path = self.config.get_path("path", ".")
        self.label = self.config.get("label", "")
        self.host = self.config.get("host", "")
        self.option = self.config.get("option", "")
        self.desc = self.config.get("desc", "")
        self.subject = self.config.get("subject", "")

        self.log.info("Component: %s", self.name)
        self.log.info("  path:    %s", self.path)
        self.log.info("  label:   %s", self.label)
        self.log.info("  host:    %s", self.host)
        self.log.info("  option:  %s", self.option)
        self.log.info("  desc:    %s", self.desc)
        self.log.info("  subject: %s", self.subject)
        self.log.info("  options: %s", self.config.options())


class Demo(ProcessClient):
    """Parent Class"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.components = self.config.get_components("watches", factory=Watch)

        self.log.info("Loaded %d components:", len(self.components))

        for name in self.components:
            self.log.info("  %s", name)

if __name__ == "__main__":
    Demo(sys.argv).run()
