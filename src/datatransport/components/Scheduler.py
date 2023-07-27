#!/usr/bin/env python

#############################################################################
#
#   Scheduler Process Client
#
#   Execute events at regular intervals. The schedule is defined in
#   the configuration file. Events are listed, one per line, in the
#   'events' parameter. Each line has a start time, duration, and
#   event name, separated by a the '|' character:
#
#   events:     00:00   |   00:45       | call-remote-1
#               05:00   |   00:45       | call-remote-2
#
#   The times are relative (timedelta) from the start of the event
#   sequence. The entire sequence is repeated at a rate defined by the
#   repear.* parameters.
#
#   The individual events are listed as 'event.<name>.<parameter>' The
#   specific parameters are dependent on the event types. Events are
#   objects that inherit from the Event class. An application would
#   provide it's own Event classes, passed in as the EventFactory
#   object to the Schedule init. Event object must support three
#   methods:
#
#       start   - called once at program startup
#       run     - called each time the event is scheduled
#       stop    - called once on exit
#
#   2005-04-07  Todd Valentic
#               Initial implementation.
#
#   2005-04-19  Todd Valentic
#               Added ability to start in mid-event sequence
#
#   2005-06-08  Todd Valentic
#               Added ability to start events early. This is useful
#                   in cases where multiple events are stacked up
#                   and some take less then there alloted time. It
#                   gives the extra time to the next event. Each
#                   event can be individually controlled, so those
#                   that need to happen at exact times still can.
#                   Even though an event may start early, it still
#                   runs until it's original end time.
#
#   2007-07-14  Todd Valentic
#               Computed offset in the wrong direction. Fixed.
#
#   2008-07-25  Todd Valentic
#               Add small offset in waituntil() to prevent problems
#                   due to small rounding errors.
#
#   2008-08-15  Todd Valentic
#               Still having problems with waituntil(). Now using
#                   a more robust scheme that will continue to
#                   retry/sleep until the target time is reached.
#
#   2009-11-24  Todd Valentic
#               Use currentTime()
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#
#   2023-07-26  Todd Valentic
#               Updated for transport3 / python3
#
#############################################################################

import datetime
import sys

from datatransport import ProcessClient
from datatransprot import ConfigComponent
from datatransport.utilities import datefunc


class Event(ConfigComponent):
    def __init__(self, name, parent):
        ConfigComponent.__init__(self, "event", name, parent)
        self.startearly = self.config.get_boolean("startearly", False)

    def __getrunning(self):
        return self.parent.running

    running = property(__getrunning)

    def start(self):
        pass

    def stop(self):
        pass

    def run(self, endtime):
        pass


class Scheduler(ProcessClient):
    def __init__(self, argv, EventFactory):
        ProcessClient.__init__(self, argv)

        self.rate = self.config.get_timedelta("repeat.rate", 60)
        self.offset = self.config.get_timedelta("repeat.offset")
        self.sync = self.config.get_boolean("repeat.sync", True)
        self.whole = self.config.get_boolean("repeat.whole", False)
        self.exit_on_error = self.config.get_boolean("exitOnError", False)

        self.events = {}
        self.schedule = []

        for entry in self.config.get("repeat.events").split("\n"):

            try:
                start, duration, name = entry.split("|")

                start = datefunc.parse_timedelta(start)
                duration = datefunc.parse_timedelta(duration)
                name = name.strip()

                if name not in self.events:
                    self.events[name] = EventFactory(name, self)

                self.schedule.append((start, duration, name))

            except:
                self.log.exception("Problem parsing event")
                self.abort()

        self.log.info("Repeat rate  : %s" % self.rate)
        self.log.info("Repeat offset: %s" % self.offset)
        self.log.info("Repeat sync  : %s" % self.sync)
        self.log.info("Repeat whole : %s" % self.whole)

        self.log.info("Schedule:")

        for start, duration, name in self.schedule:
            self.log.info("  %s: %s - %s" % (name, start, start + duration))

    def waituntil(self, starttime):

        # Sometimes small rounding errors creep in, so spin
        # around until we are really at the target time

        while self.now() < starttime:
            if not self.wait(starttime - self.now()):
                return False

        return True

    def main(self):

        for event in self.events.values():
            event.start()

        error = False

        if self.sync and self.whole:
            self.log.info("Waiting to sync whole event sequence")
            self.wait(self.rate, self.offset, self.sync)
        else:
            self.log.info("Starting in middle of event sequence")

        while not error and self.is_running():

            basetime = self.now()

            if self.sync:
                rate = self.rate.total_seconds()
                inset = datetime.timedelta(seconds=basetime.timestamp() % rate)
                basetime = basetime - inset + self.offset

            self.log.info("---- Starting event cycle ----")

            for start, duration, name in self.schedule:

                event = self.events[name]
                starttime = basetime + start
                endtime = starttime + duration

                self.log.info("start time: %s" % starttime)
                self.log.info("end   time: %s" % endtime)

                if not event.startearly:
                    if not self.waituntil(starttime):
                        break

                self.log.info("Processing %s" % name)

                if self.now() >= endtime:
                    self.log.info("  past end time, skipping")
                    continue

                try:
                    event.run(endtime)
                except:
                    self.log.exception("Problem running event")
                    if self.exit_on_error:
                        error = True
                        break

                self.log.info("  finished action for %s" % name)

            self.log.info("=" * 35)

            self.wait(self.rate, self.offset, self.sync)
            self.wait(1)

        for event in self.events.values():
            event.stop()

        if error:
            self.abort()


def main():
    Scheduler(sys.argv).run()
