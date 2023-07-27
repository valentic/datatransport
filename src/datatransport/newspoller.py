#!/usr/bin/env python
"""NewsPoller"""

###########################################################################
#
#   Data Transport NewsPoller
#
#   Poll a newsgroup and call a callback function when new messages arrive.
#
#   History:
#
#   1999-??-??  Todd Valentic
#               Initial implementation.
#
#   2000-04-29  Todd Valentic
#               Added the groupExists() check at the top of the run() method.
#               If the group isn't available (either it doesn't exist or
#               the server is down) then stall and retry every minute. This
#               situation often ocurrs when a new process group is added to
#               the system and the newsgroups don't exist yet. The posting
#               processes will create the groups, but they may not show up
#               for a few minutes. By stalling and rechecking, we eventually
#               sync up.
#
#   2001-08-11  Todd Valentic
#               Added the 'text' parameter to handle ProcessText callbacks.
#
#   2001-08-13  Todd Valentic
#               Added the idle function to get called during the main loop.
#
#   2001-11-13  Todd Valentic
#               Added self.running check to run().
#
#   2001-12-10  Todd Valentic
#               Added running check before sleeping.
#               ProcessClient now defines self.running.
#
#   2001-12-26  Todd Valentic
#               Changed tav -> sri
#
#   2002-02-24  Todd Valentic
#               Major code cleanup.
#               Changed the default config names be prefixed with "poll.". This
#                   prefix is also user setable in __init__.
#               Default server is now localhost.
#
#   2002-03-05  Todd Valentic
#               Added exit_on_error parameter (replaces debug).
#
#   2002-04-23  Todd Valentic
#               Changed call from newsPoller.prifix -> news_poll_prefix.
#                   The former is only used to prefix filenames.
#
#   2002-08-28  Todd Valentic
#               sri.transport -> Transport
#
#   2003-04-15  Todd Valentic
#               Added support for NewsPoller to listen to isRunning.
#               Removed the local system() call. This had added the
#                   current working directory to the path. This is
#                   now done in the configuration files.
#
#   2003-06-30  Todd Valentic
#               Change to new single callback method for processing.
#
#   2003-08-11  Todd Valentic
#               Removed unneeded 'import os'
#               Made rate a DeltaTime parameter.
#               Modified to handle multiple input newsgroups. newsPoller is
#                   now a list instead of a single instance.
#
#   2003-08-14  Todd Valentic
#               createDeltaTime -> getDeltaTime
#               createCallback -> getCallback
#
#   2004-02-05  Todd Valentic
#               Changed idleFunc -> idle. Keep older version for awhile.
#
#   2004-08-17  Todd Valentic
#               Changed to new logger interface.
#
#   2005-01-06  Todd Valentic
#               Changed NewsTool import.
#
#   2005-04-10  Todd Valentic
#               Use is_stopped() as poller stop function.
#
#   2005-05-09  Todd Valentic
#               Generalized run() method by adding _run_pollers and _run_idle.
#                   This makes is easier for derived classes (ie SyncPoller)
#                   to override these functions.
#
#   2005-07-27  Todd Valentic
#               New ability to specify multiple newsgroups with wild
#                   cards in their names. This requires a connection
#                   to the newsserver be available. If no
#
#   2005-11-30  Todd Valentic
#               Added debug listing of news pollers at creation.
#
#   2006-05-31  Todd Valentic
#               Added ability to set port for news server in config file.
#
#   2007-02-05  Todd Valentic
#               Added catchup.reset - when True, the catchup is applied each
#                   polling cycle. You can use this, for example, to only
#                   processes the last message.
#
#   2007-04-15  Todd Valentic
#               Moved catchup.reset processing into _run_pollers(). We
#                   were crashing on NNTP temperorary errors.
#
#   2008-08-11  Todd Valentic
#               Make sure we can connect to the news server at start.
#
#   2008-08-12  Todd Valentic
#               Correctly implement feature in 2.2.13.
#
#   2008-08-20  Todd Valentic
#               Make poll.rate.sync a boolean.
#               Make poll.rate.offset a timedelta.
#               Fix catchup.reset processing (broken in 2.2.12)
#
#   2014-01-17  Todd Valentic
#               Add poll.newsgroups.exclude
#
#   2020-01-08  Todd Valentic
#               Use rate object for poll config
#               Set lastReadPrexix if used in ConfigComponent object
#
#   2022-10-19  Todd Valentic
#               Remove deprecated idleFunc
#               Port to transport3 / python3
#
#   2023-07-04  Todd Valentic
#               Convert from being a mixin class
#
#   2023-07-27  Todd Valentic
#               Use AccessMixin
#
###########################################################################

from datatransport import newstool
from datatransport import AccessMixin


