#!/usr/bin/env python

##############################################################################
#
# FileStore
#
# This script collects data from the polled newsgroup and transfers the
# files into directories on the destination server. The output files are
# written into directories with the following format:
#
# path/name
#
# In the default case, these translate into:
#
# ./YYYY-DDD-hh-mm-ss-filename
#
#  YYYY = Year
#  DDD  = Day of year (001-366)
#  hh   = Hour (00-23)
#  mm   = Minute (00-59)
#  ss   = Second (00-59)
#
# There is a directory structure formed from the date. The filename has
# date and time prefixed to the filename in the message. This last part
# is done to ensure that each file has a unique name even if the file
# that was originally posted always has the same name.
#
# The output naming is completely controllable by the user with the
# dest.path and dest.name parameters. In the default case, these are
# set to:
#
#  dest.path= ./
#  dest.name = %Y-%j-%H-%M-%S-<filename>
#
# There are two macros that can be used in any of the parts and will be
# expanded at run-time:
#
#   <filename>     - The name of the file given in the original message
#   <rule>         - Text part of a rule match (see below).
#
# Matching rules let you distribute the received files into different
# directories based on on the filenames. The 'match' config parameter is a
# list of tuples, each having a fnmatch-style rule and a string to be
# pasted into the 'rule' section of the output name. The default rule is:
#
# match:   [('*','')]
#
# which matches any input file and doesn't insert anything into the pathname.
# Instead, if you wanted to store incoming jpeg's into an image directory,
# and text messages in another, you could give the rules:
#
# match: [('*.jpg','images'),('*.txt','text')]
#
#
# History:
#
#   1.0.0   1999-12-02  TAV
#
#   1.0.1   2000-02-18  TAV
#           Fixed bug in compute_name() that caused the year to only be
#               the first two digits (i.e. 2000 -> 20).
#
#   1.0.2   2000-10-24  TAV
#           Removed the dependance on DateTime module (can do everything
#               with just the standard time module).
#           Changed the naming convention for the output files.
#
#   1.0.3   2000-10-26  TAV
#           Added match rule sets.
#
#   1.0.4   2001-08-10  TAV
#           Fixed NULL -> None.
#           Added transform function.
#
#   1.0.3   2001-08-11  TAV
#           Started to make more robust to failures to copy files. This
#             effort is focused on checking return codes to os.system().
#           Added  abort_on_error config parameter to halt on errors.
#
#   1.0.4   2001-11-09  TAV
#           Changed NewsTool -> NewsTool
#
#   1.0.5   2002-01-25  Todd Valentic
#           Updated to new NewsPollMixin interface.
#
#   1.0.6   2002-08-27  Todd Valentic
#           Configured through the configure script.
#           sri.transport -> Transport
#
#   2016-12-25  Todd Valentic
#               Restored into components package - warning OLD code!
#
#   2022-10-07  Todd Valentic
#               Python3 port
#                   exec -> exec()
#               NewsPoller
#               Note that this old code is currently non-working
#
##############################################################################

import fnmatch
import ftplib
import os
import string
import sys
import time

from datatransport import ProcessClient
from datatransport import NewsPoller
from datatransport import newstool


