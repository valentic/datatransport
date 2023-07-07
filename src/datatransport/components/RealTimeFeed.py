###########################################################################
#
#   RealTimeFeed
#
#   This program acts as a relay between news groups on two different news
#   servers. The primary intent was to quickly deliver messages outside of
#   the normal hourly cron job. A message is extracted from a newsgroup,
#   it's header stripped of fields that will be reset when it is sent, and
#   then it is posted to the newsgroup on the out going server. The news
#   groups do not need to be the same.
#
#   1.0.0   2000-01-27  TAV
#           Initial implementation
#
#   1.0.1   2002-01-25  Todd Valentic
#           Updated to new NewsPollMixin interface.
#           Removed config param "realtime.server" - just use the
#               (now) standard post.newsserver parameter.
#
#   1.0.2   2002-08-27  Todd Valentic
#           Setup with configure script.
#           sri.transport -> Transport
#
#   1.0.3   2003-03-08  Todd Valentic
#           Added try..except around post to protect against errors.
#
#   1.0.4   2003-06-12  Todd Valentic
#           Fixed a bug: NewsPoster's groupHeader is now newsgroupHeader.
#
#   1.0.5   2003-06-30  Todd Valentic
#           Updated to new NewsPoller interface.
#
#   1.0.6   2003-09-09  Todd Valentic
#           When converting a message into a string, use the
#               .as_string() method. Just casting it as str()
#               causes the unix from envolope header to be included.
#
#   1.0.7   2006-10-05  Todd Valentic
#           Added validation.
#
#   1.0.8   2009-05-11  Todd Valentic
#           NewsPoster.postRaw() now takes an email.Message object.
#
#   1.09    2009-09-14  Todd Valentic
#           Raise ProcessRetry if we fail to post.
#
#   1.10    2011-06-28  Todd Valentic
#           Use a copy of the message when posting. Found a bug when
#               the destination group name is different, but built
#               from the name in the message. A process retry will
#               send back in the modified messages, leading to strange
#               errors.
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#
#   2023-07-04  Todd Valentic
#               Updates for transport3 / python3
#                   NewsPoller, NewsPoster
#
###########################################################################

import copy
import os
import sys

from datatransport import ProcessClient
from datatransport import newstool
from datatransport import NewsPoster
from datatransport import NewsPoller


class RealTimeFeed(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)
        self.news_poller = NewsPoller(self, callback=self.process)
        self.main = self.news_poller.main

    def fix_headers(self, message):

        ignoreHeaders = [
            "Newsgroups",
            "Path",
            "Date",
            "Message-ID",
            "NNTP-Posting-Host",
            "NNTP-Posting-Date",
            "X-Trace",
            "X-Complaints-To",
            "Xref",
        ]

        for name in ignoreHeaders:
            try:
                del message[name]
            except:
                pass

        message["Newsgroups"] = self.news_poster.newsgroup_header

        return message

    def valid_message(self, message):
        return True

    def process(self, originalMessage):

        message = copy.deepcopy(originalMessage)

        if not self.valid_message(message):
            self.log.debug("Skipping message (not valid)")
            return

        message = self.fix_headers(message)

        try:
            response = self.news_poster.post_raw(message)
            self.log.info("Files posted, response=%s" % response)
        except:
            self.log.exception("Problem posting to the news server")
            raise newstool.ProcessRetry


def main():
    RealTimeFeed(sys.argv).run()
