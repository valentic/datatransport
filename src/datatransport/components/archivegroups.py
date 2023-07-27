#!/usr/bin/env python3
"""ArchiveGroups Component"""

# pylint: disable=bare-except

##############################################################################
#
#  ArchiveGroups
#
#  Archives messages held in multiple newsgroups.
#
#  History:
#
#   1.0.0   2000-11-03  TAV
#           Initial implementation
#
#   1.0.1   2000-11-16  TAV
#           Use fnmatch instead of regular-expression matching.
#
#   1.0.2   2000-08-07  TAV
#           Code cleanup.
#           Added better error checking and message printing.
#           Try to use builtin functions when possible (limit os.system())
#
#   1.0.3   2001-09-05  TAV
#           Made groupExp (config file's pollgroups) a list of group
#               expressions. The old config files are still compatible,
#               but you can now list multiple patterns to watch for.
#
#           Added more comple <group> pattern replacement. You can now
#               give a list slice expression to pick out parts of the
#               group name. For example, if the group is transport.test.data
#               then the patter <group[1]> would return "test". A typical
#               usage is to extract the last part of the group name:
#               <group[-1]> returns "data". This feature is implemented by
#               splitting the group name up at the "." boundries and
#               evaluting the following list with the pattern.
#
#           Modified the <group> pattern to have <procgroup..> and
#               <newsgroup..>.
#
#           Switch to mx.DataTime to avoid localtime issues.
#           Added maxMessage check to limit number of files that are
#               concatenated (settng to 1 is equivalent to no concatenation
#               and a max of 0 means no limit).
#
#   1.0.4   2001-09-09  TAV
#           Created PatternTemplate class to extract pattern replacement
#               logic.
#
#           Added ability to enable report posting based on different types
#               of events (max messages, time out, time gap).
#
#   1.0.5   2001-09-13  TAV
#           Added matching rule feature.
#
#   2.0.0   2001-10-03  TAV
#           Complete rewrite of the script. It now handles the duties of a
#               number of other scripts dealing with the storing of messages
#               from the newsserver. It handles concatenated record storage
#               as well as file history and expiration. Notification messages
#               can be send on different events to a newsgroup to inform
#               others when data is ready or a newsgroup has stopped sending
#               data.
#
#   2.2.0   2001-10-17  TAV
#           Another major rewrite. I think I've got it down now. Correctly
#               handles archiving multi-part messages. Simplified things
#               considerably.
#
#   2.2.1   2001-11-06  TAV
#           Fixed a syntax error calling touch_message().
#
#   2.2.2   2001-11-08  TAV
#           Fixed an error in roll_files(). The last file was being removed
#               even if history was set to be 0 (which made the behavior
#               the same as history=1).
#
#   2.2.3   2001-11-09  TAV
#           Renamed NewsTool -> NewsTool
#
#   2.2.4   2001-11-13  TAV
#           Instrumented save_file() routine to better tell what happens it
#               fails.
#
#   2.2.5   2001-11-28  TAV
#           Modified the article processing routine to correctly handle
#               messages that are not in a multipart MIME format (ie plain
#               text messages). These are stored into a file named "noname"
#               and then processed as usual.
#
#   2.2.6   2001-11-29  TAV
#           Improved date handling. Originally, it was assumed that messages
#               had the data encoded in the Subject line (in the manner the
#               NewsTool.py employs). However, this is not always the case.
#               We used to just bail if we couldn't get the date. Now, a
#               set of dates are checked:
#                   - Subject line
#                   - NNTP-Posting-Date
#                   - Date
#                   - If those fail, use current time()
#
#   2.2.7   2001-11-30  TAV
#           Made the file name for plain text (see comments in 2.2.5) to be
#               a config parameter and set the default to noname.txt.
#
#   2.2.8   2001-12-04  TAV
#           Changed report.enable* defaults to off.
#           Fixed problem that kept the message number from being incremented
#               when no files were present in the message.
#
#   2.2.9   2001-12-10  TAV
#           Added ability to uncompress files during save if they were
#               compressed witg gzip and have a ".gz" extension. This
#               feature can be enabled/disabled with the output.uncompress
#               config option and defaults to disabled. In the future I'd
#               like to expand this to include .zip and tarballs as well.
#           Fixed date problem in filenames.
#
#   2.2.10  2001-12-26  TAV
#           Changed tav -> sri
#
#   2.2.11  2002-12-14  TAV
#           Added summary report generation. This addition requires new
#               checkpoint databases because the format changed.
#
#   2.2.12  2001-12-15  TAV
#           Fixed bug in default rules specification. The output name
#               should be the filename: (*,*,*) -> (*,*,<filename>)
#
#   2.2.13  2002-01-22  TAV
#           No longer try to set the group id when making files or dirs.
#               This is better handled using the user private group scheme
#               and saves headaches here. No longer need makePath().
#
#   2.2.14  2002-01-23  TAV
#           Added ability to disable the summary file tracking and limit
#               the maximum number of files being kept. If the summaries
#               are not being used, the file log was never cleared and
#               the database quickly grew to an enormous size, leading to
#               the crash of ArchiveGroups.
#
#           Started to add traceback printing to log on errors.
#           Signal handling now done in ProcessClient.
#
#   2.2.15  2002-02-19  Todd Valentic
#           Fixed bugs in calls to checkpoint.touch_message()
#
#   2.2.16  2002-08-028 Todd Valentic
#           sri.transport -> Transport
#           Fixed problem with timegap being reported after timeout.
#           Made separate report and summary news posters.
#           Track files in report mode if timeout or timegap is enabled.
#
#   2.2.17  2002-10-08  Todd Valentic
#           Set umask to 0 before creating path. The mode wasn't being
#               set properly otherwise.
#
#   2.2.18  2002-10-13  Todd Valentic
#           Added save_callback feature.
#
#   2.2.19  2003-03-20  Todd Valentic
#           Added ability to add an offset to message dates. Use this when
#               you need to "adjust" the date. For example, the timestamps
#               might be in UTC, but you want the files stamed in local time.
#               new time = message time + offset
#
#   2.2.20  2003-04-10  Todd Valentic
#           NewsToolBase -> NewsTool
#
#   2.2.21  2003-06-06  Todd Valentic
#           Added try..except around group check. We were dying if the
#               news server refused new connections (happens during high
#               load situations like updatedb).
#
#   2.2.22  2003-06-11  Todd Valentic
#           Added callback feature. This lets you modify the file and/or
#               filename prior to archive. This also involved changes
#               the order in which files are saved: all of the files
#               in a messages are now first uncompressed, then processed
#               then saved.
#           The check for compression was looking for gzip - right now
#               only bzip is supported.
#           Use the new NewsTool.SaveFiles() method to replace mimemsg.
#           Use NewsTool.messageDate() for timestamp.
#           Use string methods versus module.
#
#   2.2.23  2003-07-01  Todd Valentic
#           Fixed problem with initial history roll list.
#           Added support for .zip, .gz compression (in addition to .bz2)
#           Added check if source and output filenames are same (do nothing)
#
#   2.2.24  2003-08-14  Todd Valentic
#           createCallback -> getCallback
#
#   2.2.25  2003-08-21  Todd Valentic
#           Make sure to close files before calling the callback.
#
#   2.1.26  2003-08-23  Todd Valentic
#           Added option (output.overwrite) to control whether the output
#               file is overwritten if it already exists. Defaults to true.
#           Use get_timedelta for timeout and pollrate.
#
#   2.1.27  2003-10-03  Todd Valentic
#           Use get_timedelta for input.timeout and input.timegap
#
#   2.1.28  2004-03-04  Todd Valentic
#           Added timespan feature. We can now start a new file based
#               a span of time (ie daily) when concatenating messages.
#               It works in a manner similar to timegap and timeout.
#
#   2.1.29  2004-04-08  Todd Valentic
#           Add wait_on_start option (defaults on) to pause on startup
#               (prevents a lot of thrashing the news server when all
#               the processes are starting), but for long waits, it can
#               be annoying for debugging.
#
#           Added start_current_reset (defaults on) to prevent reseting
#               the start_current counter, allowing you to "catchup"
#               each time the news server is queried. Therefore, you
#               can now do something like wake up each hour and just
#               process the last message to give you an hourly sample.
#
#   2.1.30  2004-08-17  Todd Valentic
#           Change to new logging interface.
#
#   2.1.31  2004-12-27  Todd Valentic
#           Convert from mx.DateTime to datetime
#
#   2.1.32  2005-01-10  Todd Valentic
#           Make sure all times are UTC. There were places we were
#               comparing local times (which is usually UTC on the
#               servers anyways) with message headers. The new
#               datetime object is smart enough to know when you are
#               trying to compare an object with a timezone and one
#               without. Note that calling utcnow() returns the time
#               in UTC, but does not set the timezone. Use now(utc)
#               instead.
#
#           Made the report and summary enables default to the enable
#               state of the newsposter object.
#
#   2.1.33  2005-03-23  Todd Valentic
#           Fixed bug checking time.
#
#   2.1.34  2005-06-15  Todd Valentic
#           Added message headers in pattern replacement on filenames.
#
#   2.1.35  2005-08-12  Todd Valentic
#           Modified timespan to work with max_messages. By setting
#               both, we can control how many messages go into each
#               span. This can be used to do things like saving a
#               single webcam image taken once a minute every hour.
#
#   2.1.36  2005-08-13  Todd Valentic
#           Use parser for interpreting start/stop times.
#
#   2.1.37  2005-09-19  Todd Valentic
#           Added hack to save message time for callbacks. Need to
#               come up with a better method at some point.
#
#   2.1.38  2006-07-18  Todd Valentic
#           Added save_handler to allow for other saving options
#               besides copy/append (i.e., save to HDF).
#           Improve exit on error handling
#
#   2.1.39  2006-09-30  Todd Valentic
#           Fixed bug in timegap reporting. Don't reset checkpoint
#               if timegap and max_messages set.
#
#   2.1.40  2007-07-18  Todd Valentic
#           Added modify_message() call in process_message to allow
#               inherited classes to manipulate the message before
#               processing. One common use is for injecting new
#               headers (ie message times).
#
#   2.1.41  2008-05-13  Todd Valentic
#           Added parts offset
#
#   2.1.42  2008-07-19  Todd Valentic
#           Rewrote the split message processing to make rejoins more
#               robust. No longer need the parts offset added in
#               2.1.41. Removing.
#           Post errors to trouble newsgroup.
#           Make sure that keep_summary is initialized in Checkpoint.
#
#   2.1.43  2008-11-133 Todd Valentic
#           Add get_file_time() method to allow the output filename
#               computation to be based on the a timestamp relevant
#               to the file (instead of the message). The use case is
#               for messages with multiple attached files, like we
#               have in the RUDICS transport.
#
#   2.1.44  2009-02-04  Todd Valentic
#           Add newsgroup as parameter to get_file_time()
#           Print traceback if problem parsing output.rules()
#
#   2.1.45  2009-05-11  Todd Valentic
#           md5 module deprecated in Python 2.6. Use a import check
#               to pull in right library on older systems.
#
#   2.1.26  2009-09-24  Todd Valentic
#           Encounterd problem with strftime and very long (127+)
#               format strings. These are common in deep directory
#               heirarchies. Temp fix is to move it after the other
#               expansions, but that is only of limited help. Need
#               to find a work around...
#
#           Only update checkpoint message count on good files (it was
#               accounting for partial files when they are split over
#               multiple messages.
#
#   2.1.27  2010-05-07  Todd Valentic
#           Reset message count if low_mark > currentMessage. This
#               state can happen if the newsgroup is moved to a new
#               server and the counts are reset.
#
#   2.1.28  2012-02-28  Todd Valentic
#           Add file check before trying to set permissions (allows
#               for destname=/dev/null or alternate save_handlers
#               that don't actually save a file).
#
#   2.1.19  2012-11-13  Todd Valentic
#           Check for existance of database in __del__()
#
#   2.1.20  2013-01-27  Todd Valentic
#           Fix typo in __del__ for database check. Change to try..except
#
#   2.1.21  2013-05-24  Todd Valentic
#           Add newsgroup name into working directory for chunked messages
#
#   2.1.22  2018-04-16  Todd Valentic
#           Add validate_file
#
#   2.1.23  2021-07-23  Todd Valentic
#           Add ability to specify news server port (Default 119)
#
#   2016-12-23  Todd Valentic
#               Remove python<2.7 md5 import
# 		        Use datetime.timezone.utc for utc
#               No longer using dateutil.parser
#               Add main()
#
#   2022-10-07  Todd Valentic
#               Updates for Python3
#                   commands -> subprocess
#                   removeFile -> remove_file
#                   sizeDesc -> size_desc
#                   getInt -> get_int
#                   getDeltaTime -> get_timedelta
#                   getboolean -> get_boolean
#                   NewsPoster
#
#   2023-07-26  Todd Valentic
#               Updated for transport3 / python3
#
##############################################################################

