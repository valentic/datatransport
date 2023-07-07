#!/usr/bin/env python

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
#               Added catchup and reset to _runPollers() interface.
#                   These have been missing for awhile (NewsPollMixin
#                   changed the signature). The values are not used here.
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               NewsPoller
#
###########################################################################

from datatransport import ProcessClient
from datatransport import NewsPoller
from datatransport import newstool


class SyncPoller(ProcessClient):
    def __init__(self, argv, prefix="poll", callback=None, idle=None):
        ProcessClient.__init__(self, argv)

        self.news_poller = NewsPoller(self, prefix=pefix, callback=callback, idle=idle)
        self.news_pollers = self.news_poller.news_pollers

        self.messages = {}
        self.callback = callback

        for poller in self.ews_pollers:
            self.messages[poller] = None

    def get_timestamp(self, message):
        return newstool.message_date(message)

    def valid_message(self, message):
        # Derived class can override
        return True

    def compare_messages(self):

        # Search for oldest message

        oldestTime = None
        oldestPoller = None

        for poller in self.news_pollers:
            message = self.messages[poller]
            if message:
                timestamp = self.get_timestamp(message)
                if oldestTime is None or timestamp < oldestTime:
                    oldestTime = timestamp
                    oldestPoller = poller

        return oldestPoller

    def validate_message(self, message):
        return True

    def get_next_message(self, poller):

        # Get the next *valid* message from the news group.
        # Return None if no messages are available.

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

    def _runPollers(self, catchup, reset):

        while self.is_running():

            # Refresh the queued message list.

            for poller in self.news_pollers:
                if self.messages[poller] is None:
                    self.messages[poller] = self.get_next_message(poller)

            if not self.is_running():
                break

            # Find the preferred message to process

            poller = self.compare_messages()

            if not self.is_running():
                break

            # Run until all messages are processed

            if poller is None:
                break

            poller.process_article(self.messages[poller])
            self.messages[poller] = None
