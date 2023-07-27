#!/usr/bin/env python
"""News Tool"""

# pylint: disable=too-many-lines

###########################################################################
#
#   News Tool
#
#   A collection of classes to support pushing and pulling of data from
#   newsgroups using NNTP. The object heirarchy looks like this:
#
#       NewsTool
#          |
#          |---- NewsPoster
#          |         |
#          |          ---- NewsControl
#          |
#           ---- NewsPoller
#
#   Revision History:
#
#   1.0.0   1999-??-??  Todd Valentic
#           Initial version
#
#   1.0.1   1999-09-17  Todd Valentic
#           Fix bug in NewsPoller that prevented new messages from being
#               detected. The comparison of the message numbers was done
#               as strings, which failed in one particular case ("97">"258")
#               but seemed to work in other situations. I forced the
#               comparison to be done on ints. The index numbers should
#               really be stored as ints and not strings - to be cleaned up
#               in the future.
#
#   1.0.2   1999-12-03  Todd Valentic
#           Modified the NewsPoller callback's to include the header from
#               the extracted message (used primarily to extract the date
#               of posting without having to interpret the file contents.)
#           Cleaned up the polling loop syntax.
#
#   1.0.3   2000-01-20  Todd Valentic
#           Added try..except blocks around processing calls in NewsPoller
#           Added logging function instead of just going to stdout.
#           Added markRead function to NewsPoller.
#
#   1.0.4   2000-01-22  Todd Valentic
#           Added openServer() method the NewsToolBase for connections to
#           the NNTP server. The reason for this was to include a
#           "mode reader" command if necessary when connecting. If a machine
#           is defined as a feeder for a downstream server, it will not be
#           allowed reading access. The innd program adds the "mode" command
#           to allow a server to force reader access. Since all the commands
#           in this library are for readers, we go ahead and try to force
#           the access mode for the connection.
#
#   1.0.5   2000-01-26  Todd Valentic
#           Modifications to NewsPoller:
#               - Added ability to pass raw article to processing function
#               - Removed the processScript option
#               - Unpack the MIME message only if necessary
#               - Removed the 'body.txt' check
#               - Added debug flag to be used when debugging processing
#           Modifications to NewsPoster:
#               - Added ability to post a non-MIME text only body.
#
#   1.0.6   2000-01-31  Todd Valentic
#           Added single_shot setting to NewsPoller. This flag indicates that
#               only a single message should be processed even though more
#               then one may be available.
#
#   1.0.7   2000-02-15  Todd Valentic
#           Updates to NewsPoller:
#               - Split processing from polling loop to processArticle.
#                 This is to allow other methods process articles in a
#                 consistent manner.
#               - Added processPast() to process articles in a group
#                 prior to the current time. No checks are made to see
#                 if the articles had previously been processed nor is
#                 the lastreadfile updated.
#           Updates to NewsToolBase:
#               - Added time() to query the newsserver for it's
#                 current time and return it as a Unix time.
#               - Added optional name parameter to openServer to allow
#                 setting the server name at the same time.
#
#   1.0.8   2000-04-24  Todd Valentic
#           Updates to NewsPoller:
#               - Added Retry exception
#               - Moved processArticle guts to callProcessing
#               - processArticle now retries the processing if the
#                 exception is raised. It will continue doing this
#                 until the processing functions run without error.
#                 This should handle the cases when we are trying to send
#                 data to a client such as SPARC and we suffer network
#                 outages.
#               - Added enable functionality.
#
#   1.0.9   2000-04-29  Todd Valentic
#           Moved groupExsits() method to NewsToolBase from NewsControl.
#
#   1.0.10  2000-06-22  Todd Valentic
#           Added try..except blocks around the server.quit() calls.
#               It seems that we were having problems posting to SPARC
#               in the processing calls (leading to long timeouts). In the
#               mean time, the connection to the news server had been
#               dropped. The call then to server.quit raised an exception.
#               I'm not sure we actually need to do a quit() - it might
#               be better to have a persistent server object sitting
#               around that reopens a connection when needed.
#
#   1.0.11  2001-08-11  Todd Valentic
#           Added processText function to newsPoller to act like the
#                 other processing methods (func,raw). It separates the
#                 headers from the body.
#
#   1.0.12  2001-09-06  Todd Valentic
#           Changes set_newsgroup() to handle a list of group names as well
#                 as just an individual string to accommodate cross-posting.
#
#   1.0.13  2001-11-28  Todd Valentic
#           Chnaged header in postText to include data field like the
#                 normal post() method uses.
#
#   1.0.14  2002-01-24  Todd Valentic
#           Changed processFunc -> processFiles.
#
#   1.0.15  2002-04-11  Todd Valetic
#           Changed the body creation in NewsPoller processText() to
#                 join lines with a \n.
#
#   1.0.16  2002-08-25  Todd Valentic
#           Use readermode in NNTP() to set reader mode (see discussion
#                 in 1.0.4).
#
#   1.0.17  2002-10-10  Todd Valentic
#           Added check in callProcessing() for bad message id.
#
#   1.0.18  2003-02-12  Todd Valentic
#           Made catchup parameter more flexible for polling:
#                   catchup = 0: do nothing
#                   catchup = 1: mark all messages read
#                   catchup < 0: mark all messages except last count as read
#                                (but not if we have already seen them).
#
#   1.0.19  2003-04-10  Todd Valentic
#           Start using mx.DateTime module.
#           Cleaned up formatting of comments.
#           Removed setComment in NewsPoster - replaced with parameter to post
#           Time added to subject lines now in ARPA format.
#           Use string methods instead of string module.
#           There was a time that article numbers were missing the trailing
#             '>' when queried from INN. This doesn't seem to happen anymore.
#             Removing check code:
#               if article_number[-1]!='>':
#                 article_number=article_number+'>'
#           Added listArticles and listGroups methods
#           Removed setOutputName, setPrefix in NewsPoller (not used anymore)
#           Renamed NewsToolBase to NewsTool
#           Added stop() callback to NewsPoller to stop processing when
#               dealing with a large number of backlogged articles.
#           Added 'X-Transport-Date' header and parameters to postFiles() and
#               postText(). This allows a client to specify a date to later
#               be used for special purposes. For example, a client might set
#               date to match the time at which a data file is generated, not
#               the time at which the file is posted. An archiving program
#               can then use this date file to name the file correctly. This
#               used to be handled by coding the date in the Subject header.
#
#   1.0.20  2003-04-18  Todd Valentic
#           Fixed some bugs due in NewsControl object that were introduced
#               in code cleanup.
#
#   1.0.21  2003-06-10  Todd Valentic
#           Somewhere along the line, a bug was introduced where extra
#               characters were added to the end of unpacked files! This
#               was a problem with the old mimemsg interface. I replaced
#               it with the much simpler standard library email.
#
#   2.0.0   2003-06-30  Todd Valentic
#           Changed the signature for the callback functions. They now
#               provide an email.Message object as the first parameter
#               followed by the specific callback parameters (list of
#               filenames, etc). The subject line is no longer directly
#               supplied. It can easily be obtained from the message
#               headers.
#           Added the messageDate() function to the utility methods.
#           Renamed SaveFiles() -> saveFiles(). It now takes a Message.
#
#   2.0.1   2003-08-21  Todd Valentic
#           Fixed bug in processPast - didn't handle list of newsgroups
#               returned by listArticles properly.
#
#   2.0.2   2004-02-13  Todd Valentic
#           Pass user-defined headers along when posting.
#
#   2.0.3   2004-02-17  Todd Valentic
#           Record message time/size info when reading.
#
#   2.0.4   2004-02-26  Todd Valentic
#           Check if multipart in saveFiles. For non-MIME messages, save
#               the body insead.
#
#   2.0.5   2004-09-11  Todd Valentic
#           Added asConfig() utility method.
#
#   2.0.6   2004-12-27  Todd Valentic
#           Convert from mx.DateTime to datetime
#           Use dateutil.parser for date parsing
#           Change time() method to return server time in UTC
#           Change time method name to datetime
#
#   2.0.7   2005-01-10  Todd Valentic
#           Make sure all times are UTC.
#
#   2.0.8   2005-02-08  Todd Valentic
#           Fix default logging
#           Allow passing a single filename into post.
#           Add postFiles() to compliment other post* methods. This
#               is just an alias for post.
#
#   2.0.9   2005-03-08  Todd Valentic
#           Handle exception in callProcessing
#
#   2.0.10  2005-03-25  Todd Valentic
#           Added path prefix and creation to saveFiles
#
#   2.0.11  2005-04-04  Todd Valentic
#           Use get_content_* methods instead of deprectated verions.
#
#   2.0.12  2005-05-09  Todd Valentic
#           Reorganized poll() internals. Added getNextMessage() for
#               use by other routines (i.e. the SyncPoller component).
#           Added ability to set port when specifying server.
#           Added mark_message_read()
#
#   2.0.13  2005-06-13  Todd Valentic
#           Added set/add/clearExtraHeaders() to NewsPoster.
#           Added getArticle - fixed bug in processPast.
#
#   2.0.14  2005-07-29  Todd Valentic
#           Cleaned up listGroups to use fnmatch.filter.
#
#   2.0.15  2005-12-21  Todd Valentic
#           Catchup lastid if it is less then the first available
#               message id.
#           Fixed bug in Poller run() routine. Bad return value
#               in the case the server was unavailable. Found by
#               Andrew Young.
#
#   2.0.16  2006-02-03  Todd Valentic
#           Code cleanup. Removed deprecated verbose entries.
#
#   2.0.17  2006-02-07  Todd Valentic
#           Make sure that messageDate() has a timezone. Default
#               to UTC if not specified.
#
#   2.0.18  2006-07-18  Todd Valentic
#           Extra headers were not being written out in postText
#           Remove timestamp on subject line
#
#   2.0.19  2006-10-14  Todd Valentic
#           Make headers parameter to post* methods a dict.
#
#   2.0.20  2007-07-17  Todd Valentic
#           Added listFiles() and write parameter to saveFiles().
#
#   2.0.21  2008-01-06  Todd Valentic
#           Fixed bug in saveFiles where path was ignored on text
#               only messages.
#
#   2.0.22  2008-06-07  Todd Valentic
#           Fixed off by catchup off-by-one error
#
#   2.0.23  2008-08-15  Todd Valentic
#           Ignore path in saveFiles unless it is set (fix in 2.0.21
#               added ./ to all files otherwise, which is unexpected
#               by existing programs).
#
#   2.0.24  2008-08-19  Todd Valentic
#           Only use basename for attached filenames in saveFiles().
#
#   2.0.25  2008-11-13  Todd Valentic
#           Use SafeConfigParser.
#
#   2.0.26  2009-05-04  Todd Valentic
#           Fix bug in setting message header for X-Transport-ArticleNumber.
#               It an email object already has a header set, setting it
#               again does not overwrite the old definition, instead it
#               appends to the end of the list. Make sure to del it first.
#
#   2.0.27  2009-05-11  Todd Valentic
#           Use email instead of MimeWriter.
#           Code cleanup.
#           Use header array.
#
#   2.0.28  2009-08-24  Todd Valentic
#           Set socket timeout on server.
#
#   2.0.29  2009-11-26  Todd Valentic
#           Added getContents()
#
#   2.0.30  2010-05-07  Todd Valentic
#           Add check in getNextMessage() for situations where message
#               count has gone backwards. This can happen when moving
#               to a new news server.
#
#   2.0.31  2014-01-17  Todd Valentic
#           Add exclude to listGroups()
#
#   2.0.32  2016-10-31  Todd Valentic
#           Fix iteration bug introducted in listGroups(exclude)
#
#   2.0.33  2020-01-09  Todd Valentic
#           Add last_read_prefix to NewsPoller
#
#   2016-12-23  Todd Valentic
#               Use datetime.timezone.utc for UTC
#
#   2022-10-06  Todd Valentic
#               Reorder imports
#               Use sapphire.Parser
#               Use pathlib
#               Python3 changes:
#                   - Update expceptions
#                   - Update imports
#                   - Use bytes instead of string
#                   - article() return changed to (response, info)
#               Snake names:
#                   getContents -> get_contents
#                   saveFiles -> save_files
#                   listFiles -> list_files
#                   messageDate -> message_date
#                   asConfig -> as_config
#
#               NewsTool
#                   setServer -> set_server
#                   setGroup -> set_newsgroup
#                   setLog - > set_log
#                   setTimeout - set_timeout
#                   openServer -> open_server
#                   groupExists -> group_exists
#                   datetime - > get_datetime
#                   listArticles -> list_articles
#                   listGroups -> list_newsgroups
#
#   2023-07-26  Todd Valentic
#               Support pathlib in poster
#
#
###########################################################################

