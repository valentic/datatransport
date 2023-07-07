############################################################
#
#   Event Monitor
#
#   2009-03-14  Todd Valentic
#               Initial implementation.
#
#   2010-03-22  Todd Valentic
#               Allow member section name to be specified
#
#   2013-02-08  Todd Valentic
#               Make sure to see if section exists when
#                   loading compontent from saved state.
#
#   2016-12-23  Todd Valentic
#               Use datetime.timezone.utc
#
#   2022-10-19  Todd Valentic
#               Python3 port
#                   use get_ methods
#                   use sapphire.Parser
#
############################################################

import os
import datetime

from dateutil import parser

from datatransport import ConfigComponent
import sapphire_config as sapphire

utc = datetime.timezone.utc


class State(ConfigComponent):
    def __init__(self, *pos, **kw):
        ConfigComponent.__init__(self, "state", *pos, **kw)

        self.starttime = None
        self.lasttime = None
        self.elapsed = None

    def mark(self, timestamp):
        self.starttime = None
        self.update(timestamp)

    def update(self, timestamp):
        if self.starttime is None:
            self.starttime = timestamp

        self.lasttime = timestamp
        self.elapsed = self.lasttime - self.starttime

    def save(self, config, section):
        config.set(section, self.itemname + "starttime", str(self.starttime))
        config.set(section, self.itemname + "lasttime", str(self.lasttime))
        config.set(section, self.itemname + "elapsed", str(self.elapsed))

    def load(self, config, section):
        self.starttime = self.get_datetime(config, section, self.itemname + "starttime")
        self.lasttime = self.get_datetime(config, section, self.itemname + "lasttime")
        try:
            self.elapsed = self.lasttime - self.starttime
        except:
            self.elapsed = None

    def get_datetime(self, config, section, key):
        try:
            timestr = config.get(section, key)
            return parser.parse(timestr).replace(tzinfo=utc)
        except:
            return None

    def history_entry(self):
        return "%s, %s, %s" % (self.name, self.starttime, self.lasttime)


class Member(ConfigComponent):
    def __init__(self, *pos, **kw):
        if "state_factory" in kw:
            self.state_factory = kw["state_factory"]
            del kw["state_factory"]
        else:
            self.state_factory = State
        ConfigComponent.__init__(self, *pos, **kw)

        self.states = self.get_components("states", self.state_factory)
        self.unknown = self.get("states.unknown", "unknown")
        self.max_history = self.get_int("maxhistory", 10)
        self.section = self.get("section", self.name)

        if self.unknown not in self.states:
            self.states[self.unknown] = self.state_factory(self.unknown, self)

        self.cur_state = self.unknown
        self.prev_state = self.unknown
        self.history = []
        self.max_history = self.max_history
        self.current = self.states[self.cur_state]
        self.previous = self.states[self.prev_state]
        self.changed = False

    def add_states(self, *pos):
        for name in pos:
            self.states[name] = self.state_factory(name, self)

    def update(self, state, timestamp=None):

        if timestamp is None:
            timestamp = datetime.datetime.now(utc)

        self.current.update(timestamp)

        if self.cur_state == state:
            self.changed = False
        else:
            self.history.append(self.current.history_entry())
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history :]

            self.changed = True
            self.prev_state = self.cur_state
            self.cur_state = state
            self.current = self.states[self.cur_state]
            self.previous = self.states[self.prev_state]

            self.current.mark(timestamp)

        return self.changed

    def save(self, config):

        if not config.has_section(self.section):
            config.add_section(self.section)

        for entry in self.states.values():
            entry.save(config, self.section)

        config.set(self.section, "cur_state", self.cur_state)
        config.set(self.section, "prev_state", self.prev_state)
        config.set(self.section, "changed", str(self.changed))
        config.set(self.section, "history", "\n".join(self.history))

    def load(self, config):

        for entry in self.states.values():
            entry.load(config, self.section)

        if self.section not in config.sections():
            config.add_section(self.section)
            config.set(self.section, "changed", "False")

        self.cur_state = config.get(self.section, "cur_state", self.unknown)
        self.prev_state = config.get(self.section, "prev_state", self.unknown)
        self.current = self.states[self.cur_state]
        self.previous = self.states[self.prev_state]
        self.changed = config.get_boolean(self.section, "changed", False)
        self.history = config.get(self.section, "history", "").splitlines()
        self.history = self.history[-self.max_history :]


class EventMonitor:
    def __init__(self, membersDict):
        self.members = membersDict

    def changed(self):
        return set([m.name for m in self.members.values() if m.changed])

    def save(self, filename, timestamp=None):

        if timestamp is None:
            timestamp = datetime.datetime.now(utc)

        data = sapphire.Parser()
        data.set("DEFAULT", "timestamp", str(timestamp))
        data.set("DEFAULT", "changed", " ".join(self.changed()))

        for member in self.members.values():
            member.save(data)

        tmpname = filename + ".tmp"
        output = open(tmpname, "w")
        data.write(output)
        output.flush()
        os.fsync(output.fileno())
        output.close()
        os.rename(tmpname, filename)

        return data

    def load(self, filename):

        data = sapphire.Parser()
        data.read(filename)

        for member in self.members.values():
            member.load(data)
