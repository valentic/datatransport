#!/usr/bin/env python3
"""File posting example"""

##########################################################################
#
#   File post example
#
#   Periodically post a file to a news group
#
#   2022-10-10  Todd Valentic
#               Initial implementation
#
##########################################################################

import sys
import pathlib

from datatransport import ProcessClient
from datatransport import NewsPoster


class Client(ProcessClient):
    """Process Client"""

    def __init__(self, args):
        ProcessClient.__init__(self, args)

        self.news_poster = NewsPoster(self)

        self.rate = self.config.get_rate("rate")
        self.text = self.config.get("text")

        self.log.info("Post message every: %s", self.rate.period)

    def main(self):
        """Main application"""

        filename = pathlib.Path("data.txt")

        while self.wait(self.rate):
            filename.write_text(self.text, encoding="utf-8")

            self.news_poster.post(filename)
            self.log.info("Posted %s", filename)

            filename.unlink()


if __name__ == "__main__":
    Client(sys.argv).run()
