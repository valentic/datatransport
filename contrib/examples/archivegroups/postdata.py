#!/usr/bin/env python
"""Post test data files"""

##########################################################################
#
#   Post test data files
#
#   2022-11-04  Todd Valentic
#               Initial implementation
#
##########################################################################

import bz2
import gzip
import pathlib
import sys
import zipfile

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport.utilities import remove_file, make_path


class PostData(ProcessClient):
    """Data Poster"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

    def init(self):
        super().init()

        self.news_poster = NewsPoster(self)
        self.filenames = self.config.get_list("filenames")

    def save_zip(self, filename, message):
        """Save as zip file"""

        with zipfile.ZipFile(filename, "w") as archive:
            archive.writestr("content", message)

    def save_gzip(self, filename, message):
        """Save as gzip file"""

        with gzip.open(filename, "wt") as archive:
            archive.write(message)

    def save_bzip2(self, filename, message):
        """Save as bzip2 file"""

        with bz2.open(filename, "wt") as archive:
            archive.write(message)


    def main(self):
        """Main loop"""

        rate = self.config.get_rate("rate", 60)

        counter = 0

        while self.wait(rate):

            now = self.now()
            message = f"Index: {counter}"

            postnames = []

            for name in self.filenames:

                filename = pathlib.Path(now.strftime(name))
                make_path(filename)

                if filename.suffix == ".zip":
                    self.save_zip(filename, message)

                elif filename.suffix == ".gz":
                    self.save_gzip(filename, message)

                elif filename.suffix == ".bz2":
                    self.save_bzip2(filename, message)

                else:
                    filename.write_text(message, encoding='utf-8')

                postnames.append(str(filename))

            counter += 1

            self.log.info("Posting files: %s", postnames) 

            self.news_poster.post(postnames)
            remove_file(postnames)


if __name__ == "__main__":
    PostData(sys.argv).run()
