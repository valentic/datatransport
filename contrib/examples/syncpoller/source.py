#!/usr/bin/env python3
"""Generate source messages"""

import sys

from datatransport import ProcessClient
from datatransport import NewsPoster


class Source(ProcessClient):
    """Source Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.rate = self.config.get_rate("post.rate", 60)
        self.poster = NewsPoster(self)

        self.log.info("rate: %s", self.rate)

    def main(self):
        """Main application"""

        while self.wait(self.rate):
            msg = f"[self.name] {self.now()}"
            self.poster.post_text(msg)
            self.log.info("Posted message")


if __name__ == "__main__":
    Source(sys.argv).run()
