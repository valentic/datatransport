#!/usr/bin/env python
"""Test Inherited init()"""

##############################################################
#
#   Test init() call chain in inherited classes
#
#   2023-07-03  Todd Valentic
#               Initial implementation.
#
##############################################################

import sys

from datatransport import Root, ProcessClient


class MixinA(Root):
    """Mixin class A"""

    def init(self):
        super().init()
        self.log.info("MixinA.init()")


class MixinB(Root):
    """Mixin class B"""

    def init(self):
        super().init()
        self.log.info("MixinB.init()")


class Demo(MixinA, MixinB, ProcessClient):
    """Parent Class"""

    def __init__(self, args, **_kwargs):
        ProcessClient.__init__(self, args)
        MixinA.__init__(self)
        MixinB.__init__(self)

        self.log.info("Demo.mro(): %s", Demo.mro())

    def init(self):
        super().init()

        self.log.info("Demo.init()")


if __name__ == "__main__":
    Demo(sys.argv).run()