import collections
import datetime
import email
import logging
import mimetypes
import nntplib
import pathlib
import time

from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fnmatch import fnmatch

from dateutil import parser
from datatransport.utilities import datefunc, make_path
import sapphire_config as sapphire

utc = datetime.timezone.utc

###### Exception Class ###################################################


class ProcessError(Exception):
    """Raised on processing errors"""


class ProcessRetry(Exception):
    """Raised to request retry on processing error"""


##########################################################################
#
#   Utility Methods
#
##########################################################################


def get_contents(message):
    """Return body and/or contents of each attachment in a list"""

    results = []

    if not message.is_multipart():
        results.append(message.get_payload())
    else:
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            results.append(part.get_payload(decode=True))

    return results


def save_files(message, default="body.txt", path=".", write=True):
    """Save body or attached files"""

    path = pathlib.Path(path)

    if not message.is_multipart():
        if write:
            body = message.get_payload()
            filename = path / default
            make_path(filename)
            filename.write_text(body)
        return [default]

    filenames = []

    counter = 1
    for part in message.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        if not filename:
            ext = mimetypes.guess_extension(part.get_content_type())
            if not ext:
                ext = ".bin"
            filename = f"part-{counter:03}{ext}"
        counter += 1

        filename = path / pathlib.Path(filename).name

        if write:
            make_path(filename)
            filename.write_bytes(part.get_payload(decode=True))

        filenames.append(filename)

    return filenames


