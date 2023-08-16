#!/usr/bin/env/python3
"""File Post Component"""

##########################################################################
#
#   FilePost
#
#   This transport component watches for specified files to appear and
#   posts them into a newsgroup. If the newsgroup does not exist, it
#   will be created. Multiple files can be listed and they will be posted
#   as a group of attachments in a single message. This is a useful
#   feature if you have data files that belong together and should stay
#   bundled in the transport network. Once the files are posted, they are
#   removed. An option exists to leave the files as well. For the files
#   to be removed, they need to have write permission for the transport user.
#
#   The component is based on the original FileWatch componment. It
#   expands on it by allowing you to specify multiple groups of files
#   to post, each with its own destination news group. This approach
#   scales much better when there are a number of groupings.
#
#   It uses the standard transport ConfigComponent to specify the
#   groups. Each grouping can list:
#
#       post.newsgroup (and other related options for NewsPoster)
#       remove_files - remove files after posting (default True)
#       group_files - post all files to one message (default False)
#       files - list of file names (including path) to look for. If
#               multiple names are listed, they should be separated
#               by spaces. The name can include normal shell wildcards.
#
#   2010-08-16  Todd Valentic
#               Initial implementation
#
#   2017-01-11  Todd Valentic
#               Handle empty filegroup list
#
#   2022-10-12  Todd Valentic
#               Python3 port
#                   Transport -> datatransport
#                   removeFile -> remove_file
#                   NewsPoster
#
#   2023-07-27  Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import sys

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport import ConfigComponent
from datatransport.utilities import remove_file


class Watcher(ConfigComponent):
    """Watch group component"""

    def __init__(self, *p, **kw):
        ConfigComponent.__init__(self, "watch", *p, **kw)

        self.news_poster = NewsPoster(self)

        self.watchpath = self.config.get_path("path", ".")
        self.filespecs = self.config.get_list("files")
        self.remove_files = self.config.get_boolean("removefiles", True)
        self.group_files = self.config.get_boolean("groupfiles", False)

        if not self.filespecs:
            self.abort("No watch files listed in the config file")

        self.log.info("Posting to %s", self.config.get("post.newsgroup"))
        self.log.info("Watching path: %s", self.watchpath)
        self.log.info("Watching for: %s", self.filespecs)

    def find_files(self):
        """Find matching files to post"""

        filenames = []

        for filespec in self.filespecs:
            filenames.extend(self.watchpath.glob(filespec))

        filenames = [f for f in filenames if f.is_file()]

        return sorted(filenames)

    def process(self):
        """Check for new files"""

        filenames = self.find_files()

        if not filenames:
            self.log.debug("No files present")
            return

        if self.group_files:
            filenames = [filenames]

        for filegroup in filenames:
            starttime = self.now()

            try:
                self.news_poster.post(filegroup)
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.log.exception("Problem posting files: %s", e)
                return

            elapsed = (self.now() - starttime).total_seconds()
            
            if isinstance(filegroup, list):
                names = [str(n) for n in filegroup]
            else:
                names = filegroup

            self.log.info("Files posted (%0.2fs): %s", elapsed, names)

            if self.remove_files:
                try:
                    remove_file(filegroup)
                except OSError as e:
                    self.log.exception("Problem deleting file %s: %s", filegroup, e)


class FilePost(ProcessClient):
    """Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.rate = self.config.get_rate("pollrate")
        self.watches = self.config.get_components("watches", factory=Watcher)

    def process(self):
        """Process each file watch group"""

        for watch in self.watches.values():
            watch.process()

            if self.is_stopped():
                break

    def main(self):
        """Main application"""

        while self.wait(self.rate):
            self.process()


def main():
    """Script entry point"""
    FilePost(sys.argv).run()
