#!/usr/bin/env python3
"""FileWatch component"""

# pylint: disable=broad-exception-caught

##########################################################################
#
#   FileWatch
#
#   This transport component script watches for new files to appear in
#   a specified directory and posts them into a given newsgroup. If the
#   newsgroup does not exist when the script starts, it will try to
#   create it. Multiple files can be listed and they will be posted as
#   a group of attachments in a single message once they are all present.
#   This is a useful feature if you have data files that belong together
#   and should stay bundled in the transport network. Once the files are
#   posted, they are removed by this script. An option exists to leave
#   the files as well. For the files to be removed, they need to have
#   write permission for the transport user.
#
#   Config options:
#
#       (includes ProcessClient and NewsPoster options)
#
#       pollrate    - Integer, rate at which to check for new files (seconds)
#       remove_files - [0,1] flag indicating if files should be removed
#       watchpath   - String, path to look for files.
#       watchfiles  - String, list of file names to look for. If multiple
#                     names are listed, they should be separated by spaces.
#                     The name can include normal shell wildcards.
#
#   1.0.0   2000-??-??  TAV
#           Initial implementation.
#
#   1.0.1   2001-09-07  TAV
#           Changed script to abort at start up if no files are listed.
#           Check to see if the file still exists before trying to remove it.
#             This happens when setting things up and the group doesn't
#             have permission to remove the file. You'll manually remove
#             it and fix up the script writing the file. In the mean time
#             filewatch would try to remove the nonexistent file and crash.
#           Changed setStatus() -> setStatusCode().
#
#   1.0.2   2002-01-25  Todd Valentic
#           Added check for self.running.
#
#   1.0.3   2002-08-27  Todd Valentic
#           Configured through configure script
#           sri.transport -> Transport
#
#
#   1.0.4   2002-12-12  Todd Valentic
#           Removed setting of state in network (this is old code and not used).
#           Catch errors in posting.
#           Handled error on removing file better.
#
#   1.0.5   2002-12-18  Todd Valentic
#           Changed option names to be more consistent:
#               watchpath   -> watch.path
#               watchfiles  -> watch.files
#               pollrate    -> watch.rate
#               remove_files -> watch.removefiles
#
#   1.0.6   2004-07-02  Todd Valentic
#           Change rate to be DeltaDateTime.
#           Fixed reporting error when files cannot be removed.
#
#   1.0.7   2005-02-08  Todd Valentic
#           Added grouping option.
#           Make sure to sort file list.
#           Code clean up.
#
#   1.0.8   2005-10-07  Todd Valentic
#           Make sure watch.files has a default empty config value.
#
#   2022-10-07  Todd Valentic
#               Python3 port:
#                   Reorder imports
#                   removeFile -> remove_file
#                   NewsPoster
#
#   2023-07026  Todd Valentic
#               Use new config interface
#
##########################################################################

import sys

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport.utilities import remove_file


class FileWatch(ProcessClient):
    """Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)

        self.pollrate = self.config.get_rate("watch.rate", 60)
        self.remove_files = self.config.get_boolean("watch.removefiles", True)
        self.group_files = self.config.get_boolean("watch.groupfiles", False)

        self.watchpath = self.config.get_path("watch.path", ".")
        self.filespecs = self.config.get_list("watch.files")

        if not self.filespecs:
            self.abort("No watch files listed in the config file.")

        self.log.info("Posting to %s", self.config.get("post.newsgroup"))
        self.log.info("Watching path: %s", self.watchpath)
        self.log.info("Watching for: %s", self.filespecs)

    def find_files(self):
        """Find files to post"""

        readyfiles = []

        for filespec in self.filespecs:
            files = [f for f in self.watchpath.glob(filespec) if f.is_file()]
            readyfiles.extend(files)

        return sorted(readyfiles)

    def process(self):
        """Process files ready to post"""

        files = self.find_files()

        if not files:
            self.log.debug("No files present, sleeping")
            return

        if self.group_files:
            files = [files]

        for filegroup in files:
            try:
                starttime = self.now()
                self.news_poster.post(filegroup)
                elapsed = self.now() - starttime
                self.log.info("Files posted (%s): %s", elapsed, filegroup)
            except Exception:
                self.log.exception("Problem posting files")
                return

            if self.remove_files:
                try:
                    remove_file(filegroup)
                except Exception:
                    self.log.exception("Problem deleting file: %s", filegroup)

    def main(self):
        """Main application"""

        while self.wait(self.pollrate):
            self.process()


def main():
    """Script entry"""
    FileWatch(sys.argv).run()