def list_files(*pos, **kw):
    """Return list of attached files"""

    kw["write"] = False
    return save_files(*pos, **kw)


def message_date(message):
    """Return the message timestamp"""

    headers = ["X-Transport-Date", "NNTP-Posting-Date", "Date"]

    dateparser = parser.parser()

    for header in headers:
        if header in message:
            timestamp = dateparser.parse(message[header])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=utc)
            return timestamp

    return datetime.datetime.now(utc)


def as_config(message):
    """Return the message content as a sapphire.Parser object"""

    config = sapphire.Parser()
    config.read_string(message.get_payload())

    return config


##########################################################################
#
#   Base Class
#
##########################################################################


class NewsTool:
    """NewsTool base class"""

    def __init__(self):
        self.set_server("localhost")
        self.set_newsgroup("test")
        self.set_log(logging)
        self.set_timeout(60)

    # Configuration variables ---------------------------------------------

    def set_server(self, host, port=119):
        """Set newsserver parameters"""

        self.server_host = host
        self.server_port = port

    def set_newsgroup(self, newsgroup):
        """Set newsgroups header"""

        if isinstance(newsgroup, str):
            self.newsgroup_header = newsgroup
        else:
            self.newsgroup_header = ",".join(newsgroup)

    def set_log(self, func):
        """Set logger"""

        self.log = func

    def set_timeout(self, secs):
        """Set timeout"""

        self.timeout = secs

    # Services -----------------------------------------------------------

    def open_server(self, host=None, port=119):
        """Initialize instance"""

        if host:
            self.set_server(host, port)

        return nntplib.NNTP(self.server_host, 
                            port=self.server_port, 
                            readermode=True, 
                            timeout=self.timeout)

    def has_newsgroup(self, newsgroup=None):
        """Check if newsgroup exists"""

        if not newsgroup:
            newsgroup = self.newsgroup_header

        try:
            server = self.open_server()
            server.group(newsgroup)
            server.quit()
        except nntplib.NNTPTemporaryError as err:
            code = str(err).split()[0]
            if code == "411":
                return False
            raise err

        return True

    def get_datetime(self, server=None):
        """Get time from the server"""

        if server is None:
            server = self.open_server()

        response = server.date()
        datestr = response[0].split()[1]  # 111 YYYYMMDDhhmmss

        return datefunc.strptime(datestr, "%Y%m%d%H%M%S", tzinfo=utc)

    def list_articles(self, offset, newsgroups=None):
        """
        List articles during offset (which is type timedelta)

        offset is a timedelta

        newsgroup can be: None (use the header member)
                          str - single group name
                          list - list of group names
        """

        server = self.open_server()

        start = self.get_datetime(server) - offset

        if newsgroups is None:
            newsgroups = self.newsgroup_header.split(",")

        if isinstance(newsgroups, str):
            newsgroups = [newsgroups]

        articles = {}

        for newsgroup in newsgroups:
            msgs = server.newnews(newsgroup, start)[1]
            articles[newsgroup] = msgs

        return articles

    def list_newsgroups(self, pattern="transport.*", exclude=None):
        """List newsgroups matching pattern"""

        if exclude is None:
            exclude = []
        elif exclude and isinstance(exclude, str):
            exclude = [exclude]

        _response, newsgroups = self.open_server().list()
        newsgroups = [ng for ng in newsgroups if fnmatch(ng[0], pattern)]

        for entry in exclude:
            newsgroups = [ng for ng in newsgroups if not fnmatch(ng[0], entry)]

        results = {}

        for entry in newsgroups:
            minmsg = int(entry[2])
            maxmsg = int(entry[1])
            if maxmsg < minmsg:
                results[entry[0]] = (minmsg, maxmsg, 0)
            else:
                results[entry[0]] = (minmsg, maxmsg, maxmsg - minmsg + 1)

        return results


