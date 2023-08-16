#!/usr/bin/env python3
"""Post data files component"""

############################################################################
#
#   PostDataFiles
#
#   This script watches for new radar data files to appear and posts them
#   to the newsserver. There is an option not to remove the original file
#   under the assumption that someone else will in the future. It can also
#   compress the files prior to posting using bzip to reduce their size
#   (we get about a 30% reduction in size on binary MEDAC data).
#
#   The data files are assumed to have a name with the following format:
#
#       <index>.<ext>
#
#   The <index> is a monotonically increasing value that can be tracked to
#   determine if the file has been posted before. The <ext> can be any
#   arbitrary string. The algorithm for determing which new files to post
#   is based on the finding files in the specified directory and with the
#   specified name that are newer since the last time the poll was taken.
#   Of these new files, the index values are compared to the previously
#   posted file and only newer files are posted.
#
#   It is assumed that the newest file in the directory is still being
#   written to by the data aqcuisition system and shouldn't be posted.
#   You can override this behaviour with the "include_current" option.
#
#   1.0.0   2001-02-20  Todd Valentic
#           Initial implementation.
#
#   1.0.1   2001-11-30  Todd Valentic
#           Quote the the filename pattern in the poll() method.
#           Added some debugging message to verbose level 2.
#
#   1.0.2   2001-12-02  Todd Valentic
#           Only update the timestamp file as each source file is
#               processed. Update the time stamp not with the current
#               time, but the time of the source file.
#           Added signal handling to make sure we done a clean exit.
#
#   2.0.0   2002-01-18  Todd Valentic
#           Generalized from PostDataFiles to handle multiple types of
#               radar data.
#
#   2.0.1   2002-03-22  Todd Valentic
#           Remove signal handling (use ProcessClient's).
#           Use commands.getstatusoutput() in compress call.
#
#   2.0.2   2002-03-28  Todd Valentic
#           Change default value of startCurrent to false.
#
#   2.0.3   2002-08-15  Todd Valentic
#           Changed the comparison to handle generic string operations.
#               The filename does not need to be strictly a number anymore.
#           Made file compression optional. The conf option is "compress"
#               and defaults to true.
#           Added option to remove original file (removeFile). Default 0.
#           Added option to only post last N files found (default to all).
#
#   2.0.4   2002-08-27  Todd Valentic
#           Setup with configure script.
#           sri.transport -> Transport
#           split runtime into script and class module.
#
#   2.0.5   2003-04-16  Todd Valentic
#           Use string methods instead of module.
#
#   2.0.6   2003-04-18  Todd Valentic
#           Added ability to specify pollrate in days/hours/mins/secs.
#           Added sync option for wait.
#           If the timestamp file doesn't exist, initialize its time
#               to something really old (Jan 1, 1975). We start off
#               by looking for files newer then that file (unless
#               startCurrent==1). It used to be initialized to the
#               current time and old files never got pulled in when
#               first ran.
#
#   2.0.7   2003-05-02  Todd Valenic
#           Fixed bug in log reporting when a file had already been
#               processed (it was trying to print a string as an int).
#
#   2.0.8   2003-05-03  Todd Valentic
#           Added check_index to turn off index checking.
#
#   2.0.9   2003-06-20  Todd Valentic
#           Added filedate callback.
#
#   2.0.10  2003-08-14  Todd Valentic
#           createCallback -> get_callback
#           createDeltaTime -> getDeltaTime
#
#   2.0.11  2004-02-13  Todd Valentic
#           Skip compression if file is already compressed.
#           Add a maximum file size limit.
#
#   2.0.12  2004-05-07  Todd Valentic
#           Print input path/name to log at startup.
#
#   2.0.13  2004-05-28  Todd Valentic
#           Fixed bug when reporting compression ratio and the
#               input file is 0 length.
#
#   2.0.14  2004-12-27  Todd Valentic
#           Convert from mx.DateTime to datetime
#
#   2.0.15  2005-04-03  Todd Valentic
#           Use library functions to replace external calls to touch
#           Use library bz2 module
#
#   2.0.16  2005-05-04  Todd Valentic
#           Fix bug when timestamp file not present.
#           Changed a number of config parameters to booleans
#
#   2006-10-14  Todd Valentic
#               Convert headers in post to a dict from a list
#
#   2009-11-24  Todd Valentic
#               Use now()
#
#   2015-11-23  Todd Valentic
#               Add md5 checksum header.
#
#   2015-11-30  Todd Valentic
#               Use get_rate() for pollrate
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               Use get_ config methods
#               Python3 updates:
#                   commands -> subprocess
#                   removeFile -> remove_file
#                   sizeDesc -> size_desc
#                   currentTime -> now
#                   NewsPoster
#
#   2023-07-26  Todd Valentic
#               Updated for transport3 / python3
#
############################################################################

import bz2
import hashlib
import math
import nntplib
import os
import shutil
import subprocess
import sys
import time

from pathlib import Path

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport.utilities import size_desc


