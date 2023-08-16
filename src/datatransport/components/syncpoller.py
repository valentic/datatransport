#!/usr/bin/env python3
"""Synchronized newsgroup poller"""

###########################################################################
#
#   Synchronized News Group Poller
#
#   This class provides a framework for polling multiple news groups
#   and synchronizing the message stream. A user provided callback
#   function is used to compare the next available message from each
#   polled news group. The function returns the preferred message. For
#   example, the message times might be compared so that the oldest
#   message is processed next. Using a synchronization function like
#   this is necessary when performing functions based on a stream of
#   multiple asynchonous events or when processing a backlog of
#   messages.
#
#   You can customize this class in a couple of ways. The most common
#   synchronization mechanism is based on the message times. The
#   default method compareMessage() checks these time stamps and
#   selects the news group with the oldest time stamp. You can
#   override the get_timestamp() method if the message times are not in
#   the standard headers. To do synchronization on another parameter,
#   you can override compare_messages(). It returns the poller object
#   corresponding to the news group you want to process. The messages
#   list holds the currently queued message for each news group.
#
#   2005-05-07  Todd Valentic
#               Initial implementation.
#
#   2006-02-03  Todd Valentic
#               Added valid_message default method.
#
#   2009-05-04  Todd Valentic
#               Added catchup and reset to _run_pollers() interface.
#                   These have been missing for awhile (NewsPollMixin
#                   changed the signature). The values are not used here.
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               NewsPoller
#
#   2023-07-15  Todd Valentic
#               Updated for transport3 / python3
#               Converted to just be a specalized NewsPoller
#
###########################################################################

from datatransport import NewsPoller
from datatransport import newstool


class SyncPoller(NewsPoller):
    """Synchronized NewsPoller"""

    def __init__(self, *p, **kw):
        NewsPoller.__init__(self, *p, **kw)

        self.messages = {}

        for poller in self.news_pollers:
            self.messages[poller] = None

    def get_timestamp(self, message):
        """Get message timestamp"""

        return newstool.message_date(message)

    def valid_message(self, _message):
        """Check if message is valid"""

        return True

    def find_oldest_message(self):
        """Search for oldest message"""

        oldest_time = None
        oldest_poller = None

        for poller, message in self.messages.items():
            if not message:
                continue
            timestamp = self.get_timestamp(message)
            if oldest_time is None or timestamp < oldest_time:
                oldest_time = timestamp
                oldest_poller = poller

        return oldest_poller

    def get_next_message(self, poller):
        """Get the next *valid* message from the news group.
        Return None if no messages are available."""

        while self.is_running():
            message = poller.get_next_message()

            if message is None:
                break

            if self.valid_message(message):
                break

            # The message is not valid (based on some user
            # criteria). Mark the message as read and try again

            poller.mark_message_read(message)

        return message

    def refresh_messages(self):
        """Refresh message queue"""

        for poller in self.news_pollers:
            if self.messages[poller] is None:
                self.messages[poller] = self.get_next_message(poller)

    def run_pollers(self, catchup, reset):
        """Run each poller, synchronized"""

        while self.is_running():
            self.refresh_messages()

            if not self.is_running():
                break

            # Find the preferred message to process

            poller = self.find_oldest_message()

            if not self.is_running():
                break

            # Run until all messages are processed

            if poller is None:
                break

            poller.process_article(self.messages[poller])
            self.messages[poller] = None