#########################################################################
#
#   News Poster
#
#########################################################################


class NewsPoster(NewsTool):
    """News Poster"""

    def __init__(self):
        self.clear_headers()
        NewsTool.__init__(self)

        self.set_subject("Unknown")
        self.set_from("transport@datatransport.org")
        self.set_enable(True)

    def set_newsgroup(self, newsgroup):
        """Set newsgroup header"""

        NewsTool.set_newsgroup(self, newsgroup)
        if newsgroup:
            self.set_header("Newsgroups", newsgroup)

    def set_subject(self, value):
        """Set subject header"""

        self.set_header("Subject", value)

    def set_from(self, value):
        """Set from header"""

        self.set_header("From", value)

    def set_enable(self, flag):
        """Set the enable flag"""

        self.enabled = flag

    def set_header(self, key, value):
        """Set header value"""

        self.headers[key] = value

    def clear_headers(self):
        """Clear all headers"""

        self.headers = {}

    def add_headers(self, msg, date=None, extra=None):
        """Add headers to message"""

        if date:
            msg["X-Transport-Date"] = str(date)

        for key, value in self.headers.items():
            msg[key] = value

        if extra:
            for key, value in extra.items():
                msg[key] = value

    def add_file(self, msg, filename):
        """Add file attachment to message"""

        filename = pathlib.Path(filename)

        ctype, encoding = mimetypes.guess_type(filename)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        if maintype == "text":
            contents = filename.read_text("UTF-8")
            part = MIMEText(contents, _subtype=subtype)
        elif maintype == "image":
            contents = filename.read_bytes()
            part = MIMEImage(contents, _subtype=subtype)
        elif maintype == "audio":
            contents = filename.read_bytes()
            part = MIMEAudio(contents, _subtype=subtype)
        else:
            contents = filename.read_bytes()
            part = MIMEBase(maintype, subtype)
            part.set_payload(contents)
            encoders.encode_base64(part)

        basename = filename.name
        part.add_header("Content-Disposition", "attachment", filename=basename)

        msg.attach(part)

    def post(self, filenames=None, comment=None, date=None, headers=None):
        """Post files to newsgroup"""

        if filenames is not None:
            if isinstance(filenames, str):
                filenames = [filenames]
            elif not isinstance(filenames, collections.abc.Iterable): 
                filenames = [filenames]

        if not filenames:
            msg = MIMEText(comment)
        else:
            msg = MIMEMultipart()
            msg.preable = comment

            for filename in filenames:
                self.add_file(msg, filename)

        self.add_headers(msg, date=date, extra=headers)

        return self.post_raw(msg)

    def post_files(self, *pos, **kw):
        """Post files to newsgroup (alias for post)"""

        return self.post(*pos, **kw)

    def post_text(self, text, *pos, **kw):
        """Post text message to newsgroup"""

        return self.post(comment=text, *pos, **kw)

    def post_raw(self, msg):
        """Post message to newsgroup if enabled"""

        if self.enabled:
            return self.open_server().post(msg.as_bytes())

        return None


