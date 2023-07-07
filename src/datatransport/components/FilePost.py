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
##########################################################################

import os
import sys
import glob
import time

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport import ConfigComponent
from datatransport.utilities import remove_file


class Watcher(ConfigComponent):
    def __init__(self, name, parent):
        ConfigComponent.__init__(self, "watch", name, parent)
    
        self.news_poster = NewsPoster(self)

        self.file_patterns = self.get_list("files")
        self.remove_files = self.get_boolean("removefiles", True)
        self.group_files = self.get_boolean("groupfiles", False)

        self.log.info("Watch: %s" % name)
        self.log.info("  Posting to %s" % self.get("post.newsgroup"))
        self.log.info("  Watching for: %s" % self.file_patterns)

    def find_files(self):

        filenames = []

        for pattern in self.file_patterns:
            filenames.extend(glob.glob(pattern))

        filenames = [f for f in filenames if os.path.isfile(f)]
        filenames.sort()

        if self.group_files and filenames:
            filenames = [filenames]

        return filenames

    def check(self):

        files = self.find_files()

        if not files:
            self.log.debug("No files present, sleeping")
            return

        for filegroup in files:

            try:
                starttime = time.time()
                self.news_poster.post(filegroup)
                elapsed = time.time() - starttime
                self.log.info("Files posted (%.2f s): %s" % (elapsed, filegroup))
            except:
                self.log.exception("Problem posting files")
                return

            if self.remove_files:
                try:
                    remove_file(filegroup)
                except:
                    self.log.exception("Problem deleting file: %s" % filegroup)


class FilePost(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.rate = self.get_rate("rate")
        self.watches = self.get_components("watches", Watcher)

    def process(self):

        for watch in self.watches.values():
            watch.check()

    def main(self):

        while self.wait(self.rate):
            self.process()


def main():
    FilePost(sys.argv).run()
