#!/usr/bin/env python3
"""Data Transport log viewer"""

##########################################################################
#
#   ViewLog
#
#   This program displays either the server or a process group's log file
#   in a manner like "tail -F".
#
#   1.0.0   2000-??-??  Todd Valentic
#           Original implementation.
#
#   1.0.1   2002-08-26  Todd Valentic
#           Modified to be setup via configure script.
#
#   2.0.0   2005-01-07  Todd Valentic
#           Completely rewritten and no longer depends on the
#               system's tail command. Checks are made for
#               new files periodically to handle rotating log
#               files.
#
#   2.0.1   2005-04-07  Todd Valentic
#           Sort lines at start to order by time.
#
#   2.0.2   2005-11-08  Todd Valentic
#           Added key parameter to line sorting so we only sort
#               on the date.
#
#   2.0.3   2007-04-14  Todd Valentic
#           Only print log entry lines (those starting with "[")
#               at start to avoid printing part of an traceback.
#
#   2016-12-23  Todd Valentic
#               Use datatransport package format
#               Use print()
#
#   2022-10-06  Todd Valentic
#               Move into datatransport/commands
#               Convert from optparse -> argparse
#
#   2023-07-07  Todd Valentic
#               Updated for transport3 / python3
#               Add recursive and parent options
#               Handle mulitple groups/clients
#               Make sure output is always time ordered
#
##########################################################################

import argparse
import os
import signal
import sys
import time

from pathlib import Path

from datatransport import TransportConfig


class FileTracker:
    """Track view for a given file"""

    def __init__(self, name):
        self.name = name
        self.file = None
        self.size = 0
        self.inode = 0
        self.dev = 0
        self.firsttime = True

        self.n_unchanged_stats = 0
        self.n_consecutive_size_changes = 0

        self.reopen()

    def reopen(self):
        """Reopen the file in case it closes (i.e.log rotation)"""

        try:
            # pylint: disable=consider-using-with
            stream = open(self.name, "r", encoding="utf-8")
            stats = os.stat(self.name)
        except:  # pylint: disable=bare-except
            self.file = None
            self.inode = 0
            self.dev = 0
            return

        self.n_unchanged_stats = 0
        self.n_consecutive_size_changes = 0

        if self.inode != stats.st_ino or self.dev != stats.st_dev:
            self.inode = stats.st_ino
            self.dev = stats.st_dev
            self.size = 0
            self.file = stream

            if self.firsttime:
                offset = 500
                self.size = max(stats.st_size - offset, 0)
            else:
                self.size = 0

    def poll(self):
        """Poll files for changes"""

        if not self.file:
            self.reopen()
            return None

        try:
            stat = os.stat(self.name)
        except:  # pylint: disable=bare-except
            self.file = None
            return None

        if self.size == stat.st_size:
            self.n_unchanged_stats += 1
            self.n_consecutive_size_changes = 0
            if self.n_unchanged_stats > 5:
                self.reopen()
            return None

        self.n_unchanged_stats = 0
        self.n_consecutive_size_changes += 1

        if self.n_consecutive_size_changes > 200:
            self.reopen()
            return None

        if self.size > stat.st_size:
            self.reopen()
            return None

        self.file.seek(self.size)
        data = self.file.read()
        self.size = self.file.tell()

        if self.firsttime:
            self.firsttime = False
            if not data.startswith("\n") and "\n" in data:
                # Start at a newline
                data = data.split("\n", 1)[1]

        return data.rstrip()


def parsedate(line):
    """Get date field in line"""
    return line.split("]")[0][1:].rsplit(" ", 1)[0].strip()


class Tail:
    """Display the last lines of a groups of files"""

    def __init__(self, args):
        self.rate = 0.5
        self.args = args
        self.verbose = args.verbose
        self.specs = args.groups
        self.config = TransportConfig()
        self.trackers = {}

        self.logpath = self.config.get_path("DEFAULT", "path.logfiles")

        path = self.config.get_path("TransportServer", "log.file")
        self.serverlog = path.relative_to(self.logpath)

    def scan_groups(self, specs):
        """Scan for log files"""

        logfiles = [p.relative_to(self.logpath) for p in self.logpath.glob("**/*.log")]

        groups = []

        for spec in specs:
            path = Path(spec)
            groups.append(path)
            groups.extend(list(path.parents)[: self.args.parents])

        watch = set()

        for group in groups:
            if str(group) == ".":
                watch.add(self.serverlog)
                if self.args.recursive:
                    watch.update(logfiles)
                continue
            if self.args.recursive:
                watch.update([p for p in logfiles if p.match(f"{group}/**/*.log")])
            watch.update([p for p in logfiles if p.match(f"{group}/*.log")])
            watch.update([p for p in logfiles if p.match(f"{group}.log")])

        return watch

    def update_trackers(self, trackers, paths):
        """Update current log file trackers"""

        result = {}

        for path in paths:
            key = str(path)
            if key in trackers:
                tracker = trackers[key]
            else:
                tracker = FileTracker(self.logpath.joinpath(path))

            result[key] = tracker

        return result

    def run(self):
        """Print the last 10 lines of each file, sort by time"""

        if self.verbose:
            paths = self.scan_groups(self.specs)

            print("=" * 75)
            print(f"Looking in {self.specs}")
            if self.args.parents is None:
                print("Parents: all")
            else:
                print(f"Parents: {self.args.parents}")
            print(f"Total log files: {len(paths)}")
            for path in paths:
                print(path)
            print("=" * 75)

        # Tail forever

        while True:
            paths = self.scan_groups(self.specs)
            self.trackers = self.update_trackers(self.trackers, paths)

            lines = []
            for tracker in self.trackers.values():
                output = tracker.poll()
                if not output:
                    continue

                if output.startswith("["):
                    output = "\n" + output

                for entry in output.split("\n["):
                    if entry:
                        lines.append("[" + entry)

            if lines:
                lines.sort(key=parsedate)
                print(*lines, sep="\n")

            time.sleep(self.rate)


def handler(_signum, _frame):
    """Signal handler"""
    sys.exit(0)


def main():
    """Main application"""

    signal.signal(signal.SIGINT, handler)

    desc = "Data Transport Log Viewer"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument(
        "groups", nargs="*", help="Server/Group/Client names", default="."
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Show child log files"
    )
    parser.add_argument(
        "-p",
        "--parents",
        nargs="?",
        const=None,
        default=0,
        type=int,
        help="Show parent log files",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    Tail(args).run()
