#####################################################################
#
#   PlotTool
#
#   The PlotTool creates plots from incoming data streams using the
#   Round Robin Database (RRD) system. Each time a new record is
#   posted to the monitored newsgroup, the values will be appended
#   to the database and a new plot created. The incoming data format
#   defaults to the ConfigParser (section,key/value) style. However,
#   hooks are provided for subsclassed objects to override this
#   behaviour.
#
#   History:
#
#   1.0.0   2002-10-30  Todd Valentic
#           Initial implementation.
#
#   1.0.1   2003-06-04  Todd Valentic
#           Added time zone info
#           Updated some plot formatting
#
#   1.0.2   2003-06-30  Todd Valentic
#           Updated to new NewsPoller interface
#
#   1.0.3   2003-07-18  Todd Valentic
#           Generalized plotting program.
#
#   1.0.4   2003-08-08  Todd Valentic
#           Use ConfigMixin
#
#   1.0.5   2003-08-26  Todd Valentic
#           Use rrdtool vs RRDtool.
#
#   1.0.6   2003-08-27  Todd Valentic
#           Added min/max checks for variables.
#
#   1.0.7   2004-01-14  Todd Valentic
#           Added ability to set the data set type (DST) and
#               consolidation function (CF) for variables.
#
#   1.0.8   2004-02-15  Todd Valentic
#           Added ability to set start and end time.
#           Added automatic labeling and colors if more then
#               one variable on a plot.
#
#   1.0.9   2004-02-17  Todd Valentic
#           Fixed bug in setting variable range limits. Now
#               explicitly test for None.
#
#   1.0.10  2005-03-17  Todd Valentic
#           Converted from DateTime -> datetime
#           Use ConfigComponent
#           Reworked time zone. Specifically set TZ
#               before updates and plotting.
#           Removed TimeZone objects.
#
#   1.0.11  2006-02-02  Todd Valentic
#           Create output path if necessary.
#
#   1.0.12  2006-07-12 Todd Valentic
#           RRD module changed name again rrdtool -> rrdtoolmodule.
#           Try importing rrdtool then rrdtoolmodule.
#
#   1.0.13  2007-09-18  Todd Valentic
#           Change the file extension on the plots to ".png"
#               I didn't notice that the plot type had changed
#               with RRD 1.2 from .gif!
#
#   1.0.14  2007-10-17  Todd Valentic
#           Fixed bug when a CF other than AVERAGE was used.
#
#   1.0.15  2008-08-11  Todd Valentic
#           Better log info.
#
#   1.0.16  2008-08-20  Todd Valentic
#           Added y.rigid option.
#
#   1.0.17  2008-08-26  Todd Valentic
#           Added CDEF option for variables.
#
#   1.0.18  2008-11-13  Todd Valentic
#           Use SafeConfigParser
#
#   1.0.19  2008-12-08  Todd Valentic
#           Allow line.width to be a float
#
#   1.0.20  2008-12-30  Todd Valentic
#           Only print labels if actually specified.
#           Added logarithmic option to plot
#
#   1.0.21  2009-01-09  Todd Valentic
#           Added misc parameter for plots to add anything
#               other parameters to the graph.
#           Added variable plot style of none to supress any
#               lines or areas from being drawn.
#           Added stack parameter for variables
#
#   1.0.22  2009-01-30  Todd Valentic
#           Tune default line colors and add second (green) area color.
#           Use getComponents()
#           Use NewsTool.asConfig()
#           Make sure ignore_errors is honored
#
#   1.0.23  2009-02-09  Todd Valentic
#           Added plotgroups
#
#   1.0.24  2009-04-28  Todd Valentic
#           Expand plotgroups to be a full component
#           Add matching rules
#           Check for set type (compatibility for python 2.3)
#
#   1.0.25  2009-09-02  Todd Valentic
#           Add filter option for variables to filter out non-numeric
#               characters.
#
#   1.0.26  2009-11-09  Todd Valentic
#           Move plotrate into period.
#
#   1.0.27  2010-02-23  Todd Valentic
#           Do not draw line when stacking area plots
#
#   1.0.28  2010-06-01  Todd Valentic
#           Add debug log entries in check_headers
#
#   1.0.29  2010-09-08  Todd Valentic
#           Allow plotgroup specific variables
#           Add area stack.offset and stack.line
#           Auto increment stack.offset with stack.offset.auto
#           Use get_list()
#           Add area.alpha parameter
#           Use linecolor+alpha for areacolor if it isn't specified.
#           Add header checks per variable
#
#   1.0.30  2011-08-28  Todd Valentic
#           Added hidden variables.
#           Added shadow variables.
#           Added hash for Variable
#
#   1.0.31  2012-05-20  Todd Valentic
#           Added sql support
#               There is a problem with libdbi on CentOS 5. The
#               drivers were not linked properly and don't load.
#               To work around, shell out and run rrdtool. This
#               also gets around running transport in a virtual
#               environment.
#           Added GRID and MGRID colors
#           Added TEXTALIGN
#
#   1.0.32  2012-11-08  Todd Valentic
#           Move plot config file loading to load_plots(). This will
#               all for injecting values into the config file from
#               subclassed versions of PlotTool (example usage
#               would be to pull information from a database). It
#               can also be used to dynamically reload the plot
#               definitions.
#
#   1.0.33  2014-02-16  Todd Valentic
#           Add plot name to localvars when loading variables.
#
#   1.0.34  2015-08-29  Todd Valentic
#           Make sure lookup stack handles plotgroup keys
#           Add font options
#
#   1.0.35  2018-01-16  Todd Valentic
#           Update default line colors (values from matplotlib tab10)
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               Replace datefunc calls with new methods
#               Use config get_ methods
#               NewsPoller
#
#####################################################################