import email
import fnmatch
import glob
import math
import os
import shelve
import shutil
import stat
import sys
import subprocess
import traceback

from datetime import datetime, timezone
from hashlib import md5
from pathlib import Path

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport import newstool

from datatransport.utilities import size_desc
from datatransport.utilities import remove_file
from datatransport.utilities import PatternTemplate
from datatransport.utilities import datefunc
from datatransport.utilities import make_path


def now():
    """Return current time"""
    return datetime.now(timezone.utc)


class Checkpoint:
    """Track newsgroup state"""

    def __init__(self, newsgroup, low_mark, max_history, keep_summary):
        self.newsgroup = newsgroup
        self.last_message = low_mark - 1

        self.keep_summary = keep_summary
        self.summary_max_files = 1000
        self.reset_summary()

        self.num_messages = 0
        self.num_bytes = 0
        self.filenames = {}

        self.last_time = now()
        self.start_time = now()
        self.poll_time = now()

        self.history = []
        self.max_history = max_history

    def update_message(self, msg_num, date=None):
        """Update current state"""

        self.num_messages = self.num_messages + 1
        self.last_message = msg_num
        self.poll_time = now()

        if date:
            self.last_time = date

    def touch_message(self, msg_num):
        """Mark message time"""

        self.last_message = msg_num
        self.poll_time = now()

    def update_file(self, filename, numbytes):
        """Update file stats"""

        if filename in self.filenames:
            (prev_msgs, prev_bytes) = self.filenames[filename]
        else:
            prev_msgs = 0
            prev_bytes = 0

        self.filenames[filename] = (prev_msgs + 1, prev_bytes + numbytes)
        self.num_bytes = self.num_bytes + numbytes

    def reset(self, date=None, last_message=0):
        """Reset state"""

        if not date:
            date = now()

        if self.filenames:
            self.history.insert(0, (self.filenames, self.last_time))
            self.history = self.history[0 : self.max_history + 1]

            if self.keep_summary:
                self.summary_files.append(self.filenames)
                self.summary_files = self.summary_files[-self.summary_max_files :]
                self.summary_bytes = self.summary_bytes + self.num_bytes
                self.summary_msgs = self.summary_msgs + self.num_messages

        self.start_time = date
        self.last_time = date
        self.num_messages = 0
        self.num_bytes = 0
        self.filenames = {}
        self.last_message = last_message

    def is_active(self):
        """Is newsgroup active"""

        return self.num_messages > 0

    def in_span(self, curtime, timespan):
        """Check if time in span"""

        lastsecs = self.last_time.timestamp()
        cursecs = curtime.timestamp()
        interval = timespan.total_seconds()

        lastblock = int(math.floor(lastsecs / interval))
        curblock = int(math.floor(cursecs / interval))

        return lastblock == curblock

    def reset_summary(self):
        """Reset summary counts"""

        self.summary_files = []
        self.summary_start = now()
        self.summary_bytes = 0
        self.summary_msgs = 0

    def get_report(self, title, reason):
        """Generate report"""

        message = []

        fmt = "%c %Z %z"

        message.append("_" * 75)
        message.append(title)
        message.append("")
        message.append(f"    Newsgroup     : {self.newsgroup}")
        message.append(f"    Beginning     : {self.start_time.strftime(fmt)}")
        message.append(f"    Ending        : {self.last_time.strftime(fmt)}")
        message.append(f"    Messages      : {self.num_messages}")
        message.append(f"    Total bytes   : {size_desc(self.num_bytes)}")
        message.append(f"    Reason        : {reason}")
        message.append("")

        if self.filenames:
            message.append("    Filenames")
            message.append("    ---------")

            for filename in sorted(self.filenames):
                msgs, numbytes = self.filenames[filename]
                if msgs > 1:
                    units = "msgs"
                else:
                    units = "msg"
                message.append(
                    f"    {filename}: {size_desc(numbytes)} ({msgs} {units})"
                )

        message.append("_" * 75)
        message = "\n".join(message)

        return message

    def get_summary(self, title):
        """Get summary report"""

        message = []

        fmt = "%c %Z %z"

        message.append("_" * 75)
        message.append(title)
        message.append("")
        message.append(f"    Newsgroup     : {self.newsgroup}")
        message.append(f"    Beginning     : {self.summary_start.strftime(fmt)}")
        message.append(f"    Ending        : {now().strftime(fmt)}")
        message.append(f"    Messages      : {self.summary_msgs}")
        message.append(f"    Total bytes   : {size_desc(self.summary_bytes)}")
        message.append("")

        if self.summary_files:
            message.append("    Filenames")
            message.append("    ---------")

            for filegroup in self.summary_files:
                prefix = "-"
                for filename in sorted(filegroup):
                    msgs, numbytes = filegroup[filename]
                    if msgs > 1:
                        units = "msgs"
                    else:
                        units = "msg"
                    message.append(
                        f"  {prefix} {filename}: {size_desc(numbytes)} ({msgs} {units})"
                    )
                    prefix = " "

        message.append("_" * 75)
        message = "\n".join(message)

        return message