##########################################################################
#
#   News Control
#
##########################################################################


class NewsControl(NewsPoster):
    """Post control messages to news server"""

    def __init__(self):
        NewsPoster.__init__(self)

        self.set_newsgroup("control")

    def post_command(self, cmd, body=None):
        """Post control message"""

        if not body:
            body = cmd

        self.set_header("Control", cmd)
        self.set_header("Approved", self.headers["From"])
        return self.post(comment=body)

    def newgroup(self, newsgroup):
        """Create a newsgroup"""

        body = f"For your newsgroups file:\n{newsgroup} {newsgroup}"
        return self.post_command(f"newgroup {newsgroup}", body)

    def rmgroup(self, newsgroup):
        """Remove a newsgroup"""

        return self.post_command(f"rmgroup {newsgroup}")

    def cancel_message(self, newsgroup, message_id):
        """Cancel a message in a newsgroup"""

        self.set_newsgroup(newsgroup)
        return self.post_command(f"cancel {message_id}")

    def cancel_newsgroup(self, newsgroup):
        """Cancel all of the messages in a newsgroup"""

        server = self.open_server()
        _response, _count, first, last, _name = server.group(newsgroup)
        _response, subject = server.xhdr("Message-ID", f"{first}-{last}")
        server.quit()

        for _article_number, message_id in subject:
            self.cancel_message(newsgroup, message_id)


