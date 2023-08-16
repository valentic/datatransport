#!/usr/bin/env python
"""Scheduler Component"""

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
import importlib
import sys

from datatransport import ProcessClient
from datatransport import ConfigComponent
from datatransport.utilities import datefunc


class SchedulerEvent(ConfigComponent):
    """Event Component"""

    def __init__(self, *p, **kw):
        ConfigComponent.__init__(self, "event", *p, **kw)
        self.startearly = self.config.get_boolean("startearly", False)

    def startup(self):
        """Start handler"""

    def shutdown(self):
        """Stop handler"""

    def run(self, endtime):
        """Run handler"""


class Scheduler(ProcessClient):
    """Scheduler Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.rate = self.config.get_rate("repeat", 60)
        self.exit_on_error = self.config.get_boolean("exit_on_error", False)

        self.events = self.config.get_components("events", factory=self.event_factory)
        self.schedule = []

        lines = self.config.get_list("schedule", sep="\n")

        for lineno, entry in enumerate(lines):
            try:
                start, duration, name = entry.split("|")
                start = datefunc.parse_timedelta(start)
                duration = datefunc.parse_timedelta(duration)
                name = name.strip()
            except ValueError as err:
                self.log.error("Failed to parse schedule at line %d", lineno + 1)
                self.log.error(entry)
                self.log.error(str(err))
                self.abort()

            try:
                self.schedule.append((start, duration, self.events[name]))
            except KeyError:
                self.abort("Unkown event: %s", name)

        self.log.info("Repeat: %s", self.rate)

        self.log.info("Schedule:")

        for start, duration, name in self.schedule:
            self.log.info("  %s: %s - %s", name, start, start + duration)

    def event_factory(self, name, config, parent):
        """Create an event component"""

        key = config.get(f"event.{name}.type")
        key = config.get("event.default.type", key)
        key = config.get("event.*.type", key)

        module_name, method_name = key.rsplit(".", 1)

        module = importlib.import_module(module_name)

        return getattr(module, method_name)(name, config, parent)

    def event_cycle(self):
        """Single cycle throuth events in a schedule"""

        period = self.rate.period.total_seconds()

        for start_offset, duration, event in self.schedule:
            now = self.now()
            cycle_offset = datetime.timedelta(seconds=now.timestamp() % period)
            cycle_start = now - cycle_offset
            end_offset = start_offset + duration

            self.log.debug("Next event: %s", event.name)
            self.log.debug("cycle time: %s", cycle_offset)
            self.log.debug("start time: %s", start_offset)
            self.log.debug("end   time: %s", end_offset)

            if not event.startearly and cycle_offset < start_offset:
                self.log.debug("  waiting")
                if not self.wait(start_offset - cycle_offset):
                    return False

            self.log.info("Processing %s", event.name)

            if cycle_offset >= end_offset:
                self.log.info("  skipping, past end time")
                continue

            try:
                event.run(cycle_start + end_offset)
            except Exception as err:    # pylint: disable=broad-exception-caught
                if self.exit_on_error:
                    self.log.exception("Problem running event")
                    return False
                self.log.error("Problem running event: %s", err)

            self.log.info("  finished action for %s", event.name)

        return True

    def main(self):
        """Main application"""

        for event in self.events.values():
            event.startup()

        while self.wait(self.rate):
            self.log.info("---- Starting event cycle ----")

            if not self.event_cycle():
                break

            self.log.info("=" * 35)

        for event in self.events.values():
            event.shutdown()


def main():
    """Script entry point"""
    Scheduler(sys.argv).run()
