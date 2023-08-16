#!/usr/bin/env python3

from datatransport.apps import SchedulerEvent 

class BuildingEvent(SchedulerEvent):

    def __init__(self, *p, **kw):
        SchedulerEvent.__init__(self, *p, **kw)

        self.label = self.config.get("label")

    def run(self, endtime):
        self.log.info("Run: %s %s", self.label, endtime)

