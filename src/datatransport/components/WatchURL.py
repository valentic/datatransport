#!/usr/bin/env python3
"""WatchURL Component"""

#####################################################################
#
#   WatchURL
#
#   This script watches a URL (which, for example, can be a web
#   page or an image) and posts it to the specified newsgroup when
#   a new version appears.
#
#   Based on code written by Angela Li (SRI International).
#
#   History:
#
#   1.0.0   2002-01-15  TAV
#           Initial implementation.
#
#   1.0.1   2002-09-03  Todd Valentic
#           Moved to python2, sri.transport -> Transport
#           Use python2 md5's hexdigest() (replace local hexstr()).
#           Added retry time for problem sites
#           Added header checks, exclude list
#           Added indirect url features.
#
#   1.0.2   2002-10-13  Todd Valentic
#           Added ability to create thumbnails. These are posted
#               as another attachment in the message. Makes it
#               nice when used with ArchiveGroups and the history
#               function.
#
#   1.0.3   2003-03-02  Todd Valentic
#           Added ability to sync the pollrate.
#
#   1.0.4   2003-03-08  Todd Valentic
#           Put the news post in try..except block to catch errors.
#
#   1.0.5   2003-03-31  Todd Valentic
#           Added offset to compliment sync.
#
#   1.0.6   2003-04-16  Todd Valentic
#           Added use of timeoutsocket
#
#   1.0.7   2003-08-25  Todd Valentic
#           Use DeltaDateTime objects in config
#           Added ability to exclude image names in patterns check
#           Added images in anchor tags to those checked
#           Added small test for parser at end of file
#
#   1.0.8   2005-08-15  Todd Valentic
#           Change sync to be a boolean.
#
#   1.0.8   2009-05-11  Todd Valentic
#           md5 module deprecated in Python 2.6. Use a import check
#               to pull in right library on older systems.
#
#   1.0.8   2013-01-29  Todd Valentic
#           Add timeout parameter
#
#   1.0.9   2013-08-18  Todd Valentic
#           Add time replacement to rename rules
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               Python3 migration:
#                   commands -> subprocess
#                   <> -> !=
#                   htmllib -> html.parser
#                   urlparse -> urllib.parse
#                   removeFile -> remove_file
#                   NewsPoster
#
#   2023-07-26  Todd Valentic
#               Updated for transport3 / python3
#
#####################################################################

import datetime
import fnmatch
import os
import socket
import subprocess
import sys
import time
import urllib

from html.parser import HTMLParser
from hashlib import md5
from urllib.parse import urlparse, urljoin

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport.utilities import remove_file


class Parser(HTMLParser):
    def __init__(self, include_names, exclude_names):
        HTMLParser.__init__(self)

        self.include_patters = include_names
        self.exclude_patterns = exclude_names

    def get_images(self, url):

        self.urls = []
        self.base = url

        page = urllib.urlopen(url).read()
        self.reset()
        self.feed(page)
        self.close()

        return self.urls

    def match(self, url):

        try:
            path = urlparse(url)[2]
        except:
            return 0

        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(path, pattern):
                return 0

        for pattern in self.include_patters:
            if fnmatch.fnmatch(path, pattern):
                return 1

    def handle_image(self, src, alt, ismap, align, width, height):

        # This is a fix for one broken site

        src = src.replace("\n", "")
        src = src.replace("\r", "")

        if self.match(src):
            self.urls.append(urljoin(self.base, src))

        if self.anchor and self.match(self.anchor, self.patterns):
            self.urls.append(urljoin(self.base, self.anchor))

    def anchor_bgn(self, href, name, type):

        if self.match(href):
            self.urls.append(urljoin(self.base, href))


