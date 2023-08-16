#!/usr/bin/env python3
"""Disk Monitor Component"""

##########################################################################
#
#   DiskMonitor
#
#   This process client monitors the system disk usage reported in the
#   output messages from the ResourceMonitor client running in the
#   ServerMonitor process group. A trouble message will be sent when
#   disk space is running low.
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
#   2023-07-27  Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import fnmatch
import pathlib
import sys

import texttable

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport import NewsPoller
from datatransport import newstool
from datatransport.utilities import size_desc

import sapphire_config as sapphire


class DiskMonitor(ProcessClient):
    """Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)
        self.news_poller = NewsPoller(self, callback=self.process)
        self.main = self.news_poller.main

        self.cachefile = pathlib.Path("history")
        self.load_history()

        sysmnts = "/dev* /run* /sys*"

        self.includes = self.config.get_list("mounts.include", "*")
        self.excludes = self.config.get_list("mounts.exclude", sysmnts)
        self.max_used_pct = self.config.get_float("max.percent.used", 95)

    def load_history(self):
        """Load history from cache"""

        self.history = sapphire.Parser()
        self.history.read(self.cachefile)

    def save_history(self):
        """Save history to cache"""

        with self.cachefile.open("w", encoding="utf-8") as f:
            self.history.write(f)

    def update_history(self, prefix, stats, mount):
        """Update history"""

        if not self.history.has_section(mount):
            self.history.add_section(mount)

        for option in stats.options(mount):
            value = stats.get(mount, option)
            self.history.set(mount, f"{prefix}.{option}", value)

    def checkmount(self, stats, mount):
        """Check mounted filesystem"""

        if self.history.has_section(mount):
            prevalarm = self.history.get_boolean(mount, "last.alarm")
        else:
            prevalarm = False

        usedpct = stats.get_float(mount, "usedpct")
        curalarm = usedpct >= self.max_used_pct

        setalarm = not prevalarm and curalarm
        clearalarm = prevalarm and not curalarm

        if setalarm:
            self.log.info("Warning: %s is %d%% full", mount, usedpct)
            notes = "Alarm set"
        elif clearalarm:
            self.log.info("Cleared: %s is now only %d%% full", mount, usedpct)
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
        """Check mounted filesystems"""

        self.log.debug("Checking disk usage (limit is %d%%)", self.max_used_pct)

        # Patchup for development debugging
        if not stats.has_section("System"):
            stats.add_section("System")

        mounts = stats.get_list("System", "mounts")

        for include in self.includes:
            mounts = [m for m in mounts if fnmatch.fnmatch(m, include)]
        for exclude in self.excludes:
            mounts = [m for m in mounts if not fnmatch.fnmatch(m, exclude)]

        report = 0

        for mount in mounts:
            report += self.checkmount(stats, mount)

        if report:
            message = self.alert_message(mounts)
            try:
                self.news_poster.post_text(message, date=self.timestamp)
            except Exception as e: # pylint: disable=broad-exception-caught
                self.log.exception("Problem posting message: %s", e)

    def alert_message(self, mounts):
        """Return an alert message"""

        timestr = self.timestamp.strftime("%Y-%m-%d %H:%M")

        message = "\n"
        message += f"Disk Space Report - {timestr}\n\n"

        table = texttable.Texttable()
        table.header(["Mount", "Total", "Used", "Avail", "% Full", "Notes"])
        table.set_cols_align(["l", "r", "r", "r", "r", "l"])

        for mount in mounts:
            total = self.history.get_float(mount, "last.totalbytes")
            used = self.history.get_float(mount, "last.usedbytes")
            free = self.history.get_float(mount, "last.freebytes")
            usedpct = self.history.get_float(mount, "last.usedpct")

            row = [mount]
            row.append(size_desc(total))
            row.append(size_desc(used))
            row.append(size_desc(free))
            row.append(f"{usedpct:0.1f}%")
            row.append(self.history.get(mount, "last.notes"))

            table.add_row(row)

        message += table.draw()
        message += "\n"

        return message

    def process(self, message):
        """Process handler"""

        stats = newstool.as_config(message)

        self.timestamp = newstool.message_date(message)
        self.history.set("DEFAULT", "last.time", str(self.timestamp))

        self.check(stats)
        self.save_history()


def main():
    """Script entry point"""
    DiskMonitor(sys.argv).run()