class NewsPoller(AccessMixin):
    """News poller"""

    def __init__(self, parent, prefix="poll", callback=None, idle=None):
        AccessMixin.__init__(self, parent)

        self.prefix = prefix
        self.idle = idle
        self.rate = self.config.get_rate(f"{prefix}.rate", 60)

        self.news_pollers = self.create_pollers(prefix, callback)

    # pylint: disable=inconsistent-return-statements
    def connect_to_server(self, host, port):
        """Open a connection to the news server"""

        server = newstool.NewsTool()
        server.set_server(host, port)

        while self.is_running():
            try:
                server.open_server()
                return server
            except:  # pylint: disable=bare-except
                self.log.exception(f"Failed to connect to {host}:{port}")
                self.wait(15)

        self.abort("Exiting")

    def get_newsgoups(self, prefix, server):
        """Get a list of newsgroups"""

        targetgroup = self.config.get(f"{prefix}.newsgroup", "")
        targetgroups = self.config.get_list(f"{prefix}.newsgroups", targetgroup)
        excludegroup = self.config.get(f"{prefix}.newsgroup.exclude", "")
        excludegroups = self.config.get_list(f"{prefix}.newsgroups.exclude", excludegroup)

        newsgroups = []

        for groupspec in targetgroups:
            if "*" in groupspec or "?" in groupspec:
                try:
                    matches = server.list_newsgroups(groupspec, excludegroups)
                    newsgroups.extend(matches)
                except:  # pylint: disable=bare-except
                    self.log.info(f"Problem matching '{groupspec}'")
                    continue
            else:
                newsgroups.append(groupspec)

        return newsgroups

    def create_pollers(self, prefix, callback):
        """Create a news poller for each newsgroup"""

        host = self.config.get(f"{prefix}.newsserver", "localhost")
        port = self.config.get_int(f"{prefix}.newsserver.port", 119)

        exit_on_error = self.config.get_boolean(f"{prefix}.exit_on_error", False)
        retry_wait = self.config.get_timedelta(f"{prefix}.retry_wait", 60)

        # Prefix the tracking file when used in ConfigComponent
        # because we might have multiple references to the same group

        if hasattr(self.parent, "prefix") and hasattr(self.parent, "name"):
            last_read_prefix = f"{self.parent.prefix}-{self.parent.name}"
        else:
            last_read_prefix = ""

        server = self.connect_to_server(host, port)
        newsgroups = self.get_newsgoups(prefix, server)

        self.log.debug("Creating news pollers:")

        pollers = []

        for newsgroup in newsgroups:
            poller = newstool.NewsPoller()
            poller.set_server(host, port)
            poller.set_newsgroup(newsgroup)
            poller.set_log(self.log)
            poller.set_callback(callback)
            poller.set_stop_func(self.is_stopped)
            poller.set_retry_wait(retry_wait.total_seconds())
            poller.set_debug(exit_on_error)
            poller.set_last_read_prefix(last_read_prefix)

            pollers.append(poller)

            self.log.debug(" - [%s:%s] %s", host, port, newsgroup)

        return pollers

    def run_pollers(self, catchup, reset):
        """Run each poller"""

        for poller in self.news_pollers:
            if reset and catchup != 0:
                poller.mark_read(catchup, reset=reset)

            poller.poll()

    def run_idle(self):
        """Run the idle handler"""

        if self.idle and self.is_running():
            self.idle()

    def mark_read(self, catchup, reset):
        """Mark each newsgroup as read"""

        for poller in self.news_pollers:
            while not poller.has_newsgroup():
                self.self.log.error(
                    f"The polling group ({poller.newsgroup_header}) "
                    f"does not exist on "
                    f"{poller.server_host}:{poller.server_port}, "
                    f"waiting 60 seconds ..."
                )
                if not self.wait(60):
                    return

            if catchup != 0:
                poller.mark_read(catchup, reset)

    def process(self):
        """Process messages"""

        catchup = self.config.get_int(f"{self.prefix}.catchup", 0)
        catchup_reset = self.config.get_boolean(f"{self.prefix}.catchup.reset", False)
        exit_on_error = self.config.get_boolean(f"{self.prefix}.exit_on_error", False)

        if catchup == 0:
            self.log.debug("Starting with first article in last read file")
        else:
            self.mark_read(catchup, catchup_reset)

        while self.is_running():
            try:
                self.run_pollers(catchup, catchup_reset)
            except:  # pylint: disable=bare-except
                self.log.exception("Error detected during polling")
                if exit_on_error:
                    self.abort("Exiting on error")

            try:
                self.run_idle()
            except:  # pylint: disable=bare-except
                self.log.exception("Error detected during idle")
                if exit_on_error:
                    self.abort("Exiting on error")

            yield 1

    def main(self):
        """Main loop"""

        if not self.wait(self.rate):
            return

        for _step in self.process():
            self.wait(self.rate)

    def run_step(self):
        """Run one step in main loop"""

        next(self.process())
