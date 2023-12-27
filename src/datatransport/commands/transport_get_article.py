#!/usr/bin/env python3
"""Download messages from a newsgroup"""

#####################################################################
#
#   GetArticle
#
#   This script can be used to extract messages from a news group.
#   It can be run in a one shot or loop mode.
#
#   History:
#
#   2003-02-24  Todd Valentic
#               Initial implementation.
#
#   2004-02-17  Todd Valentic
#               Updated to new callback format.
#
#   2006-02-03  Todd Valentic
#               Removed reference for setVerbose.
#
#   2016-12-26  Todd Valentic
#               Use datatransport package
#
#   2023-08-33  Todd Valentic
#               Updated for transport3 / python3
#               Format for PEP8 compliance
#               Use argparse
#               Add signal handling
#               Add no save option
#               Add uncompress option
#               Add output directory option
#
#   2023-11-01  Todd Valentic
#               Append message ID to name when message in body
#
#####################################################################

import argparse
import bz2
import fnmatch
import gzip
import logging
import pathlib
import shutil
import signal
import sys
import time
import threading

from datatransport import newstool

VERSION = "1.1"


class NewsgroupPoller:
    """Monitor a single newsgroup"""

    def __init__(self, parent, newsgroup):
        self.args = parent.args
        self.log = parent.log
        self.done = parent.done
        self.newsgroup = newsgroup
        self.finished = False

        self.poller = newstool.NewsPoller()
        self.poller.set_server(self.args.server, port=self.args.port)
        self.poller.set_newsgroup(newsgroup)
        self.poller.set_stop_func(self.done.is_set)
        self.poller.set_debug(self.args.debug)
        self.poller.set_single_shot(True)
        self.poller.set_last_read_path(self.args.trackdir)
        self.poller.set_last_read_prefix(".track")

        self.poller.set_callback(self.process)

        if self.args.catchup:
            self.poller.mark_read(self.args.catchup)

    def uncompress(self, filename):
        """Uncompress file"""

        if not self.args.uncompress:
            return filename

        outname = filename.with_suffix("")

        if filename.suffix == ".bz2":
            handler = bz2.BZ2File
        elif filename.suffix == ".gz":
            handler = gzip.GzipFile
        else:
            return filename

        with handler(filename, "rb") as infile, outname.open("wb") as outfile:
            shutil.copyfileobj(infile, outfile)

        filename.unlink()

        return outname

    def process(self, message):
        """Message processor"""

        output = self.args.outputdir

        if self.args.addgroupdir:
            output = output.joinpath(message["Newsgroups"])

        msgnum = message["Xref"].rsplit(":", 1)[-1]
        name = f"body-{msgnum}.txt"
        filenames = newstool.save_files(
            message, default=name, write=self.args.save, path=output
        )
        self.log.info("Received files from %s", message["Newsgroups"])

        for filename in filenames:
            filename = self.uncompress(filename)
            self.log.info("  - %s", filename.name)

        if self.args.oneshot:
            self.finished = True

    def run(self):
        """Poll newsgroup for new messages"""

        self.log.debug("Checking %s", self.newsgroup)
        self.poller.poll()
        return not self.finished