class PostDataFiles(ProcessClient):
    """Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)

        self.exit_on_failure = self.config.get_boolean("exit_on_error", False)

        self.input_name = self.config.get("input.name", "*.DAT")
        self.input_path = self.config.get("input.path", ".")
        self.include_current = self.config.get_boolean("include_current", False)
        self.compress = self.config.get_boolean("compress", True)
        self.remove_files = self.config.get_boolean("remove_files", False)
        self.max_files = self.config.get_int("max_files")
        self.max_size = self.config.get_bytes("max_size", "20Mb")
        self.check_index = self.config.get_boolean("check_index", True)
        self.check_size = self.config.get_boolean("check_size", True)

        self.pollrate = self.config.get_rate("pollrate", 60)
        self.filedate = self.config.get_callback("filedate", self.filedate_callback)

        self.timefile = Path("timestamp")
        self.indexfile = Path("index")

        if not self.timefile.exists():
            # Default to sometime long ago
            self.timefile.write_text("0", "utf-8")
            timestamp = time.mktime((1975, 1, 1, 0, 0, 0, 0, 0, 0))
            os.utime(self.timefile, (timestamp, timestamp))

        if self.config.get_boolean("start_current", False):
            os.utime(self.timefile, None)

        self.log.info("Input path: %s", self.input_path)
        self.log.info("Input name: %s", self.input_name)

    def filedate_callback(self, _filename):
        """Extract timestamp from file"""

        return None

    def split(self, filename):
        """Split file into chunks"""

        filesize = filename.stat().st_size

        if not self.check_size or filesize <= self.max_size:
            return [filename]

        num_chunks = math.ceil(filesize / self.max_size)
        chunks = []

        with filename.open("rb") as f:
            for chunk in range(num_chunks):
                data = f.read(self.max_size)
                chunkname = Path(f"chunk.{chunk:03d}")
                chunkname.write_bytes(data)
                chunks.append(chunkname)

            self.log.info("  - split into %d parts", num_chunks)

        return chunks

    def compute_checksum(self, filename):
        """Compute checksum"""

        with filename.open("rb") as f:
            digest = hashlib.file_digest(f, "md5")

        return digest.hexdigest()

    def post(self, filename, timestamp):
        """Post file to newsgroup"""

        filenames = self.split(filename)
        numparts = len(filenames)
        checksum = self.compute_checksum(filename)

        for part, filepart in enumerate(filenames):
            headers = {}
            if numparts > 1:
                headers["X-Transport-Part"] = f"{part}/{numparts}"
                headers["X-Transport-Filename"] = filename.stem

            # Note - checksum of the *entire* file, not part
            headers["X-Transport-md5"] = checksum

            filesize = filepart.stat().st_size
            self.log.debug("  - posting %s (%s)", filepart, size_desc(filesize))
            self.news_poster.post([filepart], date=timestamp, headers=headers)

            if numparts > 1:
                os.remove(filepart)

    def valid_index(self, filename):
        """Check file is larger than last index"""

        if not self.check_index:
            return True

        if not self.indexfile.exists():
            return True

        last_filename = self.indexfile.read_text("utf-8")

        if filename.stem > last_filename:
            return True

        self.log.info("  - %s already processed (%s)", filename.stem, last_filename)

        return False

    def process_file(self, filename):
        """Process file (compress, split, post)"""

        self.log.info("Processing %s", filename)

        # Check if we have seen this file before

        if not self.valid_index(filename):
            return

        # Get timestamp from file

        try:
            timestamp = self.filedate(filename)
            if timestamp:
                self.log.debug("  - file timestamp %s", timestamp)
        except Exception:  # pylint: disable=broad-exception-caught
            self.log.exception("Error calling routine to determine file timestamp")
            return

        # Compress the file

        bzipext = ".bz2"
        zipname = filename.with_suffix(filename.suffix + bzipext)

        if self.compress and filename.suffix != bzipext:
            starttime = self.now()

            self.log.debug("  - compressing file")
            with filename.open("rb") as infile:
                with bz2.BZ2File(zipname, "wb", compresslevel=9) as outfile:
                    shutil.copyfileobj(infile, outfile)

            orgsize = filename.stat().st_size
            zipsize = zipname.stat().st_size

            if orgsize > 0:
                zippct = (zipsize / orgsize) * 100
            else:
                zippct = 0

            totaltime = self.now() - starttime
            self.log.info(
                "  - %s -> %s (%d%%) %s",
                size_desc(orgsize),
                size_desc(zipsize),
                zippct,
                totaltime,
            )

            postfile = zipname

        else:
            postfile = filename

        # Post file to news server

        try:
            self.post(postfile, timestamp)
        except nntplib.NNTPError as err:
            self.log.error("Problem posting file: %s", err)
            return

        # Cleanup files

        if zipname.exists():
            zipname.unlink()

        if self.remove_files:
            try:
                filename.unlink()
                self.log.debug("  - removed original file: %s", filename)
            except OSError as err:
                self.log.error("Problem removing file %s: %s", filename, err)

        # Update the index file

        if self.check_index:
            self.indexfile.write_text(filename.stem, "utf-8")

    def poll(self):
        """Poll for new files"""

        # pylint: disable=consider-using-f-string

        cmd = 'find %s -newer %s -type f -name "%s" -print' % (
            self.input_path,
            self.timefile,
            self.input_name,
        )

        status, output = subprocess.getstatusoutput(cmd)

        if status != 0:
            self.log.debug("Problem running find")
            self.log.debug("cmd: %s", cmd)
            self.log.debug("status: %s", status)
            self.log.debug("output: %s", output)
            return []

        filelist = sorted(output.split("\n"))

        if not self.include_current:
            # exclude the current file
            filelist = filelist[:-1]

        if self.max_files:
            # only keep the last N files
            filelist = filelist[-self.max_files :]

        return [Path(filename) for filename in filelist]

    def process(self):
        """Post any new files"""

        filenames = self.poll()

        self.log.debug("Polling - found %d new files.", len(filenames))

        for filename in filenames:
            timestamp = filename.stat().st_mtime
            self.process_file(filename)
            os.utime(self.timefile, (timestamp, timestamp))

            if self.is_stopped():
                return

    def main(self):
        """Main application"""

        while self.wait(self.pollrate):
            try:
                self.process()
            except Exception as err:  # pylint: disable=broad-exception-caught
                if self.exit_on_error:
                    self.log.exception("Problem processing")
                    return
                self.log.error("Problem processing: %s", err)


def main():
    """Script entry point"""
    PostDataFiles(sys.argv).run()
