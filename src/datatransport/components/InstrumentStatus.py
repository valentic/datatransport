##############################################################################
#
#  NOTICE: Deprectated. Use NewsgroupMonitor for new projects.
#
#  InstrumentStatus
#
#  This script polls newsgroups to determine if an instrument is running.
#  The output is an HTML fragment that can be included in web pages.
#
#  There is a plugin callback system available to chain into the events
#  for each instrument. You need to create a python module with a callable
#  function and make sure that it is with in the python path. If you have
#  the plugin in the group's home, then you will want to make sure to add
#  this to the PYTHONPATH. Add the following line in the ProcessGroup
#  section of the config file:
#
#  environ.add.pythonpath: %(group.home)s
#
#  The function must be callable with the following keyword parameters:
#
#      callback(self,curstate=None,prevstate=None,changed=0)
#
#  When the module is first loaded, the init method will be called.
#  You can initialize any variables that you need
#  by storing then into self.*. You can even pull in values from the
#  config file (which is cool!). During the run of the program, the
#  callback will be called with a code in the even field. The current
#  codes are defined in Status in this module. If the state has
#  changed since the last check, then the changed flag is set.
#
#  History:
#
#   1.0.0   2000-02-22  TAV
#           Initial implementation
#
#   1.0.1   2000-02-22  TAV
#           Added maillist reporting.
#
#   1.0.2   2000-02-26  TAV
#           Added ability to set the table title from the config file.
#
#   1.0.3   2000-02-29  TAV
#           Updated appearance of HTML tables (colors and fonts).
#
#   1.0.4   2000-03-14  TAV
#           Another HTML update - now uses simplified table and style sheets.
#
#   1.0.5   2000-04-26  TAV
#           Added the reportFailure parameter to the instruments. This will
#               cause a mail message to be sent to the troublegroup news
#               group. The intention is to notify people when an instrument
#               that should always be running has stopped.
#
#   1.0.6   2000-10-26  TAV
#           Added the reportStart parameter to complement the reportStop
#               feature. This change allows system status to signal when
#               an instrument such as the imager or lidar begin sending data.
#
#   1.0.7   2001-11-09  TAV
#           Renamed newstool -> NewsTool
#
#   1.0.8   2001-12-02  TAV
#           Fixed problem connecting to newsserver due to NewsTool name
#               change. Also added some log messages to indicate alert
#               to problem in future.
#           Cleaned up some HTML.
#
#   1.0.9   2002-09-03  Todd Valentic
#           Moved to python2, sri.transport -> Transport
#
#   1.0.10  2002-10-04  Todd Valentic
#           Fixed some config file name bugs.
#           Added traceback listing if count get operation fails.
#
#   1.0.11  2002-11-10  Todd Valentic
#           Added more tracebacks.
#           Check for self.running, use self.wait()
#
#   1.0.12  2003-02-21  Todd Valentic
#           Improved determination of time from header
#
#   1.0.13  2003-03-26  Todd Valentic
#           Assumptions were being made that the time was GMT. Now using
#               ISO format for printing in messages.
#           Using DateTime module versus time for everything.
#           Changed the time determination again. Now I'm just using the
#               NNTP-Posting-Date header instead of trying to parse the
#               header. This header reflects the time that the last message
#               was posted into the transport network.
#           Removed string module (using methods instead).
#
#   1.0.14  2003-04-04  Todd Valentic
#           Changed the pollserver and pollrate config parameters to be
#               poll.newsserver and poll.rate so they are consistent with
#               other naming schemes.
#           Fixed newly instroduced bug in instrument check time.
#           Changed reportStart and reportStop to report.start and report.stop
#
#   1.1.0   2003-04-07  Todd Valentic
#           Started major overhaul. Now remember state between runs.
#
#   1.1.1   2003-04-18  Todd Valentic
#           Changed window -> timeout for config parameter.
#           Default the timeout to 5 minutes.
#
#   1.1.2   2003-05-11  Todd Valentic
#           Added link to parent.abort in Instrument class.
#           Added plugin system to hook into events.
#
#   1.1.3   2003-06-11  Todd Valentic
#           Converted plugin to new general callback scheme.
#
#   1.1.4   2003-08-14  Todd Valentic
#           Problem using the general callback scheme with Instrument.
#               need to make some sort of mixin class.
#
#   1.1.5   2004-08-28  Todd Valentic
#           Updated to XML-RPC version.
#           Import PageKit from Componentsa
#
#   1.1.6   2004-12-13  Todd Valentic
#           Removed traceback call (left over from XML-RPC conversion)
#           Renamed self.config -> self.history to prevent name collision.
#
#   1.1.7   2004-12-27  Todd Valentic
#           Convert from mx.DateTime to datetime
#
#   1.1.8   2005-01-26  Todd Valentic
#           Added get_boolean to Instrument to track change 
#
#   1.1.9   2005-05-04  Todd Valentic
#           Added getfloat() to instrumnent (bug fix)
#
#   1.1.10  2005-07-07  Todd Valentic
#           Use get_timedelta for poll.rate
#
#   1.1.11  2007-08-06  Todd Valentic
#           Added history posting
#
#   1.1.12  2007-08-08  Todd Valentic
#           Fixed typo in Instrument news server parameter
#
#   1.1.13  2008-11-13  Todd Valentic
#           Use SafeConfigParser
#
#   1.1.14  2008-12-11  Todd Valentic
#           Make sure only strings are used in config
#
#   1.1.15  2009-05-05  Todd Valentic
#           Fixed bug in log message when posting failed.
#
#   2016-12-23  Todd Valentic
#               Use datetime.timezone for utc
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               Python3 migration
#                   ConfigParser -> sapphire.Parser 
#                   StringIO -> io.StringIO
#                   NewsPoster
#
##############################################################################