class Downloader:
    """Download articles from multiple newsgroups"""

    def __init__(self):
        self.setup_signals()

        self.done = threading.Event()
        self.args = self.parse_command_line()
        self.log = self.setup_log(self.args)

        self.pollers = self.create_pollers(self.args)

        self.show_config()

    def setup_signals(self):
        """Setup signal handlers"""

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGHUP, self.signal_handler)

    def signal_handler(self, _signum, _frame):
        """Signal handler"""

        self.done.set()

    def show_config(self):
        """Display banner and configuration options"""

        self.log.info("=" * 75)
        self.log.info("Data Transport News Article Downloader %s", VERSION)
        self.log.info("=" * 75)

        self.log.info("Press Ctrl-C to exit")
        self.log.info("")

        self.log.info("News server: %s:%s", self.args.server, self.args.port)
        self.log.info("One shot: %s", self.args.oneshot)
        self.log.info("Catchup: %s", self.args.catchup)
        self.log.info("Save files: %s", self.args.save)
        self.log.info("Output path: %s", self.args.outputdir)

        self.log.info("Watching newsgroups:")

        for poller in self.pollers.values():
            self.log.info("  %s", poller.newsgroup)

        self.log.info("-" * 75)

    def parse_command_line(self):
        """Parse the command line"""

        desc = "Download messages from a newsgroup" ""
        parser = argparse.ArgumentParser(description=desc)

        parser.add_argument("-V", "--version", action="version", version=VERSION)

        parser.add_argument(
            "-q", "--quiet", action="store_true", help="Only show errors"
        )

        parser.add_argument("-d", "--debug", action="store_true", help="Debug output")

        parser.add_argument(
            "-c",
            "--catchup",
            type=int,
            nargs="?",
            default=0,
            help="Mark all messages as read, -N mark up to last N messages",
        )

        parser.add_argument(
            "-e",
            "--oneshot",
            action="store_true",
            help="Exit after one message is received from each newsgroup",
        )

        parser.add_argument(
            "-n",
            "--nosave",
            action="store_false",
            dest="save",
            help="Don't save files, just report",
        )

        parser.add_argument(
            "-u",
            "--uncompress",
            action="store_true",
            help="Uncompress gz or bz2 files",
        )

        parser.add_argument(
            "-o",
            "--outputdir",
            default=".",
            type=pathlib.Path,
            help="Store files in this directory",
        )

        parser.add_argument(
            "-g",
            "--addgroupdir",
            action="store_true",
            help="Add newsgroup name to output directory",
        )

        parser.add_argument(
            "-t",
            "--trackdir",
            default=".",
            type=pathlib.Path,
            help="Store tracking files in this directory",
        )

        parser.add_argument(
            "-s",
            "--server",
            default="localhost",
            help="News server (default: localhost)",
        )

        parser.add_argument(
            "-p",
            "--port",
            type=int,
            default=119,
            help="News server port (default: 119)",
        )

        parser.add_argument("newsgroups", nargs="+", metavar="newsgroup")

        args = parser.parse_args()

        if args.catchup is None:
            args.catchup = 1

        return args

    def setup_log(self, args):
        """Setup the log output"""

        fmt = "[%(levelname)s] %(message)s"

        if args.debug:
            logging.basicConfig(format=fmt, level=logging.DEBUG)
        elif args.quiet:
            logging.basicConfig(format=fmt, level=logging.ERROR)
        else:
            logging.basicConfig(format=fmt, level=logging.INFO)

        return logging

    def create_pollers(self, args):
        """Create a poller for each newsgroup"""

        server = newstool.NewsTool()
        server.set_server(args.server, port=args.port)
        available_newsgroups = server.list_newsgroups()

        pollers = {}

        for pattern in args.newsgroups:
            for newsgroup in available_newsgroups:
                if fnmatch.fnmatch(newsgroup, pattern):
                    if newsgroup not in pollers:
                        pollers[newsgroup] = NewsgroupPoller(self, newsgroup)

        return pollers

    def run(self):
        """Run a polling cycle for all of the monitored newsgroups"""

        pollers = self.pollers.values()

        while not self.done.is_set() and pollers:
            self.log.debug("Cycle start")

            next_pollers = []

            for poller in pollers:
                if poller.run():
                    next_pollers.append(poller)

            pollers = next_pollers

            if self.args.oneshot and pollers:
                self.log.debug("Waiting for messages from")
                for poller in pollers:
                    self.log.debug("  %s", poller.newsgroup)

            self.log.debug("Cycle finished")

            time.sleep(1)

        return 0


def main():
    """Script entry point"""

    return_code = Downloader().run()
    sys.exit(return_code)