##########################################################################
#
#   News Poller
#
##########################################################################


class NewsPoller(NewsTool):
    """News Poller"""

    def __init__(self):
        NewsTool.__init__(self)

        self.set_callback(self.default_callback)
        self.set_debug(False)
        self.set_single_shot(False)
        self.set_retry_wait(60)
        self.set_stop_func(self.default_stop)
        self.set_last_read_prefix("")

    # Configuration variables ---------------------------------------------

    def set_callback(self, func):
        """Set callback processing function"""

        self.callback = func

    def set_debug(self, flag):
        """Set debug flag"""
        self.debug = flag

    def set_single_shot(self, flag):
        """Set single shot flag"""
        self.single_shot = flag

    def set_retry_wait(self, secs):
        """Set retry wait time"""
        self.retry_wait = secs

    def set_stop_func(self, func):
        """Loop exit condition"""
        self.stop = func

    def set_last_read_prefix(self, prefix):
        """Prefix for last read tracking file"""
        if prefix:
            self.last_read_prefix = prefix + "-"
        else:
            self.last_read_prefix = ""

    # Methods -------------------------------------------------------------

    def default_stop(self):
        """Place holder - clients can override"""
        return False

    def default_callback(self):
        """Place holder - set by clients"""
        return

    def last_read_filename(self):
        """Return the filename of the last_read tracking file"""
        return pathlib.Path(self.last_read_prefix + self.newsgroup_header)

    def save_last_read(self, article_num):
        """Update the last read tracking file"""
        self.last_read_filename().write_text(str(article_num), "UTF-8")

    def load_last_read(self):
        """Read the last read tracking file"""
        article_num = self.last_read_filename().read_text("UTF-8")
        return int(article_num.strip())

    def mark_read(self, msgcount=1, reset=False):
        """Mark newsgroup as read"""

        if msgcount == 0:
            return

        server = self.open_server()
        response = server.group(self.newsgroup_header)
        server.quit()

        first = int(response[2])
        last = int(response[3])

        try:
            lastid = self.load_last_read()
        except (FileNotFoundError, ValueError, UnicodeDecodeError):
            lastid = first - 1

        if msgcount == 1:
            newlast = last
        elif reset:
            newlast = max(0, last + msgcount)
        else:
            newlast = max(lastid, last + msgcount)

        self.log.debug(
            f"Marking read ({msgcount}): "
            f"old watermark={lastid}, new watermark={newlast}"
        )

        self.save_last_read(newlast)

    def call_processing(self, message):
        """Call the processing callback function"""

        article_number = message["X-Transport-ArticleNumber"]

        self.log.debug(f"  Processing message {article_number}")

        try:
            self.callback(message)
        except ProcessRetry:
            raise  # propogate up
        except BaseException as err:  # pylint: disable=broad-except
            self.log.error(f"Problem in the callback function: {err}")

            if self.debug:
                raise err

    def process_article(self, message):
        """Process the article"""

        while not self.stop():

            try:
                self.call_processing(message)
                self.mark_message_read(message)
                return
            except ProcessRetry:
                time.sleep(self.retry_wait)

            # FIX ME - should pass in/use wait

    def mark_message_read(self, message):
        """Mark this message has read"""

        self.save_last_read(message["X-Transport-ArticleNumber"])

    def process_past(self, offset):
        """Process old messages"""

        self.log.debug("Processing past articles:")

        server = self.open_server()

        for newsgroup, articles in self.list_articles(offset=offset).items():
            self.log.debug(f"  {newsgroup}: {len(articles)} articles available")

            for article_num in articles:

                if self.stop():
                    break

                try:
                    message = self.get_article(server, article_num)
                except:  # pylint: disable=bare-except
                    continue

                # TBD - Better except handling

                self.process_article(message)

    def get_article(self, server, article_num):
        """Retrieve message from the newsgroup"""

        _response, info = server.article(article_num)
        content = b"\n".join(info.lines)
        message = email.message_from_bytes(content)

        del message["X-Transport-ArticleNumber"]
        message["X-Transport-ArticleNumber"] = article_num

        return message

    def get_next_message(self):
        """Get the next message from the newsgroup"""

        try:
            server = self.open_server()
            _resp, count, low, high, name = server.group(self.newsgroup_header)
        except nntplib.NNTPError as e:
            self.log.debug("Failed to get message numbers: %s", e)
            return None
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.log.debug("Failed to get message numbers: %s", e)
            return None

        self.log.debug(f"Group {name} has {count} articles from {low} to {high}")

        try:
            lastid = self.load_last_read()
            self.log.debug(f"  last message read was {lastid}")
        except:  # pylint: disable=bare-except
            lastid = low - 1
            self.log.debug("  no messages read yet")

        if low > high:
            self.log.debug("  no messages on server")
            return None

        if lastid < low - 1 or lastid > high:
            self.log.debug("  catching up to available messages")
            lastid = low - 1

        nextid = lastid + 1

        if nextid > high:
            self.log.debug("  no new messages")
            return None

        article_number = str(nextid)

        self.log.debug("  retrieving  message {article_number}")

        try:
            message = self.get_article(server, article_number)
        except nntplib.NNTPTemporaryError as e:
            code = int(str(e).split()[0])
            if code >= 400:
                self.log.error("Problem retrieving {article_num} (code={code})")
                self.save_last_read(article_number)
            return None
        except:  # pylint: disable=bare-except
            self.log.exception("Problem parsing message body")
            self.save_last_read(article_number)
            return None

        return message

    def poll(self):
        """Poll newsgroup for new messages"""

        while not self.stop():

            message = self.get_next_message()

            if message is None:
                break

            self.process_article(message)

            if self.single_shot:
                break

        self.log.debug("End of polling cycle")