class ArchiveGroups(ProcessClient):
    """Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.report_poster = NewsPoster(self, prefix="report", quiet=True)
        self.summary_poster = NewsPoster(self, prefix="summary", quiet=True)
        self.trouble_poster = NewsPoster(self, prefix="trouble", quiet=True)

        self.time_fmt = "%Y %j %H:%M:%S"

        self.replace_proc_group = PatternTemplate("procgroup", "/")
        self.replace_client_name = PatternTemplate("clientname", "/")
        self.replace_newsgroup = PatternTemplate("newsgroup", ".")
        self.replace_filename = PatternTemplate("filename", ".")
        self.replace_rule = PatternTemplate("rule")
        self.replace_history = PatternTemplate("history")
        self.replace_header = PatternTemplate("header")

        self.time_offset = self.config.get_timedelta("timeoffset", 0)
        self.pollrate = self.config.get_rate("input.pollrate", 60)
        self.wait_on_start = self.config.get_boolean("input.wait_on_start", True)

        self.pollserver_host = self.config.get("input.server", "localhost")
        self.pollserver_port = self.config.get_int("input.server.port", 119)
        self.timeout = self.config.get_timedelta("input.timeout", None)
        self.timegap = self.config.get_timedelta("input.timegap", None)
        self.timespan = self.config.get_timedelta("input.timespan", None)
        self.start_time = self.config.get("input.start_time", None)
        self.stop_time = self.config.get("input.stop_time", None)
        self.start_current = self.config.get_int("input.start_current", 1)
        self.start_current_reset = self.config.get_boolean(
            "input.start_current.reset", True
        )

        self.dest_path = self.config.get("output.path", "")
        self.dest_name = self.config.get("output.name", "<rule>")
        self.dest_file_mode = self.config.get_int("output.mode.file", "0o644")
        self.dest_path_mode = self.config.get_int("output.mode.path", "0o755")
        self.max_messages = self.config.get_int("output.max_messages", 1)
        self.expire = self.config.get_timedelta("output.expire", None)
        self.history = self.config.get_int("output.history", 0)
        self.plain_text_name = self.config.get("output.plain_text_name", "noname.txt")
        self.uncompress = self.config.get_boolean("output.uncompress", False)
        self.overwrite = self.config.get_boolean("output.overwrite", True)

        self.report_subject = self.config.get(
            "report.subject", "Newsgroup archive report"
        )
        self.report_title = self.config.get("report.title", "Newsgroup archive report")

        enable = self.report_poster.enabled
        self.report_max_messages = self.config.get_boolean(
            "report.enable.max_messages", enable
        )
        self.report_timeout = self.config.get_boolean("report.enable.timeout", enable)
        self.report_timegap = self.config.get_boolean("report.enable.timegap", enable)
        self.report_timespan = self.config.get_boolean("report.enable.timespan", enable)

        self.summary_subject = self.config.get(
            "summary.subject", "Newsgroup summary report"
        )
        self.summary_title = self.config.get(
            "summary.title", "Newsgroup summary report"
        )
        self.summary_enable = self.config.get_boolean(
            "summary.enable", self.summary_poster.enabled
        )
        self.summary_period = self.config.get_timedelta("summary.period", 60 * 60 * 24)
        self.summary_offset = self.config.get_timedelta("summary.offset", 0)
        self.summary_max_files = self.config.get_int("summary.max_files", 1000)

        self.debug = self.config.get_boolean("debug", False)

        self.include_newsgroups = self.config.get_list("input.newsgroups")
        self.exclude_newsgroups = self.config.get_list("input.newsgroups.exclude")
        self.include_filenames = self.config.get_list("input.filenames", "*")
        self.exclude_filenames = self.config.get_list("input.filenames.exclude")

        try:
            self.callback = self.config.get_callback("callback")
        except:
            self.log.exception("Problem loading callback")
            self.abort()

        try:
            self.rules = eval(
                self.config.get("output.rules", "[('*','*','<filename>')]")
            )
        except:
            self.log.exception("There was a problem parsing output.rules.")
            self.abort()

        self.validate_setup()
        self.setup_database()

    def __del__(self):
        try:
            self.database.close()
        except:
            pass

    def setup_database(self):
        """Setup checkpoint database"""

        self.database = shelve.open("checkpoint.db")

        # Update the config parameters in the database to new values.

        for key, checkpoint in self.database.items():
            checkpoint.max_history = self.history
            checkpoint.keep_summary = self.summary_enable
            checkpoint.summary_max_files = self.summary_max_files
            self.database[key] = checkpoint

        # Make sure that the on-disk files are initialized, otherwise they will
        # be zero-length and cause problems next time if opened that way.

        self.database.sync()

    def validate_setup(self):
        """Validate setup"""

        if self.start_time:
            try:
                self.start_time = datefunc.strptime(
                    self.start_time, self.time_fmt, timezone.utc
                )
                self.log.info("Only processing messages past %s", self.start_time)
            except:
                self.log.exception(
                    "The start time format is bad. It should be YYYY JJJ HH:MM:SS"
                )
                self.abort("Exiting")

        if self.stop_time:
            try:
                self.stop_time = datefunc.strptime(
                    self.stop_time, self.time_fmt, timezone.utc
                )
                self.log.info("Only processing messages before  %s", self.stop_time)
            except:
                self.log.exception(
                    "The stop time format is bad. It should be YYYY JJJ HH:MM:SS"
                )
                self.abort("Exiting")

        self.log.debug("Watching these newsgroups (+ = include, - = exclude):")
        for newsgroup in self.include_newsgroups:
            self.log.debug("  + %s", newsgroup)
        for newsgroup in self.exclude_newsgroups:
            self.log.debug("  - %s", newsgroup)

        self.log.debug("Watching these filenames (+ = include, - = exclude):")
        for filename in self.include_filenames:
            self.log.debug("  + %s", filename)
        for filename in self.exclude_filenames:
            self.log.debug("  - %s", filename)

    def get_groups(self, newsserver):
        """Get newsgroup list"""

        groups = []

        _response, newsgroup_list = newsserver.list()

        for newsgroup, high_mark, low_mark, _flag in newsgroup_list:
            high_mark = int(high_mark)
            low_mark = int(low_mark)

            for incgroup in self.include_newsgroups:
                if fnmatch.fnmatch(newsgroup, incgroup):
                    keep = 1
                    for excgroup in self.exclude_newsgroups:
                        if fnmatch.fnmatch(newsgroup, excgroup):
                            keep = 0
                            break
                    if keep:
                        groups.append((newsgroup, low_mark, high_mark))
                        if not newsgroup in self.database:
                            checkpoint = Checkpoint(
                                newsgroup, low_mark, self.history, self.summary_enable
                            )
                            self.database[newsgroup] = checkpoint
                            self.database.sync()

        return groups

    def filter_filenames(self, filenames):
        """Filter filenames"""

        goodfiles = []

        for filename in filenames:
            for incpattern in self.include_filenames:
                if fnmatch.fnmatch(filename, incpattern):
                    keep = 1
                    for excpattern in self.exclude_filenames:
                        if fnmatch.fnmatch(filename, excpattern):
                            keep = 0
                            break
                    if keep:
                        goodfiles.append(filename)

        return goodfiles

    def get_file_time(self, _newsgroup, _filename):
        """Get timestamp from filename"""
        return None

    def compute_name(self, filename, checkpoint):
        """Compute filename"""

        rule = self.find_rule(checkpoint.newsgroup, filename)

        path = os.path.join(self.dest_path, self.dest_name)
        path = self.replace_rule(path, rule)

        try:
            filetime = self.config.get_file_time(checkpoint.newsgroup, filename)
        except:
            filetime = None

        if filetime is None:
            if self.max_messages == 1:
                filetime = checkpoint.last_time
            else:
                filetime = checkpoint.start_time

        # NOTE - Potential breakage with long paths and versions
        #        of python < 2.4.4 where strftime is limited to
        #        127 character strings. Moving it to the end
        #        of the expansion here, helped, but I need to
        #        figure out a better way of doing this...

        path = self.replace_newsgroup(path, checkpoint.newsgroup)
        path = self.replace_proc_group(path, self.groupname)
        path = self.replace_client_name(path, self.name)
        path = self.replace_filename(path, str(filename))
        path = self.replace_header(path)
        path = filetime.strftime(path)

        return path

    def find_rule(self, newsgroup, filename):
        """Find matching rule"""

        for rule in self.rules:
            if fnmatch.fnmatch(newsgroup, rule[0]) and fnmatch.fnmatch(
                filename, rule[1]
            ):
                return rule[2]

        return ""

    def post_report(self, checkpoint, reason):
        """Post report"""

        title = self.report_title
        title = self.replace_newsgroup(title, checkpoint.newsgroup)
        title = self.replace_proc_group(title, self.groupname)
        title = self.replace_client_name(title, self.name)

        header = self.report_subject
        header = self.replace_newsgroup(header, checkpoint.newsgroup)
        header = self.replace_proc_group(header, self.groupname)
        header = self.replace_client_name(header, self.name)

        message = checkpoint.get_report(title, reason)

        try:
            self.report_poster.set_subject(header)
            self.report_poster.post_text(message)
            self.log.info("%s, posting report (%s)", reason, checkpoint.newsgroup)
        except:
            self.log.exception("Error posting report message")

    def post_summary(self, checkpoint):
        """Post summary report"""

        title = self.summary_title
        title = self.replace_newsgroup(title, checkpoint.newsgroup)
        title = self.replace_proc_group(title, self.groupname)
        title = self.replace_client_name(title, self.name)

        header = self.summary_subject
        header = self.replace_newsgroup(header, checkpoint.newsgroup)
        header = self.replace_proc_group(header, self.groupname)
        header = self.replace_client_name(header, self.name)

        message = checkpoint.get_summary(title)

        try:
            self.summary_poster.set_subject(header)
            self.summary_poster.post_text(message)
            self.log.info("Posting summary report (%s)", checkpoint.newsgroup)
        except:
            self.log.error("Error posting summary message")

    def roll_files(self, checkpoint):
        """Only keep N files"""

        self.log.debug("Rolling file history:")
        self.log.debug("  history length: %d", len(checkpoint.history))
        self.log.debug("  max history: %d", checkpoint.max_history)

        if not checkpoint.history or checkpoint.max_history == 0:
            self.log.debug("  no files to roll")
            return

        history_index = list(range(len(checkpoint.history)))
        history_index.reverse()

        for index in history_index:
            filenames = checkpoint.history[index][0].keys()

            for filename in filenames:
                oldname = self.replace_history(filename, index)
                newname = self.replace_history(filename, index + 1)

                try:
                    if index < checkpoint.max_history:
                        if oldname == newname:
                            self.log.debug("  keeping  %s", oldname)
                        else:
                            os.rename(oldname, newname)
                            self.log.debug("  copying  %s -> %s", oldname, newname)
                    else:
                        os.remove(oldname)
                        self.log.debug("  removing %s", oldname)
                except:
                    pass

    def save_callback(self, filename):
        """Save callback"""

        # Used by derived classes to do something interesting with
        # the newly saved file such as creating a thumbnail of images.

    def save_handler(self, srcname, destname, mode):
        """Save handler"""

        srcfile = open(srcname, "rb")
        destfile = open(destname, mode)
        shutil.copyfileobj(srcfile, destfile)
        srcfile.close()
        destfile.close()
        os.chmod(destname, self.dest_file_mode)

    def save_file(self, srcname, checkpoint):
        """Save single file"""

        num_bytes = os.stat(srcname)[stat.ST_SIZE]
        name = self.compute_name(srcname, checkpoint)
        destname = self.replace_history(name, str(0))
        destname = os.path.abspath(destname)

        self.log.debug("Saving %s", srcname)
        self.log.debug("  dest: %s", destname)
        self.log.debug("  maxmessages: %d", self.max_messages)
        self.log.debug("  nummessages: %d", checkpoint.num_messages)
        self.log.debug("  is_active: %s", checkpoint.is_active())

        if not self.overwrite and os.path.exists(destname):
            self.log.debug("  destination exists - not saving")
            return

        if self.max_messages != 1 and checkpoint.is_active():
            mode = "ab"
            self.log.info("Concat: %s -> %s", srcname, destname)
        else:
            mode = "wb"
            self.log.info("Start : %s -> %s", srcname, destname)

        try:
            make_path(destname, self.dest_path_mode)
        except BaseException as err:
            self.log.exception("Problem creating the path.")
            raise err

        try:
            if os.path.abspath(srcname) != destname:
                self.save_handler(srcname, destname, mode)

            if os.path.isfile(destname):
                os.chmod(destname, self.dest_file_mode)
        except:
            self.log.exception("Problem saving file")
            raise

        try:
            self.save_callback(destname)
        except:
            self.log.exception("Problem running the save callback")

        checkpoint.update_file(name, num_bytes)

    def uncompress_file(self, cmd, filename):
        """Uncompress file if needed"""

        uncompressname = filename.stem

        try:
            status, output = subprocess.getstatusoutput(f"{cmd} {filename}")
        except IOError:
            self.abort("Error running uncompression: %s", cmd)

        if status == 0:
            self.log.debug("  uncompressing: %s", filename)
        else:
            subject = "Archive: Error umcompressing file"
            note = []
            note.append("Error trying to uncompress file")
            note.append("   command: %s", cmd)
            note.append("   status:  %d", status)
            note.append("   output:  %s", output)
            self.post_error(subject, note)
            return None

        return Path(uncompressname)

    def last_tracback(self):
        """Format last traceback"""

        return traceback.format_tb(sys.exc_traceback)[-1]

    def post_error(self, subject, note):
        """Post error message"""

        for line in note:
            self.log.error(line)

        try:
            self.trouble_poster.set_subject(subject)
            self.trouble_poster.post_text("\n".join(note))
            self.log.info("Sent trouble message")
        except:
            self.log.exception("Failed to post trouble message")

    def validate_file(self, _filename):
        """Validate file"""
        return True

    def process_files(self, filenames, checkpoint, msg_num, msg_time):
        """Process files"""

        # Hack alert - the callbacks sometimes want access to
        # the message time.
        self.msg_time = msg_time

        # Roll old files

        if not checkpoint.is_active():
            self.roll_files(checkpoint)
            checkpoint.reset(msg_time, msg_num)

        # Uncompress any files that need it

        uncompressedfiles = []

        for filename in filenames:
            if self.uncompress:
                # if filename.suffix == ".zip":
                #    filename = self.uncompress_file("unzip -o", filename)
                if filename.suffix == ".gz":
                    filename = self.uncompress_file("gunzip -f", filename)
                elif filename.suffix == ".bz2":
                    filename = self.uncompress_file("bunzip2 -f", filename)

            if filename:
                uncompressedfiles.append(filename)

        # Run the callback function if needed

        savefiles = []

        for filename in uncompressedfiles:
            if not self.validate_file(filename):
                continue

            if self.callback:
                try:
                    filename = self.callback(self, filename)
                    # filename can now be the same name, a new name
                    # None if we should forget it, or a list if new
                    # files were created.
                except:
                    self.log.exception("Problem running callback:")
                    continue

            if not filename:
                # The callback doesn't want the file saved
                continue

            if isinstance(filename, (list, tuple)):
                savefiles.extend(filename)
            else:
                savefiles.append(filename)

        for filename in savefiles:
            try:
                self.save_file(filename, checkpoint)
            except:
                note = []
                note.append("Problem storing file:")
                note.append(f"  filename    = {filename}")
                note.append(f"  path        = {self.dest_path}")
                note.append(f"  message num = {msg_num}")
                note.append(f"  newsgroup   = {checkpoint.newsgroup}")
                note.append(f"  file mode   = {oct(self.dest_file_mode)}")
                note.append(f"  path mode   = {oct(self.dest_path_mode)}")
                note.append("")
                note.append(traceback.format_exc())

                subject = f"Archive: problem saving {filename}"

                self.post_error(subject, note)

                if self.debug:
                    self.log.error("Exiting on error (debug mode on)")
                    raise

                self.abort("Exiting on error")
                break

            remove_file(filename)

            if self.is_stopped():
                break

    def modify_message(self, message):
        """Modify message"""

        return message

    def process_message(self, newsserver, msg_num, checkpoint):
        """Process message"""

        try:
            article = newsserver.article(str(msg_num))[1]
            message = email.message_from_bytes(b"\n".join(article.lines))
        except:
            self.log.exception("    unable to retrieve article body")
            checkpoint.touch_message(msg_num)
            return

        message = self.modify_message(message)

        if not message:
            self.log.info("    skipping message")
            checkpoint.touch_message(msg_num)
            return

        msg_time = newstool.message_date(message) + self.time_offset

        headers = {}
        for key in message.keys():
            headers[key] = message[key]

        self.replace_header.set_value(headers)

        if self.start_time and msg_time < self.start_time:
            self.log.debug(
                "    rejecting - too old (%s)", msg_time.strftime(self.time_fmt)
            )
            checkpoint.reset(msg_time, msg_num)
            return

        if self.stop_time and msg_time > self.stop_time:
            self.log.debug(
                "    rejecting - too new (%s)", msg_time.strftime(self.time_fmt)
            )
            checkpoint.reset(msg_time, msg_num)
            return

        if self.timegap and (msg_time - checkpoint.last_time) >= self.timegap:
            self.log.info("    time gap between messages exceeds limit")
            if self.report_timegap and checkpoint.is_active():
                self.post_report(checkpoint, "Time gap")
            checkpoint.reset(msg_time, msg_num)

        if self.timespan:
            if checkpoint.in_span(msg_time, self.timespan):
                if self.max_messages and checkpoint.num_messages >= self.max_messages:
                    self.log.debug("    rejecting, max reached for this time span")
                    return

            else:
                self.log.info("    message is in a new time span")
                if self.report_timespan and checkpoint.is_active():
                    self.post_report(checkpoint, "Time span")
                checkpoint.reset(msg_time, msg_num)

        try:
            filenames = newstool.save_files(message)
        except:
            self.log.exception("    rejecting - unable to parse message body")
            checkpoint.touch_message(msg_num)
            return

        if "x-transport-part" in message:
            # Assumes that there is only one part attached

            part, total = map(int, message["X-Transport-Part"].split("/"))
            srcname = os.path.basename(filenames[0])
            destname = os.path.basename(message["X-Transport-Filename"])
            workdir = os.path.join("work", checkpoint.newsgroup, destname)
            workname = os.path.join(workdir, srcname)

            if not os.path.exists(workdir):
                os.makedirs(workdir)

            shutil.move(srcname, workname)

            parts = sorted(glob.glob(os.path.join(workdir, "*")))

            if len(parts) == total:
                with Path(destname).open("wb") as destfile:
                    for filepart in parts:
                        contents = Path(filepart).read_bytes()
                        destfile.write(contents)

                remove_file(parts)
                os.rmdir(workdir)

                self.log.debug("Joined split message: %d parts", total)

                if "x-transport-md5" in message:
                    orgmd5 = message["x-transport-md5"]
                    newmd5 = md5(Path(destname).read_bytes()).hexdigest()
                    if orgmd5 == newmd5:
                        self.log.debug("  MD5 checksum matches")
                        filenames = [destname]
                    else:
                        subject = "Archive: MD5 mismatch"

                        note = []
                        note.append("MD5 mistmatch in file")
                        note.append(f"  message ID: {message['Xref']}")
                        note.append(f"  filename:   {destname}")
                        note.append(f"  expected:   {orgmd5}")
                        note.append(f"  found:      {newmd5}")
                        self.post_error(subject, note)

                        filenames = []
                else:
                    self.log.debug("  No MD5 checksum to compare")
                    filenames = [destname]

            else:
                filenames = []
                self.log.debug("Joining split message: part %d of %d", part, total)

        goodfiles = self.filter_filenames(filenames)
        self.log.debug(
            "    message contains %d file(s), saving %d:",
            len(filenames),
            len(goodfiles),
        )
        for filename in filenames:
            if filename in goodfiles:
                self.log.debug("      + %s", filename)
            else:
                self.log.debug("      - %s", filename)

        if goodfiles:
            self.process_files(goodfiles, checkpoint, msg_num, msg_time)
            checkpoint.update_message(msg_num, msg_time)

        remove_file(filenames)

        self.log.debug(
            "    after writing files, message count=%d, max=%d",
            checkpoint.num_messages,
            self.max_messages,
        )

        if self.max_messages and checkpoint.num_messages >= self.max_messages:
            if self.max_messages > 1:
                self.log.info("    max message count reached")
            if self.report_max_messages:
                self.post_report(checkpoint, "Max message count reached")
            if not self.timespan and not self.timegap:
                checkpoint.reset(msg_time, msg_num)

    def process_group(self, newsserver, checkpoint, low_mark, high_mark):
        """Process newsgroup"""

        self.log.debug("Processing newsgroup: %s", checkpoint.newsgroup)
        self.log.debug(
            "  available message numbers: %d - %d, last processed: %d",
            low_mark,
            high_mark,
            checkpoint.last_message,
        )

        if self.start_current == 1:
            self.log.debug("  catching up")
            checkpoint.reset(last_message=high_mark)

        elif self.start_current < 0:
            last_msg = max(low_mark - 1, high_mark + self.start_current)
            last_msg = max(last_msg, checkpoint.last_message)
            self.log.debug(
                "  starting with last %d message(s)", abs(high_mark - last_msg)
            )
            checkpoint.reset(last_message=last_msg)

        elif low_mark > high_mark:
            self.log.debug("  no messages on server")
            return

        elif (
            checkpoint.last_message < low_mark - 1
            or checkpoint.last_message > high_mark
        ):
            self.log.info("  message count reset")
            checkpoint.reset(last_message=low_mark - 1)

        if checkpoint.last_message == high_mark:
            self.log.debug("  no new messages")

            if self.timeout and checkpoint.is_active():
                if (now() - checkpoint.poll_time) >= self.timeout:
                    self.log.info("  time out reached")
                    if self.report_timeout:
                        self.post_report(checkpoint, "Time out reached")
                    checkpoint.reset(last_message=high_mark)

                return

        newsserver.group(checkpoint.newsgroup)

        for msg_num in range(checkpoint.last_message + 1, high_mark + 1):
            self.log.debug("  processing message %d", msg_num)

            self.process_message(newsserver, msg_num, checkpoint)
            self.database[checkpoint.newsgroup] = checkpoint
            self.database.sync()

            if self.is_stopped():
                break

    def check_groups(self):
        """Check newsgroups"""

        host = self.pollserver_host
        port = self.pollserver_port

        with newstool.NewsTool().open_server(host, port) as newsserver:
            for newsgroup, low_mark, high_mark in self.get_groups(newsserver):
                checkpoint = self.database[newsgroup]
                self.process_group(newsserver, checkpoint, low_mark, high_mark)
                self.database[newsgroup] = checkpoint
                self.database.sync()

                if self.is_stopped():
                    break

        if self.start_current_reset:
            self.start_current = 0

    def expire_files(self):
        """Expire old files"""

        self.log.debug("Expiring old files")

        for key, checkpoint in self.database.items():
            self.log.debug("  - %s", key)

            if len(checkpoint.history) > 0:
                self.log.debug("    checking file history expire times:")

                history_index = list(range(len(checkpoint.history)))
                history_index.reverse()

                for index in history_index:
                    filenames, lastdate = checkpoint.history[index]

                    diff = now() - lastdate
                    expire = diff > self.expire

                    self.log.debug(
                        "      %d: time=%s, diff=%s, expire? %d",
                        index,
                        lastdate,
                        diff,
                        expire,
                    )

                    if expire:
                        for filename in filenames.keys():
                            filename = self.replace_history(filename, index)
                            self.log.debug("         %s", filename)
                            try:
                                os.remove(filename)
                            except:
                                pass
                        del checkpoint.history[index]
                    else:
                        break

            self.database[key] = checkpoint

        self.database.sync()

    def check_summary(self):
        """Check if time for summary report"""

        if not self.summary_enable:
            return

        self.log.debug("Checking summary reporting")

        for key, checkpoint in self.database.items():
            self.log.debug("  - %s", key)

            secs = checkpoint.summary_start.timestamp()
            interval = self.summary_period.total_seconds()
            offset = self.summary_offset.total_seconds()

            next_time = (math.floor(secs / interval) + 1) * interval + offset
            next_time = datetime.fromtimestamp(next_time, tz=timezone.utc)

            self.log.debug("    - interval = %s", self.summary_period)
            self.log.debug("    - offset   = %s", self.summary_offset)
            self.log.debug("    - start_time= %s", checkpoint.summary_start)
            self.log.debug("    - next_time = %s", next_time)

            if now() >= next_time:
                self.log.info("Summary time reached")
                self.post_summary(checkpoint)
                checkpoint.reset_summary()

            self.database[key] = checkpoint

        self.database.sync()

    def main(self):
        """Main application"""

        self.log.info("Starting")

        while self.wait(self.pollrate):
            try:
                self.check_groups()
            except SystemExit:
                self.log.info("TAV *** SYSTEM EXIT exception")
                break
            except:
                note = [traceback.format_exc()]
                self.post_error("Archive: problem checking groups", note)

            self.check_summary()

            if self.expire:
                self.expire_files()

        self.log.info("Finished")


def main():
    """Script entry point"""
    ArchiveGroups(sys.argv).run()
