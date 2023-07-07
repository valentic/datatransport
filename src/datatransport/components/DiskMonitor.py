##########################################################################
#
#   DiskMonitor
#
#   Monitor disk space using results in ResourceMonitor
#   snapshots. Produce trouble alerts when when running low.
#
#   2004-02-01	Todd Valentic
#               Initial implementation.
#
#   2008-11-13  Todd Valentic
#               Use SafeConfigParser
#
#   2016-12-23  Todd Valentic
#               Use external texttable
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               Python3 updates
#                   ConfigParser -> sapphire.Parser 
#                   StringIO -> io.StringIO
#                   sizeDesc -> size_desc
#                   NewsPoster, NewsPoller
#
##########################################################################

import io
import fnmatch
import sys

import texttable

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport import NewsPoller
from datatransport import newstool
from datatransport import ConfigComponent
from datatransport.utilities import size_desc

import sapphire_config as sapphire


class DiskMonitor(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)
        self.news_poller = NewsPoller(self, callback=self.process)
        self.main = self.news_poller.main

        self.load_history()

        self.includes = self.get_list("mounts.include", "*")
        self.excludes = self.get_list("mounts.exclude", "")
        self.maxusedpct = self.get_float("max.percent.used", 95)

    def load_history(self):
        self.history = sapphire.Parser()
        self.history.read("history")

    def save_history(self):
        self.history.write(open("history", "w"))

    def update_history(self, prefix, stats, mount):

        if not self.history.has_section(mount):
            self.history.add_section(mount)

        for option in stats.options(mount):
            value = stats.get(mount, option)
            self.history.set(mount, f"{prefix}.{option}", value)

    def checkmount(self, stats, mount):

        if self.history.has_section(mount):
            prevalarm = self.history.get_int(mount, "last.alarm")
        else:
            prevalarm = 0

        usedpct = stats.get_float(mount, "usedpct")
        curalarm = usedpct >= self.maxusedpct

        setalarm = not prevalarm and curalarm
        clearalarm = prevalarm and not curalarm

        if setalarm:
            self.log.info("Warning: %s is %d%% full" % (mount, usedpct))
            notes = "Alarm set"
        elif clearalarm:
            self.log.info("Cleared: %s is now only %d%% full" % (mount, usedpct))
            notes = "Cleared alarm"
        elif curalarm and prevalarm:
            notes = "Low space alarm"
        else:
            notes = ""

        self.update_history("last", stats, mount)
        self.history.set(mount, "last.alarm", str(curalarm))
        self.history.set(mount, "last.notes", notes)

        return setalarm or clearalarm

    def check(self, stats):

        self.log.debug("Checking disk usage (limit is %d%%)" % self.maxusedpct)

        # Patchup for development debugging
        if not stats.has_section("System"):
            stats.add_section("System")

        mounts = stats.get("System", "mounts").split()

        for include in self.includes:
            mounts = filter(lambda x: fnmatch.fnmatch(x, include), mounts)
        for exclude in self.excludes:
            mounts = filter(lambda x: not fnmatch.fnmatch(x, exclude), mounts)

        report = 0

        for mount in mounts:
            report += self.checkmount(stats, mount)

        if report:
            message = self.alert_message(mounts)
            try:
                self.news_poster.post_text(message, date=self.timestamp)
            except:
                self.log.exception("Problem posting message")

    def alert_message(self, mounts):

        timestr = self.timestamp.strftime("%Y-%m-%d %H:%M")

        message = "\n"
        message += "Disk Space Report - %s\n\n" % timestr

        table = texttable.Texttable()
        table.header(["Mount", "Total", "Avail", "Used", "% Full", "Notes"])
        table.set_cols_align(["l", "r", "r", "r", "r", "l"])

        for mount in mounts:

            total = long(self.history.get(mount, "last.totalbytes"))
            used = long(self.history.get(mount, "last.usedbytes"))
            free = long(self.history.get(mount, "last.freebytes"))
            usedpct = self.history.get_float(mount, "last.usedpct")

            row = [mount]
            row.append(size_desc(total))
            row.append(size_desc(used))
            row.append(size_desc(free))
            row.append("%d%%" % usedpct)
            row.append(self.history.get(mount, "last.notes"))

            table.add_row(row)

        message += table.draw()
        message += "\n"

        return message

    def process(self, message):

        body = message.get_payload()
        file = io.StringIO(body)
        stats = sapphire.Parser()
        stats.readfp(file)

        self.timestamp = newstool.message_date(message)
        self.history.set("DEFAULT", "last.time", self.timestamp)

        self.check(stats)
        self.save_history()


def main():
    DiskMonitor(sys.argv).run()