import datetime
import io
import sys

from dateutil import parser

from datatransport import ProcessClient
from datatransport import NewsPoster
from datatransport import newstool
from datatransport import ConfigComponent
from datatransport.components import PageKit

import sapphire_config as sapphire

##############################################################################


class InstrumentTable(PageKit.Table):
    def __init__(self, title, instruments):
        PageKit.Table.__init__(self, title=title)

        self.instruments = instruments
        self.num_cols = 2

    def print_status(self, instrument):

        print("<tr>")
        print('<td class=desc width="85%">', end="")
        print("&nbsp;&nbsp;%s" % instrument.label, end="")
        print("</td>")

        if instrument.status == Status.online:
            msg = "Running"
            style = "running"
        elif instrument.status == Status.offline:
            msg = "Stopped"
            style = "stopped"
        else:
            msg = "Unknown"
            style = "warning"

        print("<td class=%s>%s</td>" % (style, msg))
        print("</tr>")

    def body(self):

        for instrument in self.instruments:
            self.print_status(instrument)


##############################################################################


class Status:

    unknown = 0
    offline = 2
    online = 3

    label = {unknown: "unknown", offline: "offline", online: "online"}


##############################################################################


class Instrument(ConfigComponent):
    def __init__(self, name, parent):
        ConfigComponent.__init__(self, None, name, parent)

        self.news_poster = NewsPoster(self, quiet=1)

        self.load(parent.history)

        self.label = self.get("label", name)
        self.pollserver = self.get("poll.newsserver", "localhost")
        self.pollgroup = self.get("poll.newsgroup", "")
        self.reportstart = self.get_boolean("report.start", True)
        self.reportstop = self.get_boolean("report.stop", True)
        self.timeout = self.get_timedelta("timeout", 300)
        self.callback = self.get_callback("callback")

        if self.callback:
            self.callback(self, curstatus=self.status)

        self.newstool = newstool.NewsTool()
        self.newstool.set_server(self.pollserver)
        self.newstool.set_newsgroup(self.pollgroup)

        self.log.info("  " + name)
        self.log.info("    label       : %s" % self.label)
        self.log.info("    poll server : %s" % self.pollserver)
        self.log.info("    poll group  : %s" % self.pollgroup)
        self.log.info("    timeout     : %s" % self.timeout)
        self.log.info("    report start: %d" % self.reportstart)
        self.log.info("    report stop : %d" % self.reportstop)
        self.log.info("    status      : %s" % Status.label[self.status])
        self.log.info("    start time  : %s" % self.starttime)
        self.log.info("    stop time   : %s" % self.stoptime)
        self.log.info("    first msg   : %s" % self.firstmessage)
        self.log.info("    last msg    : %s" % self.lastmessage)
        self.log.info("    run time    : %s" % self.runtime)
        self.log.info("    off time    : %s" % self.offtime)

        module = self.get("callback.module")
        function = self.get("callback.function")

        if self.callback:
            self.log.info("    callback    : %s.%s" % (module, function))
        else:
            self.log.info("    callback    : None")

    def save(self, config):

        if not config.has_section(self.name):
            config.add_section(self.name)

        config.set(self.name, "status", str(self.status))
        config.set(self.name, "starttime", str(self.starttime))
        config.set(self.name, "stoptime", str(self.stoptime))
        config.set(self.name, "firstmessage", str(self.firstmessage))
        config.set(self.name, "lastmessage", str(self.lastmessage))
        config.set(self.name, "runtime", str(self.runtime.seconds))
        config.set(self.name, "offtime", str(self.offtime.seconds))
        config.set(self.name, "label", self.label)

    def loadtime(self, config, key):

        try:
            return parser.parse(config.get(self.name, key))
        except:
            return datetime.datetime.now(datetime.timezone.utc)

    def loaddeltatime(self, config, key):

        try:
            secs = config.get_float(self.name, key)
            return datetime.timedelta(seconds=secs)
        except:
            return datetime.timedelta(0)

    def load(self, config):

        try:
            self.status = config.get_int(self.name, "status")
        except:
            self.status = Status.unknown

        self.starttime = self.loadtime(config, "starttime")
        self.stoptime = self.loadtime(config, "stoptime")
        self.firstmessage = self.loadtime(config, "firstmessage")
        self.lastmessage = self.loadtime(config, "lastmessage")

        self.runtime = self.loaddeltatime(config, "runtime")
        self.offtime = self.loaddeltatime(config, "offtime")

    def check(self):

        prevstatus = self.status
        self.status = self.get_status()

        self.changed = 0

        # unknown -> online

        if prevstatus == Status.unknown and self.status == Status.online:

            self.starttime = self.firstmessage

            self.log.info("  %s state now known (online)" % self.name)

        # unknown -> offline

        elif prevstatus == Status.unknown and self.status == Status.offline:

            self.stoptime = self.servertime
            self.starttime = self.servertime

            self.log.info("  %s state now known (offline)" % self.name)

        # unknown -> unknown

        elif prevstatus == Status.unknown and self.status == Status.unknown:

            self.log.debug("  %s state still unknown" % self.name)

        # offline -> online

        elif prevstatus == Status.offline and self.status == Status.online:

            self.changed = 1
            self.starttime = self.firstmessage
            self.changetime = self.starttime
            self.offtime = self.starttime - self.stoptime

            if self.reportstart:
                header, message = self.start_message()
                self.post(header, message)

            self.log.info("  %s going online (was off %s)" % (self.name, self.offtime))

        # online -> offline

        elif prevstatus == Status.online and self.status == Status.offline:

            self.changed = 1
            self.stoptime = self.lastmessage
            self.changetime = self.stoptime
            self.runtime = self.stoptime - self.starttime

            if self.reportstop:
                header, message = self.stop_message()
                self.post(header, message)

            self.log.info("  %s going offline (was on %s)" % (self.name, self.runtime))

        # still online

        elif prevstatus == Status.online and prevstatus == self.status:

            self.stoptime = self.lastmessage
            self.runtime = self.stoptime - self.starttime

            self.log.debug("  %s still online (%s)" % (self.name, self.runtime))

        # still offline

        elif prevstatus == Status.offline and prevstatus == self.status:

            self.offtime = self.servertime - self.stoptime

            self.log.debug("  %s still offline (%s)" % (self.name, self.offtime))

        if self.callback:
            try:
                self.callback(
                    self,
                    curstatus=self.status,
                    prevstatus=prevstatus,
                    changed=self.changed,
                )
            except:
                self.log.exception("Problem running the callback function:")

        return self.changed

    def get_message_time(self, msg):

        # Date is UTC

        try:
            server = self.newstool.open_server()
            response = server.group(self.pollgroup)
            date = server.xhdr("NNTP-Posting-Date", msg)[1][0]
            date = " ".join(date.split()[1:])
            date = parser.parse(date)
            server.quit()
        except:
            date = datetime.datetime.now(datetime.timezone.utc)
            self.log.exception("Problem determining message time")

        return date

    def get_status(self):

        articles = self.newstool.list_articles(self.timeout).values()[0]

        self.servertime = self.newstool.datetime()

        if len(articles) > 0:

            self.firstmessage = self.get_message_time(articles[0])
            self.lastmessage = self.get_message_time(articles[-1])

            return Status.online

        else:

            return Status.offline

    def start_message(self):

        header = "%s has started" % self.label

        message = []
        message.append("")
        message.append("  The following instrument has started sending data:")
        message.append("")
        message.append("    Instrument: %s" % self.label)
        message.append("    Date/Time : %s" % self.starttime)
        message.append("    Offline   : %s" % self.offtime)
        message.append("")

        message = "\n".join(message)

        return header, message

    def stop_message(self):

        header = "%s has stopped" % self.label

        message = []
        message.append("")
        message.append("  The following instrument has stopped sending data:")
        message.append("")
        message.append("    Instrument: %s" % self.label)
        message.append("    Date/Time : %s" % self.stoptime)
        message.append("    Online    : %s" % self.runtime)
        message.append("")

        message = "\n".join(message)

        return header, message

    def post(self, header, message):

        try:
            self.news_poster.set_subject(header)
            self.news_poster.post_text(message)
        except:
            self.log.exception("Error posting message for %s" % self.name)


