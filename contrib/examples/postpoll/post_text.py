#!/usr/bin/env python3
"""Text posting example"""

##########################################################################
#
#   Posting example
#
#   Periodically post a message to a news group
#
#   2022-10-10  Todd Valentic
#               Initial implementation
#
##########################################################################

import sys

from datatransport import ProcessClient
from datatransport import NewsPoster


class Client(ProcessClient):
    """Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)

        self.rate = self.config.get_rate("rate")
        self.text = self.config.get("text")

        self.log.info("Post message every %s", self.rate.period)

    def main(self):
        """Main application"""

        while self.wait(self.rate):
            self.news_poster.post_text(self.text)
            self.log.info("Posted message")


if __name__ == "__main__":
    Client(sys.argv).run()
