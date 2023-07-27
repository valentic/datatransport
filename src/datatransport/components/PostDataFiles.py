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
import glob
import math
import os
import subprocess
import sys
import time

from datetime import datetime

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport.utilities import size_desc


class PostDataFiles(ProcessClient):
    """Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)

        self.input_name = self.get("input.name", "*.DAT")
        self.input_path = self.get("input.path", ".")
        self.include_current = self.get_boolean("include_current", False)
        self.compress = self.get_boolean("compress", True)
        self.remove_files = self.get_boolean("remove_files", False)
        self.max_files = self.get_int("max_files")
        self.max_size = self.get_bytes("max_size", "20Mb")
        self.check_index = self.get_boolean("check_index", True)
        self.check_size = self.get_boolean("check_size", True)

        self.pollrate = self.get_rate("pollrate", "5")
        self.filedate = self.get_callback("filedate", self.filedate_callback)

        self.timefile = "timestamp"
        self.indexfile = "index"

        if not os.path.isfile(self.timefile):
            # Default to sometime long ago
            open(self.timefile, "w").write("0")
            t = time.mktime((1975, 1, 1, 0, 0, 0, 0, 0, 0))
            os.utime(self.timefile, (t, t))

        if self.get_boolean("startCurrent", False) == 1:
            os.utime(self.timefile, None)

        if not os.path.isfile(self.indexfile):
            open(self.indexfile, "w").write("0")

        self.log.info("Input path: %s" % self.input_path)
        self.log.info("Input name: %s" % self.input_name)

    def filedate_callback(self, file):
        return None

    def split(self, filename):

        filesize = os.path.getsize(filename)

        if not self.check_size or filesize <= self.max_size:
            return [filename]

        numchunks = int(math.ceil(filesize / float(self.max_size)))
        chunks = []
        file = open(filename, "rb")

        for chunk in range(numchunks):
            data = file.read(self.max_size)
            chunkname = f"chunk.{chunk:03d}"
            open(chunkname, "wb").write(data)
            chunks.append(chunkname)

        self.log.info("  - split into %d parts" % numchunks)

        return chunks

    def get_checksum(self, filename):
        # Shell out - some files might be quite large
        status, output = subprocess.getstatusoutput("md5sum %s" % filename)

        if status != 0:
            return None

        return output.split()[0]

    def post(self, filename, timestamp):

        files = self.split(filename)
        part = 1
        numparts = len(files)
        basename = os.path.basename(filename)
        checksum = self.get_checksum(filename)

        for file in files:

            headers = {}
            if numparts > 1:
                headers["X-Transport-Part"] = "%d/%d" % (part, numparts)
                headers["X-Transport-Filename"] = basename
                part += 1

            if checksum:
                # Note - checksum of the *entire* file, not part
                headers["X-Transport-md5"] = checksum

            filesize = os.path.getsize(file)
            self.log.debug("  - posting %s (%s)" % (file, size_desc(filesize)))
            self.news_poster.post([file], date=timestamp, headers=headers)

            if numparts > 1:
                os.remove(file)

    def process(self, file):

        # Compress the file

        self.log.info("Processing %s" % file)

        bzipext = ".bz2"
        basename = os.path.basename(file)
        baseext = os.path.splitext(basename)[1]
        isCompressed = baseext == bzipext
        zipname = basename + bzipext
        lastindex = open(self.indexfile).readline()

        if self.check_index:
            try:
                curindex = os.path.splitext(basename)[0]
            except:
                self.log.error("Cannot determine index of %s" % basename)
                return

            if curindex <= lastindex:
                self.log.info(
                    "  - the file %s has been processed before (index=%s)"
                    % (basename, lastindex)
                )
                return

        try:
            date = self.filedate(file)
            if date:
                self.log.debug("  - file date: %s" % date)
        except:
            self.log.exception("Error calling routine to determine file date")
            return

        if self.compress and not isCompressed:

            starttime = self.now()

            self.log.debug("  - compressing file")
            data = open(file).read()
            open(zipname, "w").write(bz2.compress(data))

            orgsize = os.path.getsize(file)
            zipsize = os.path.getsize(zipname)

            if orgsize > 0:
                zippct = (zipsize / float(orgsize)) * 100
            else:
                zippct = 0

            totaltime = self.now() - starttime
            self.log.info(
                "  - %s -> %s (%d%%) %s"
                % (size_desc(orgsize), size_desc(zipsize), zippct, totaltime)
            )

            postfile = zipname

        else:

            postfile = file

        # Post file to news server

        try:
            self.post(postfile, date)
        except:
            self.log.exception("Problem post file")
            return

        # Cleanup files

        remove_file(zipname)

        if self.remove_files:
            try:
                remove_file(file)
                self.log.debug("  - removed original file: %s" % file)
            except:
                self.log.exception("Problem removing file: %s" % file)

        # Update the index file

        if self.check_index:
            file = open(self.indexfile, "w").write(str(curindex))

    def poll(self):

        cmd = 'find %s -newer %s -type f -name "%s" -print' % (
            self.input_path,
            self.timefile,
            self.input_name,
        )

        (status, filelist) = subprocess.getstatusoutput(cmd)  # run command, get output

        if status != 0:
            return []

        filelist = filelist.split()  # make list, break at \n
        filelist.sort()

        if not self.include_current:
            filelist = filelist[0:-1]  # don't include the current file

        if self.max_files:  # keep only the last N files
            filelist = filelist[-self.max_files :]

        return filelist

    def do_run(self):

        try:
            files = self.poll()
            self.log.debug("Polling - found %d new files." % len(files))

            for file in files:
                timestamp = os.path.getmtime(file)
                self.process(file)
                os.utime(self.timefile, (timestamp, timestamp))
                if self.is_stopped():
                    return

        except:
            self.log.exception("Failure in run")

    def main(self):

        while self.wait(self.pollrate):
            self.do_run()

        self.log.error("Exiting")


def main():
    PostDataFiles(sys.argv).run()
