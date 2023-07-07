#####################################################################
#
#   Newsgroup Monitor
#
#   Monitors the news groups for messages
#
#   2009-05-04  Todd Valentic
#               Initial implementation. Based on InstrumentStatus
#
#   2010-03-20  Todd Valentic
#               Added feedgroups
#
#   2010-03-23  Todd Valentic
#               Save history at start
#
#   2011-03-11  Todd Valentic
#               Add warning state
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               Python3 updates:
#                   StringIO -> io.StringIO
#               NewsPoller, NewsPoster
#
#####################################################################

import io
import sys

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport import NewsPoller
from datatransport import ConfigComponent
from datatransport.components import EventMonitor


class FeedGroup(ConfigComponent):
    def __init__(self, name, parent):
        ConfigComponent.__init__(self, "feedgroup", name, parent)

        self.log.info("  Feed group: %s" % name)

        localvars = {"feedgroup": name, "section": "%(feedgroup)s:%(feed)s"}

        for key, option in self.optionsdict().items():
            value = self.get(option, raw=True)
            localvars["feedgroup." + key] = value

        feeds_dict = self.get_components("feeds", Feed, vars=localvars)
        self.feeds = feeds_dict.values()

    def check(self):

        for feed in self.feeds:
            try:
                feed.check()
            except:
                self.log.exception("Problem checking %s" % feed.name)


class Feed(EventMonitor.Member):
    def __init__(self, *pos, **kw):
        EventMonitor.Member.__init__(self, "feed", *pos, **kw)

        self.news_poster = NewsPoster(self, quiet=True)
        self.news_poller = NewsPoller(self)
        self.main = news_poller.main

        self.add_states("online", "offline", "warning", "error")

        self.feedgroup = kw["localvars"]["feedgroup"]

        if self.feedgroup:
            desc = "%s:%s" % (self.feedgroup, self.name)
        else:
            desc = self.name

        self.log.info("    %s:%s" % (self.feedgroup, self.name))

        self.timeout = self.get_timedelta("timeout", "1:00:00")
        self.report_change = self.get_boolean("report.change", True)
        self.desc = self.get("desc", desc)
        self.alwayson = self.get_boolean("alwayson", False)

    def check(self):

        groups = {}

        for poller in self.news_pollers:
            groups.update(poller.list_articles(self.timeout))

        count = 0
        feeds = 0

        for group, articles in groups.items():
            if articles:
                feeds += 1
                count += len(articles)

        if feeds:
            if len(groups) == feeds:
                self.update("online")
            else:
                self.update("warning")
        else:
            if self.alwayson:
                self.update("error")
            else:
                self.update("offline")

        msg = "  - %s: %s %s (%s msgs in %s feeds over the last %s)" % (
            self.name,
            self.cur_state,
            self.current.elapsed,
            count,
            feeds,
            self.timeout,
        )

        if self.changed:
            msg += " <- Changed from %s" % self.prev_state

        self.log.info(msg)

        if self.report_change and self.changed:
            self.report()

    def report(self):

        subject, message = self.report_message()

        try:
            self.news_poster.set_subject(subject)
            self.news_poster.post_text(message)
        except:
            self.log.exception("Error posting change message for %s" % self.name)

    def report_message(self):

        if self.cur_state == "online":
            action = "started"
        else:
            action = "stopped"

        subject = "%s has %s" % (self.desc, action)

        fmt = "%a, %d %b %Y %H:%M:%S %Z"

        message = []
        message.append("")
        message.append("  The following instrument has %s sending data:" % action)
        message.append("")
        message.append("    Instrument: %s" % self.desc)
        message.append("    Date/Time : %s" % self.current.starttime.strftime(fmt))
        message.append("    Currently : %s" % self.cur_state.capitalize())
        message.append("")
        message.append("  Previous state: %s" % self.prev_state.capitalize())
        message.append("    Start time: %s" % self.previous.starttime.strftime(fmt))
        message.append("    Stop time : %s" % self.previous.lasttime.strftime(fmt))
        message.append("    Elapsed   : %s" % self.previous.elapsed)
        message.append("")

        message = "\n".join(message)

        return subject, message


class NewsgroupMonitor(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.history_poster = NewsPoster(self, prefix="history", quiet=True)
        self.status_poster = NewsPoster(self, prefix="status", quiet=True)
        self.update_poster = NewsPoster(self, prefix="update", quiet=True)

        self.log.info("Loading feed groups")

        self.feedgroups = self.get_components("feedgroups", FeedGroup).values()

        if not self.feedgroups:
            self.feedgroups = [FeedGroup("", self)]

        self.feeds = {}

        for feedgroup in self.feedgroups:
            for feed in feedgroup.feeds:
                key = "%s:%s" % (feedgroup.name, feed.name)
                self.feeds[key] = feed

        self.tracker = EventMonitor.EventMonitor(self.feeds)
        self.tracker.load("tracker")

        self.first_time = True

    def main(self):

        rate = self.get_timedelta("poll.rate", "1:00")
        sync = self.get_boolean("poll.sync")
        offset = self.get_timedelta("poll.offset")

        while self.wait(rate, sync, offset):

            for feedgroup in self.feedgroups:
                self.log.info("Checking feeds: %s" % feedgroup.name)
                feedgroup.check()

            try:
                self.save_state()
            except:
                self.log.exception("Problem saving tracker")

    def save_state(self):

        config = self.tracker.save("tracker")
        strbuff = io.StringIO()
        config.write(strbuff)

        self.update_poster.post_text(strbuff.getvalue())

        if self.first_time:
            self.history_poster.post_text(strbuff.getvalue())
            self.first_time = False

        if self.tracker.changed():
            self.history_poster.post_text(strbuff.getvalue())

            subject, message = self.status_message()
            self.status_poster.set_subject(subject)
            self.status_poster.post_text(message)

    def status_message(self):

        message = []
        message.append("")
        message.append("  A change in instrument status has been detected:")
        message.append("")

        subject = None

        descwidth = max([len(feed.desc) for feed in self.feeds.values()])
        fmt = "%a, %d %b %Y %H:%M:%S %Z"

        for feed in self.feeds.values():

            status = feed.cur_state.capitalize()

            if not feed.changed:
                changed = ""
            else:
                changed = "<-- %s" % feed.current.starttime.strftime(fmt)
                if not subject:
                    subject = "%s %s" % (feed.desc, feed.cur_state)
                else:
                    subject = "Multiple instruments have changed status"

            message.append(
                "  %s: %-10s %s" % (feed.desc.rjust(descwidth), feed.cur_state, changed)
            )

        message.append("")
        message = "\n".join(message)

        return subject, message


def main():
    NewsgroupMonitor(sys.argv).run()