class FileStore(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poller = NewsPoller(self, callback=self.process)
        self.main = self.news_poller.main

        method = self.get("method", "copy")
        transform = self.get("transform", None)

        self.dest_path = self.get("dest.path", "./")
        self.dest_name = self.get("dest.name", "%Y-%j-%H-%M-%S-<filename>")
        self.abort_on_error = self.get_int("abortOnError", 1)

        if method == "copy":
            self.transfer = self.copy_file
            self.log.debug("Using the copy transfer method")

        elif method == "ftp":
            self.transfer = self.ftp_file
            self.log.debug("Using the ftp transfer method")

            self.dest_server = self.get("dest.server")
            self.dest_username = self.get("dest.username", "anonymous")
            self.dest_password = self.get("dest.password", "transport@")
            self.dest_sleep = self.get_int("dest.sleep", 5)

            if not self.dest_server:
                self.abort("The destination server is not set")

        else:
            self.abort("Unknown transfer method: %s" % method)

        # Test the dest.path and dest.prefix to make sure no badness happens

        curtime = time.localtime(time.time())

        try:
            time.strftime(self.dest_path, curtime)
        except:
            self.abort("There is a problem with the formatting of dest.path")

        try:
            time.strftime(self.dest_name, curtime)
        except:
            self.abort("There is a problem with the formatting of dest.name")

        # Get matching rules

        try:
            self.rules = eval(self.get("match", "[('*','')]"))
        except:
            self.abort("There was a problem reading the match rules")

        # Try to load the transform module

        if transform:
            try:
                module, function = os.path.splitext(transform)
                exec("import %s" % module)
                exec("self.transform = %s" % transform)
            except:
                self.abort("There was a problem loading the transform module.")
        else:
            self.transform = None

    def compute_name(self, header, basename, rule):

        # Assume that the date is at the end and between brackets ([])

        date = string.split(header, "[")[-1]
        dt = time.strptime(date[:-1], "%c")

        filename = os.path.join(self.dest_path, self.dest_name)

        filename = time.strftime(filename, dt)
        filename = string.replace(filename, "<rule>", rule[1])
        filename = string.replace(filename, "<filename>", basename)

        # Do a split in case someone puts path parts in dest_name

        return os.path.split(filename)

    def ftp_file(self, basename, header, rule):

        path, name = self.compute_name(header, basename, rule)

        ftp = ftplib.FTP(self.dest_server)
        ftp.login(self.dest_username, self.dest_password)

        parts = string.split(path, "/")

        if path[0] == "/":
            ftp.cwd("/")

        self.log.debug("Remote path: %s" % path)

        for part in parts[1:]:
            try:
                ftp.cwd(part)
            except:
                ftp.mkd(part)
                ftp.cwd(part)

        self.log.debug("Remote file name: %s" % basename)

        file = open(basename, "r")
        ftp.storbinary("STOR %s" % name, file, 1024)
        file.close()

        os.remove(basename)

        # Some systems don't like a bunch of data ftp'd in a very short
        # amount of time (part of the intrusion detection). So, we sleep
        # for a bit to pace things out.

        time.sleep(self.dest_sleep)

    def copy_file(self, basename, header, rule):

        path, name = self.compute_name(header, basename, rule)

        self.log.debug("basename=%s" % basename)
        self.log.debug("path=%s" % path)
        self.log.debug("name=%s" % name)

        try:
            if not os.path.isdir(path):
                os.path.makedirs(path)
        except:
            msg = "Failed to create path: %s" % path
            if self.abort_on_error:
                self.abort(msg)
            else:
                self.log.error(msg)
                raise newstool.ProcessError

        if os.system("cp %s %s/%s" % (basename, path, name)) != 0:
            msg = "Failed to copy file to: %s/%s. Permission problem?" % (path, name)
            if self.abort_on_error:
                self.abort(msg)
            else:
                self.log.error(msg)
                raise newstool.ProcessError

        os.remove(basename)

        self.log.debug("Copied file to: %s/%s" % (path, name))

    def find_match(self, filename):

        self.log.debug("Trying to match rules to file=%s" % filename)

        for rule in self.rules:
            if fnmatch.fnmatch(filename, rule[0]):
                self.log.debug(" - yes: rule=%s" % rule)
                return rule
            self.log.debug(" - no : rule=%s" % rule)

        self.log.debug("No matching rule found")

        return None

    def process(self, message):
        
        filenames = newstool.save_files(message)

        for filename in filenames:

            rule = self.find_match(filename)

            if rule is None:
                self.log.debug("No matching rule for the file: %s" % filename)
                continue

            if self.transform:
                self.log.debug("Calling transform function")
                self.log.debug("  before: %s" % filename)
                filename = self.transform(filename)
                self.log.debug("  after: %s" % filename)

            try:
                self.transfer(filename, header, rule)
                self.log.info("Transfered file: %s" % header)
            except:
                self.log.error("Failure to transfer file: %s" % header)
                os.system("rm -f %s" % filename)
                raise newstool.ProcessError


def main():
    FileStore(sys.argv).run()