##############################################################################


class InstrumentStatus(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)
        self.pollrate = self.get_timedelta("poll.rate", 60)
        self.htmlname = self.get("htmlname", "instrumentstatus.html")
        self.title = self.get("title", "Instrument Status")
        self.history = sapphire.Parser()

        self.history_poster = self.create_news_poster("history", quiet=True)

        self.load_history()

        self.log.info("Reading instrument definitions:")

        self.instruments = []
        self.labelwidth = 0

        for name in self.get("instruments", "").split():
            try:
                instrument = Instrument(name, self)
                self.instruments.append(instrument)
                self.labelwidth = max(self.labelwidth, len(instrument.label))
            except:
                self.log.exception("Problem creating %s" % name)
                self.abort("Exiting")

        self.save_history()

    def load_history(self):

        self.log.info("Loading history")

        try:
            self.history.read("history")
        except:
            self.log.exception("Problem reading history file:")
            self.abort("Exiting")

    def save_history(self):

        self.history = sapphire.Parser()

        self.log.debug("Saving history")

        for instrument in self.instruments:
            instrument.save(self.history)

        self.history.write(open("history", "w"))

        buffer = io.StringIO.StringIO()
        self.history.write(buffer)

        try:
            self.history_poster.post_text(buffer.getvalue())
        except:
            self.log.error("Failed to post history")

    def post_message(self):

        message = []
        message.append("")
        message.append("  A change in instrument status has been detected:")
        message.append("")

        header = None

        for instrument in self.instruments:

            status = Status.label[instrument.status].capitalize()

            if instrument.changed == 0:
                changed = ""
            else:
                changed = "<-- %s" % instrument.changetime
                if not header:
                    header = instrument.label + " " + status
                else:
                    header = "Multiple instruments have changed status"

            instrument.changed = 0

            message.append(
                "  %s: %-10s %s"
                % (instrument.label.rjust(self.labelwidth), status, changed)
            )

        message = "\n".join(message)

        try:
            self.news_poster.set_subject(header)
            self.news_poster.post_text(message)
        except:
            self.log.error("Error posting message to mailing list.")

    def report(self):

        InstrumentTable(self.title, self.instruments).save(self.htmlname)

        self.post_message()

        self.log.info("Updated status report")

    def instrument_change(self):

        self.log.debug("Checking for status change:")

        numchanged = 0

        for instrument in self.instruments:

            try:
                instrument.check()
            except:
                self.log.exception("Problem checking %s" % instrument.name)
                continue

            numchanged += instrument.changed

            if self.is_stopped():   
                break

        return numchanged > 0

    def main(self):

        while self.wait(self.pollrate):

            if self.instrument_change():
                self.save_history()
                self.report()

        self.save_history()


def main():
    InstrumentStatus(sys.argv).run()
