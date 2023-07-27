###########################################################################
#
#  GroupControl
#
#  This script polls a "control" newsgroup looking for messages to start
#  and stop process groups.
#
#  History:
#
#   1.0.0   2000-01-19  TAV
#           Initial implementation
#
#   1.0.1   2000-02-22  TAV
#           Added the maillist reporting feature.
#
#   1.0.2   2000-02-26  TAV
#           Improved wording and look of the mailing list message.
#
#   1.0.3   2000-04-25  TAV
#           Added connect() method to retry connecting to server incase it
#               is busy during the initial contact.
#
#   1.0.4   2000-04-29  TAV
#           Fixed bug in connect call.
#
#   1.0.5   2001-11-13  TAV
#           Added prefix and postfix config options.
#
#   1.0.6   2001-12-26  TAV
#           Changed tav -> sri
#
#   1.0.7   2002-01-25  Todd Valentic
#           Updated to new NewsPollMixin interface.
#
#   1.0.8   2002-08-27  Todd Valentic
#           Setup through configure script.
#           sri.transport -> Transport
#           use socket.getfqdn() versus sri.util.hostname()
#
#   1.0.9   2003-03-21  Todd Valentic
#           Code cleanups. Use self.wait in connect()
#           Use string methods instead of string module
#           Split out baseclass from driver
#
#   1.0.10  2003-05-09  Todd Valentic
#           Moved the connection code up into __init__()
#               we were sleeping 60 seconds on the first
#               message process otherwise.
#
#   1.0.11  2003-06-30  Todd Valentic
#           Updated to new NewsPoller interface.
#
#   1.0.12  2004-08-08  Todd Valentic
#           Use new XML-RPC interface to transport server.
#
#   1.0.13  2004-12-27  Todd Valentic
#           Convert from mx.DateTime to datetime
#
#   1.0.14  2006-01-18  Todd Valentic
#           Minor code cleanups
#
#   1.0.15  2006-10-26  Todd Valentic
#           Use new CurrentTime method
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               Python3 migration:
#                   exception handling
#                   NewsPoller, NewsPoster
#
#   2023-07-28  Todd Valentic
#               Updated for transport3 / python3
#
###########################################################################

import os
import socket
import sys

from datatransport import ProcessClient
from datatransport import NewsPoller
from datatransport import NewsPoster
from datatransport import newstool


class GroupControl(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)
        self.news_poller = NewsPoller(self, callback=self.process)
        self.main = self.news_poller.main

        self.prefix = self.config.get("prefix", "")
        self.postfix = self.config.get("postfix", "")

        self.connect()

    def connect(self):

        self.log.info("Connecting to transport server")

        while True:

            try:
                self.server.status()
                return
            except:
                self.log.error("  - waiting 30 seconds to try again.")

            if not self.wait(30):
                break

    def post_message(self, action, group):

        curtime = self.current_time()
        hostname = socket.getfqdn()

        body = []
        body.append("")
        body.append("  The following action has been performed:")
        body.append("")
        body.append("      Command  : %s" % action)
        body.append("      Group    : %s" % group)
        body.append("      Time     : %s" % curtime)
        body.append("      Server   : %s" % hostname)
        body.append("")

        header = "%s %s" % (action, group)

        try:
            self.news_poster.set_subject(header)
            self.news_poster.post_text("\n".join(body))
        except:
            self.log.error("Error posting message to mailing list.")

    def start_group(self, name):
        self.log.info("Start request for %s" % name)
        try:
            self.server.startgroup(name)
            self.post_message("start", name)
        except NameError(msg):
            self.log.info("  The process group does not exist")

    def stop_group(self, name):
        self.log.info("Stop request for %s" % name)
        try:
            self.server.stopgroup(name)
            self.post_message("stop", name)
        except NameError(msg):
            self.log.info("  The process group does not exist")

    def process(self, message):

        filenames = newstool.save_files(message)

        for filename in filenames:

            if self.is_stopped():
                return

            for line in open(filename):

                try:
                    command, name = line.split("=")
                except:
                    continue

                command = command.strip().lower()
                name = os.path.join(self.prefix, name.strip())
                name = os.path.join(name, self.postfix)

                if command == "start":
                    self.start_group(name)
                elif command == "stop":
                    self.stop_group(name)
                else:
                    self.log.error("Unknown request: %s" % command)

            os.remove(filename)


def main():
    GroupControl(sys.argv).run()