class WatchURL(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)

        self.pollrate = self.config.get_rate("pollrate", '10m')
        self.retryrate = self.config.get_rate("retryrate", 60)
        self.timeout = self.config.get_timedelta("timeout", 60)

        self.url = self.config.get("url", None)
        self.include_names = self.config.get_list("images", "*")
        self.exclude_names = self.config.get_list("images.exclude", "")
        self.check_headers = self.config.get_boolean("headers.enable", True)
        self.exclude_headers = self.config.get_list("headers.exclude", "Date")
        self.rename_rules = self.config.get("rename", "[]")
        self.save_body = self.config.get_boolean("save.body", True)
        self.save_images = self.config.get_boolean("save.images", False)
        self.save_thumbnails = self.config.get_boolean("save.thumbnails", False)
        self.thumbnail_cmd = self.config.get(
            "thumbnails.cmd", "convert -geometry 125x125 -sharpen 2x2"
        )
        self.thumbnail_exts = self.config.get_list("thumbnails.ext", ".jpg .png .gif")
        self.thumbnail_name = self.config.get("thumbnails.name", "%s-thumbnail.jpg")

        socket.setdefaulttimeout(self.timeout.total_seconds())

        try:
            self.rename_rules = eval(self.rename_rules)
        except:
            self.log.exception("Problem parsing the rename rules:")
            self.abort("Aborting")

        if self.url is None:
            self.abort("No URL specified")

        scheme = urlparse(self.url)[0]

        if self.save_images and not scheme.startswith("http"):
            self.abort("Can only save images from http sites")

        self.parser = Parser(self.include_names, self.exclude_names)

    def gather_urls(self):

        urls = []

        if self.save_body:
            urls.append(self.url)

        if self.save_images:
            urls.extend(self.parser.get_images(self.url))

        self.log.debug("Checking these URLs:")
        for url in urls:
            self.log.debug("  %s" % url)

        return urls

    def get_headers(self, url):

        self.log.debug("  getting headers from %s" % url)

        headers = urllib.urlopen(url).info().headers

        keepers = []

        for header in headers:

            key = header.split(":")[0].strip()

            if key not in self.exclude_headers:
                self.log.debug("    including %s" % header.strip())
                keepers.append(header)
            else:
                self.log.debug("    excluding %s" % header.strip())

        return "".join(keepers)

    def headers_changed(self, urls):

        self.log.debug("Checking headers")

        try:
            prevChecksum = open("checksum.headers").read()
        except:
            prevChecksum = 0

        checksum = md5()

        for url in urls:
            checksum.update(self.get_headers(url))

        checksum = checksum.hexdigest()

        self.log.debug("  prev checksum: %s" % prevChecksum)
        self.log.debug("  new  checksum: %s" % checksum)

        if checksum != prevChecksum:
            self.log.debug("  header change detected")
            open("checksum.headers", "w").write(checksum)
            return 1
        else:
            return 0

    def files_changed(self, checksum):

        self.log.debug("Checking file checksum")

        try:
            prevChecksum = open("checksum.files").read()
        except:
            prevChecksum = 0

        self.log.debug("  prev checksum: %s" % prevChecksum)
        self.log.debug("  new  checksum: %s" % checksum)

        if checksum != prevChecksum:
            self.log.debug("  new files detected")
            open("checksum.files", "w").write(checksum)
            return 1
        else:
            self.log.debug("  files are the same")
            return 0

    def remap(self, filename):

        for pattern, result in self.rename_rules:
            if fnmatch.fnmatch(filename, pattern):
                return self.now().strftime(result)

        return filename

    def retrieve_files(self, urls):

        filenames = []
        unknownext = 0
        checksum = md5()

        self.log.debug("Retrieving files:")

        for url in urls:

            path = urlparse.urlparse(url)[2]
            filename = os.path.basename(path)
            if not filename:
                filename = "unknown.%d" % unknownext
                unknownext = unknownext + 1

            filename = self.remap(filename)

            try:
                contents = urllib.urlopen(url).read()
                checksum.update(contents)
                open(filename, "w").write(contents)
                filenames.append(filename)
                self.log.debug("  %s -> %s" % (url, filename))
            except:
                self.log.error("Problem retrieving %s" % url)
                self.log.exception("Traceback:")

        return filenames, checksum.hexdigest()

    def make_thumbnails(self, filenames):

        self.log.debug("Making thumbnails")

        thumbnails = []

        for filename in filenames:
            root, ext = os.path.splitext(filename)
            if ext in self.thumbnail_exts:
                self.log.debug("  creating thumbnail for %s" % filename)
                outputname = self.thumbnail_name % root
                cmd = "%s %s %s" % (self.thumbnail_cmd, filename, outputname)
                status, output = subprocess.getstatusoutput(cmd)

                if status == 0:
                    thumbnails.append(outputname)
                else:
                    self.log.error("Problem running thumbnail command: %s" % cmd)
                    self.log.error("Output: %s" % output)

        return thumbnails

    def main(self):

        self.wait(self.pollrate)

        while self.is_running():

            try:
                urls = self.gather_urls()
            except:
                self.log.exception("Problem gathering URLs")
                self.wait(self.retryrate)
                continue

            if not urls:
                self.log.debug("No urls to check")
                self.wait(self.pollrate)
                continue

            try:
                if self.check_headers and not self.headers_changed(urls):
                    self.log.debug("The headers have not changed")
                    self.wait(self.pollrate)
                    continue
            except:
                self.log.exception("Problem checking headers")
                self.wait(self.retryrate)
                continue

            filenames, checksum = self.retrieve_files(urls)

            if self.files_changed(checksum):
                if self.save_thumbnails:
                    try:
                        filenames.extend(self.make_thumbnails(filenames))
                    except:
                        self.log.exception("Problem making thumbnails")

                if filenames:
                    try:
                        self.news_poster.post(filenames)
                        self.log.info("New files detected, posting %s", filenames)
                    except:
                        self.log.exception("Error posting to the news server")
                else:
                    self.log.info(
                        "Strange, filenames detected, but none listed for posting..."
                    )

            remove_file(filenames)

            self.wait(self.pollrate)


def main():
    WatchURL(sys.argv).run()