import fnmatch
import os
import string
import sys
import time

from datetime import datetime
from subprocess import Popen, PIPE

from datatransport import ProcessClient
from datatransport import newstool
from datatransport import NewsPoller
from datatransport import ConfigComponent

# Fake the rrdtool module


class RRDTool:
    def __getattr__(self, name):
        def method(*args):
            args = list(args)
            args.insert(0, name)
            args.insert(0, "rrdtool")
            p = Popen(args, stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            if p.returncode != 0:
                raise IOError(err)
            return out, err

        return method


rrdtool = RRDTool()


class ManageTZ:
    def __init__(self):

        if "TZ" in os.environ:
            self.tz = os.environ["TZ"]
        else:
            self.tz = None

    def set(self, newtz):

        os.environ["TZ"] = newtz
        time.tzset()

    def restore(self):

        if self.tz:
            self.set(self.tz)
        else:
            del os.environ["TZ"]
            time.tzset()


timezone = ManageTZ()


def get_headers(self, key):

    headers = {}

    for entry in self.get_list(key, token="\n"):
        if not entry:
            continue
        try:
            header, value = [x.strip() for x in entry.split("=", 1)]
        except:
            self.log.exception("Problem parsing: %s" % entry)
            raise
        headers[header] = value

    return headers


ConfigComponent.get_headers = get_headers

####################################################################
#
#   Period
#
#   This component represents a time period over which to plot
#   data. The values are:
#
#   span - rrd time description for how long to plot from the
#          end of the archive.
#
#   xlabel - String to print as the x-axis label
#   suffix - Appended to filename (before extension). Defaults to the
#            value of span. The current time is applied in strftime
#            style.
#   ticks  - Formatting string for the x-tick labels (rrd style)
#
#   Examples:
#       span;   1day
#       xlabel: %A, %B, %d, %Y
#       suffix: 1day
#       ticks:  MINUTE:30:HOUR:2:HOUR:2:0:%H:%M
#
#   Plots are generated at intervals of plotrate, which can be
#   independently set for each period.
#
####################################################################


class Period(ConfigComponent):
    def __init__(self, name, config):
        ConfigComponent.__init__(self, "period", name, config)

        self.span = self.get("span", "1hour")
        self.xlabel = self.get("xlabel", "")
        self.suffix = self.get("suffix", name)
        self.ticks = self.get("ticks", None)
        self.plotrate = self.get_timedelta("plotrate", 60)

        self.log.info("      period: %s" % name)
        self.log.info("        span    : %s" % self.span)
        self.log.info("        xlabel  : %s" % self.xlabel)
        self.log.info("        suffix  : %s" % self.suffix)
        self.log.info("        ticks   : %s" % self.ticks)
        self.log.info("        plotrate: %s" % self.plotrate)

        self.plotrate = self.plotrate.total_seconds()
        self.next_plot_time = time.time()

    def ready_to_plot(self):
        return time.time() > self.next_plot_time

    def schedule_next_plot(self):
        waittime = self.plotrate - time.time() % self.plotrate
        self.next_plot_time = time.time() + waittime


####################################################################
#
#   Variable
#
#   This component represents a variable to store in the database
#   and draw on the plot. It consists of a section/key pair that
#   is used to look up the value in the ConfigParser-style input
#   file. By default, the key is just the name.
#
#   We assume that the timestamps of the variable are given in UTC.
#   If they are not, you need to manipulate the timestamp in a
#   derived class.
#
#   If the style is none, the database reference is included,
#   but no line or area is plotted (the intention being that
#   a CDEF in plot is going to use these variables to generate
#   it's own line).
#
#   style: area | line | none
#
####################################################################


class Variable(ConfigComponent):
    def __init__(self, name, parent, **kw):
        ConfigComponent.__init__(self, "variable", name, parent, localvars=kw)

        self.plotgroup = kw["plotgroup"]

        self.lookup_stack.append("variable.%s.%s." % (self.plotgroup, name))

        if self.plotgroup and not os.path.exists(self.plotgroup):
            os.makedirs(self.plotgroup)

        self.sql = self.get("sql")
        self.sqlfunc = self.get("sql.func", "avg")
        self.key = self.get("key", name)
        self.section = self.get("section", "DEFAULT")
        self.label = self.get("label", "")
        self.linecolor = self.get("line.color", "")
        self.linewidth = self.get_float("line.width", 1)
        self.areacolor = self.get("area.color")
        self.areaalpha = self.get("area.alpha")
        self.style = self.get("style", "line").lower()
        self.min_value = self.get_float("min", None)
        self.max_value = self.get_float("max", None)
        self.datatype = self.get("datatype", "GAUGE")
        self.cf = self.get("function", "AVERAGE")
        self.cdef = self.get("cdef", None)
        self.stack = self.get("stack", False)
        self.stackoffset = self.get("stack.offset")
        self.stackauto = self.get_boolean("stack.offset.auto", False)
        self.stackline = self.get_boolean("stack.line", False)
        self.filter = self.get_boolean("filter", False)
        self.headers = self.get_headers("headers")
        self.start = self.get_datetime("start", "")
        self.end = self.get_datetime("end", "")
        self.shadow = self.get("shadow")

        self.log.info("      variable: %s" % name)
        self.log.info("        plotgroup   :  %s" % self.plotgroup)
        self.log.info("        shadow      :  %s" % self.shadow)
        self.log.info("        key         :  %s" % self.key)
        self.log.info("        section     :  %s" % self.section)
        self.log.info("        label       :  %s" % self.label)
        self.log.info("        style       :  %s" % self.style)
        self.log.info("        line.color  :  %s" % self.linecolor)
        self.log.info("        line.width  :  %s" % self.linewidth)
        self.log.info("        area.color  :  %s" % self.areacolor)
        self.log.info("        range.min   :  %s" % self.min_value)
        self.log.info("        range.max   :  %s" % self.max_value)
        self.log.info("        data type   :  %s" % self.datatype)
        self.log.info("        function    :  %s" % self.cf)
        self.log.info("        cdef        :  %s" % self.cdef)
        self.log.info("        stack       :  %s" % self.stack)
        self.log.info("        stack.offset:  %s" % self.stackoffset)
        self.log.info("        filter      :  %s" % self.filter)
        self.log.info("        headers     :  %s" % self.headers)
        self.log.info("        start       :  %s" % self.start)
        self.log.info("        end         :  %s" % self.end)
        self.log.info("        sql         :  %s" % self.sql)

        if self.start:
            self.start = ":start=%s" % self.start.strftime("%H\:%M %Y%m%d")

        if self.end and not self.start:
            self.start = ":start=00\:00 01/01/1980"

        if self.end:
            self.end = ":end=%s" % self.end.strftime("%H\:%M %Y%m%d")

        if self.shadow:
            self.database = os.path.join(self.plotgroup, self.shadow + ".rrd")
        elif self.sql:
            self.database = self.sql
        else:
            self.database = os.path.join(self.plotgroup, name + ".rrd")
            if not os.path.exists(self.database):
                self.create_database()

        self.linecolors = [
            "2B337F",
            "ff7f0e",
            "2ca02c",
            "d62728",
            "9467bd",
            "8c564b",
            "e377c2",
            "e377c2",
            "7f7f7f",
            "17becf",
        ]

        self.areacolors = ["AAAADD", "66AF6C"]

    def __hash__(self):
        return hash("%s:%s" % (self.name, self.plotgroup))

    def __eq__(self, other):
        return other.__hash__() == self.__hash__()

    def __repr__(self):
        return "%s:%s" % (self.name, self.plotgroup)

    def create_database(self):

        oneday = 60 * 60 * 24

        samplerate = self.get_timedelta("samplerate", 60)
        timeout = self.get_timedelta("timeout", 60)
        duration = self.get_timedelta("duration", oneday)

        samplerate = samplerate.total_seconds()
        timeout = timeout.total_seconds()
        duration = duration.total_seconds()

        startTime = time.time() - duration

        cmd = []
        cmd.append(self.database)
        cmd.append("-b %d" % startTime)
        cmd.append("-s %d" % samplerate)
        cmd.append("RRA:%s:0.5:1:%d" % (self.cf, int(duration / samplerate)))

        if self.min_value is not None:
            minvalue = str(self.min_value)
        else:
            minvalue = "U"

        if self.max_value is not None:
            maxvalue = str(self.max_value)
        else:
            maxvalue = "U"

        cmd.append(
            "DS:%s:%s:%d:%s:%s"
            % (self.name, self.datatype, timeout, minvalue, maxvalue)
        )

        try:
            rrdtool.create(*tuple(cmd))
        except:
            timezone.restore()
            self.log.exception("Error creating database")
            self.abort("Exiting")

        self.log.info("Created initial database for %s" % self.name)

    def update(self, timestamp, value):

        if self.shadow or self.sql:
            return

        entry = "%d" % timestamp.timestamp()

        if value:
            entry += ":" + str(value)
        else:
            entry += ":U"

        # self.log.debug('%s updated at %s' % (self.name,timestamp))
        rrdtool.update(self.database, entry)

    def options(self, index, hidden=False):

        params = []
        line = "LINE%f" % self.linewidth
        name = self.name

        if self.shadow:
            dsname = self.shadow
        elif self.sql:
            dsname = self.sqlfunc
        else:
            dsname = self.name

        params.append(
            "DEF:%s=%s:%s:%s%s%s"
            % (self.name, self.database, dsname, self.cf, self.start, self.end)
        )

        if self.label:
            label = self.label
        else:
            label = ""

        if self.linecolor:
            linecolor = self.linecolor
        else:
            linecolor = self.linecolors[index % len(self.linecolors)]

        if self.areacolor:
            areacolor = self.areacolor
        else:
            areacolor = linecolor

        if self.areaalpha and len(areacolor) == 6:
            areacolor += self.areaalpha

        if self.cdef:
            name = self.name + "cdef"
            params.append("CDEF:%s=%s" % (name, self.cdef))

        if self.stack:
            stack = ":STACK"
        else:
            stack = ""

        if self.stackauto and self.stackoffset:
            offset = float(self.stackoffset) * index
        else:
            offset = self.stackoffset

        if hidden:
            style = "none"
        else:
            style = self.style

        if style == "area":

            offsetline = "%s:%s#%s:" % (line, offset, linecolor)

            if self.stackoffset:
                params.append(offsetline)

            params.append("AREA:%s#%s:%s%s" % (name, areacolor, label, stack))

            if self.stack:
                if self.stackline:
                    if self.stackoffset:
                        params.append(offsetline)
                    params.append("%s:%s#%s::STACK" % (line, name, linecolor))
            else:
                params.append("%s:%s#%s:" % (line, name, linecolor))

        elif style == "line":
            params.append("%s:%s#%s:%s%s" % (line, name, linecolor, label, stack))

        return params


####################################################################
#
#   Plot
#
#   This component represents a plot. It includes a list of
#   variable components and time periods. For each period, the
#   a graph of the variables is created. The other parameters
#   decorate the graph (and will be the same for each plot).
#
####################################################################


class Plot(ConfigComponent):
    def __init__(self, plotname, parent, **kw):
        ConfigComponent.__init__(self, "plot", plotname, parent, localvars=kw)

        self.log.info("    plot: %s" % plotname)

        self.plotgroup = kw["plotgroup"]

        groupkey = "plot.%s.%s." % (self.plotgroup, plotname)
        self.lookup_stack.append(groupkey)

        for mixin in self.get_list(groupkey + "mixin")[::-1]:
            self.lookup_stack.insert(-1, mixin + ".")

        self.log.debug("    Extended lookup stack: %s" % self.lookup_stack)

        self.variables = []
        self.periods = []
        self.hidden_variables = []

        varlocal = {}
        varlocal.update(kw)
        varlocal["plot"] = plotname

        for name in self.get_list("variables", ""):
            self.variables.append(Variable(name, parent, **varlocal))

        for name in self.get_list("variables.hidden", ""):
            self.hidden_variables.append(Variable(name, parent, **varlocal))

        for name in self.get_list("periods", ""):
            self.periods.append(Period(name, parent))

        if not self.periods:
            self.log.warn("No periods defined for %s" % plotname)

        self.filename = self.get("filename", plotname)
        self.title = self.get("title", None)
        self.ymin = self.get_float("y.min", None)
        self.ymax = self.get_float("y.max", None)
        self.ylabel = self.get("y.label", None)
        self.yticks = self.get("y.ticks", None)
        self.yrigid = self.get_boolean("y.rigid", False)
        self.height = self.get_int("height", None)
        self.width = self.get_int("width", None)
        self.exponent = self.get_int("exponent", None)
        self.legend = self.get_int("legend", 1)
        self.griddash = self.get("grid.dash", "1:0")
        self.shadea = self.get("color.shadea", "FFFFFF")
        self.shadeb = self.get("color.shadeb", "FFFFFF")
        self.background = self.get("color.background", "FFFFFF")
        self.gridcolor = self.get("color.grid", "00000033")
        self.mgridcolor = self.get("color.mgrid", "00000033")
        self.textalign = self.get("textalign", "left")
        self.tz = self.get("timezone")
        self.timestart = self.get("time.start", "now")
        self.timestop = self.get("time.end", "now")
        self.logarithmic = self.get_boolean("logarithmic", False)
        self.misc = self.get("misc")

        self.log.info("options:")

        for key, value in self.optionsdict().items():
            self.log.info("  %s: %s" % (key, value))

        outputpath = os.path.dirname(self.filename)

        if not outputpath:
            outputpath = self.plotgroup
            self.filename = os.path.join(outputpath, self.filename)

        if not os.path.exists(outputpath):
            try:
                os.makedirs(outputpath)
            except:
                self.log.error("Problem creating output path: %s" % outputpath)
                raise

    def options(self, period):

        options = []

        options.append("%s-%s.png" % (self.filename, period.suffix))
        options.append("--color=SHADEA#%s" % self.shadea)
        options.append("--color=SHADEB#%s" % self.shadeb)
        options.append("--color=BACK#%s" % self.background)
        options.append("--color=GRID#%s" % self.gridcolor)
        options.append("--color=MGRID#%s" % self.mgridcolor)
        options.append("TEXTALIGN:%s" % self.textalign)

        options.append("-s %s-%s" % (self.timestart, period.span))
        options.append("-e %s" % (self.timestop))

        if period.xlabel:
            xlabel = time.strftime(period.xlabel, time.localtime())
            options.append("COMMENT:%s\c" % xlabel)

        if self.yticks:
            options.append("-y %s" % self.yticks)

        if self.logarithmic:
            options.append("--logarithmic")

        if not self.legend:
            options.append("-g")

        if not self.ylabel is None:
            options.append("-v %s" % self.ylabel)

        if not self.title is None:
            options.append("-t %s" % self.title)

        if not self.height is None:
            options.append("-h %d" % self.height)

        if not self.width is None:
            options.append("-w %d" % self.width)

        if not self.ymin is None:
            options.append("-l %f" % self.ymin)

        if not self.ymax is None:
            options.append("-u %f" % self.ymax)

        if self.yrigid:
            options.append("-r")

        if self.griddash:
            options.append("--grid-dash=%s" % self.griddash)

        if not self.exponent is None:
            options.append("--units-exponent=%d" % self.exponent)

        if period.ticks:
            options.append("--x-grid=%s" % period.ticks)

        for index, variable in enumerate(self.variables):
            options.extend(variable.options(index))

        for index, variable in enumerate(self.hidden_variables):
            options.extend(variable.options(index, hidden=True))

        if self.misc:
            options.extend(self.misc.split("\n"))

        return tuple(options)

    def create(self):

        if self.tz:
            timezone.set(self.tz)

        for period in self.periods:

            if not period.ready_to_plot():
                continue

            if self.parent.parent.is_stopped():
                break

            try:
                options = self.options(period)
                self.log.info(
                    "Plotting %s %s at %s" % (self.plotgroup, self.name, period.name)
                )
                self.log.debug("  options: %s" % options)
                rrdtool.graph(*options)
            except:
                self.log.exception(
                    "Problem creating plots for %s %s" % (self.name, period.name)
                )

            period.schedule_next_plot()

        if self.tz:
            timezone.restore()


####################################################################
#
#   PlotGroup
#
#   Orginizational structure for producing a group of plots.
#
####################################################################


class PlotGroup(ConfigComponent):
    def __init__(self, name, parent):
        kw = {"plotgroup": name}
        ConfigComponent.__init__(self, "plotgroup", name, parent, kw)

        self.log.info("  Plot group %s" % name)

        self.headers = self.get_headers("headers")

        if self.headers:
            self.log.info("    headers:")
            for header, value in self.headers.items():
                self.log.info("      %s: %s" % (header, value))

        self.log.info("    local vars:")

        self.localvars = {"plotgroup": name}

        for key, option in self.optionsdict().items():
            value = self.get(option, raw=True)
            self.localvars["plotgroup." + key] = value
            self.log.info("      %s: %s" % (key, value))

        self.plots = self.get_components("plots", Plot, **self.localvars).items()


####################################################################
#
#   PlotTool
#
#   Process client to create plots. The database will be updated
#   each time a new record shows up in the monitored news group,
#   Independently, the plots will updated at a periodic rate. If
#   no new records are received, the plots will continue to update.
#
#   It will be common that clients will inherit from this class
#   in order to interpret the message in the news group and make
#   it look like a ConfigParser object.
#
####################################################################


class PlotTool(ProcessClient):
    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poller = NewsPoller(
            self, callback=self.process, 
            idleFunc=self.create_plots
        )
        self.main = self.news_poller.main

        self.ignore_errors = self.get_boolean("ignore_errors", False)
        self.report_missing = self.get_boolean("report_missing", True)

        self.load_plots()

        if not self.plots:
            self.abort("No plots were defined")

        self.log.info("Variable set:")
        for variable in self.variables:
            self.log.info("  %s" % variable)

        # When filtering, keep digits and +-.

        self.filter_table = string.maketrans(string.printable, string.printable)
        self.filter_chars = string.letters + string.punctuation
        self.filter_chars = self.filter_chars.translate(self.filter_table, "+-.")

    def load_plots(self):

        self.log.info("Loading plot group definitions:")

        self.plotgroups = self.get_components("plotgroups", PlotGroup)

        if not self.plotgroups:
            self.plotgroups = {"": PlotGroup("", self)}

        self.headers = {}
        self.plots = []
        self.variables = set()

        for plotgroup in self.plotgroups.values():
            self.plots.extend(plotgroup.plots)
            for plot in plotgroup.plots:
                self.variables.update(plot.variables)
                self.variables.update(plot.hidden_variables)

    def create_plots(self):

        for plot in self.plots:
            plot.create()
            if self.is_stopped():
                break

    def check_headers(self, variable):

        plotgroup = self.plotgroups[variable.plotgroup]

        self.log.debug("Checking headers:")
        self.log.debug("  plotgroup.headers: %s" % plotgroup.headers)
        self.log.debug("  variable.headers:  %s" % variable.headers)
        self.log.debug("  message  headers:  %s" % self.headers)

        target_headers = {}
        target_headers.update(plotgroup.headers)
        target_headers.update(variable.headers)

        for header, pattern in target_headers.items():
            if header in self.headers:
                if not fnmatch.fnmatch(self.headers[header], pattern):
                    self.log.debug("  reject: header mismatch (%s)" % header)
                    return False
            else:
                self.log.debug("  reject: header missing (%s)" % header)
                return False

        self.log.debug("  accept: all headers match")
        return True

    def update_dateabase(self):

        self.log.info("Updating variables for %s" % self.timestamp)

        for variable in self.variables:

            if not self.check_headers(variable):
                continue

            label = "%s %s" % (variable.plotgroup, variable.name)

            try:
                value = self.get_value(variable)
                if variable.filter:
                    value = value.translate(self.filter_table, self.filter_chars)
            except:
                if self.ignore_errors:
                    if self.report_missing:
                        self.log.exception("No data found for %s" % label)
                    continue
                else:
                    self.log.error("Problem with %s" % label)
                    raise

            self.log.info("  %s = %s" % (label, value))

            try:
                variable.update(self.timestamp, value)
            except:
                self.log.exception("Problem updating %s" % label)
                if not self.ignore_errors:
                    raise

    def get_value(self, variable):
        return self.data.get(variable.section, variable.key)

    def get_timestamp(self, message):
        return newstool.message_date(message)

    def parse(self, message):

        try:
            self.data = newstool.as_config(message)
        except:
            self.log.exception("Problem parsing input")
            return False

        return True

    def process(self, message):

        # Need self.data, self.timestamp and self.headers

        if self.parse(message):
            self.timestamp = self.get_timestamp(message)
            self.headers = dict(message.items())
            self.update_dateabase()


def main():
    PlotTool(sys.argv).run()
