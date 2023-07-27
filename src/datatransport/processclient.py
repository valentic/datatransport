#!/usr/bin/env/python
"""ProcessClient"""

###########################################################################
#
#    ProcessClient
#
#    A base class for client programs of a process group.
#
#    History:
#
#    1.0.0  1999.??.??  TAV
#           Initial implementation.
#
#    1.2.0  2000.04.18  TAV
#           Migration of CORBA from Fnorb to omniORB.
#
#    1.2.1  2001-09-07  TAV
#           setStatus() -> setStatusCode()
#
#    1.2.2  2001-12-10  TAV
#           Added running data member here for general use.
#           Modified abort() to respect running and exit if stopped.
#
#    1.2.3  2001-12-26  TAV
#           Changed tav -> sri
#
#    1.2.4  2002-01-23  Todd Valentic
#           Added traceback() method to help in error reporting.
#           Added wait() method.
#           Added signal handling.
#
#    1.2.5  2002-08-28  Todd Valentic
#           sri.transport -> Transport
#
#    1.2.6  2002-12-19  Todd Valentic
#           Reworked the environment variable processing to mirror
#             that of the process group (.set and .add options).
#
#    1.2.7  2003-02-06  Todd Valentic
#           Added return value to wait (1=ok, 0=not running).
#
#    1.2.8  2003-06-11  Todd Valentic
#           Added createCallback method so other classes can use a
#             common system for plugins.
#
#    1.2.9  2003-06-20  Todd Valentic
#           Added default to createCallback.
#           Added createDeltaTime method.
#           Convert pollrate to int in wait - this lets us pass in
#            a DeltaDateTime object.
#
#    1.2.10 2003-06-27  Todd Valentic
#           Code cleanup. Renamed "datapath" to "workingdir".
#           Changed default values on abort.
#
#    1.2.11 2003-08-14  Todd Valentic
#           Changed createCallback and createDeltaTime to be mixin
#             classes and changed name to getCallback and
#             getDeltaTime to match consistency with other get*
#             methods.
#
#    1.2.12 2003-11-21  Todd Valentic
#           Fixed bug in wait() when sync enabled (pollrate needed to
#             converted to an int - see 1.2.9).
#
#    1.2.13 2003-12-23  Todd Valentic
#           Make sure to convert offset to int in wait() in case it
#             is a DateTime object.
#
#    1.2.14 2004-02-08  Todd Valentic
#           Removed unused imports (socket,CosNaming,DateTime)
#
#   2.0.0   2004-08-08  Todd Valentic
#           Converted to XML-RPC.
#           Major code cleanup.
#
#   2.0.1   2004-12-27  Todd Valentic
#           Convert from mx.DateTime to datetime
#           Added client.name to config options
#
#   2.0.2   2005-04-04  Todd Valentic
#           Added multiple conf files.
#
#   2.0.3   2005-04-10  Todd Valentic
#           Added is_running() and is_stopped() methods
#
#   2.0.4   2005-04-17  Todd Valentic
#           Added put() method for adding to config space.
#
#   2.0.5   2005-06-22  Todd Valentic
#           Changed default PATH to be /usr/local/bin:/bin:/usr/bin
#               This better matches the default shell version.
#
#   2.0.6   2005-11-12  Todd Valentic
#           Pass through keywords in get*() methods.
#
#   2.0.7   2005-11-30  Todd Valentic
#           Show configuration file names in debug log output.
#
#   2.0.8   2006-01-18  Todd Valentic
#           Added exit() command to compliment abort().
#
#   2.0.9   2006-02-03  Todd Valentic
#           Start each client in group.work instead of group.home.
#               This move separates the config files from the local
#               runtime generated files. Makes distributing groups
#               much easier.
#
#   2.0.10  2006-10-25  Todd Valentic
#           Added sleep parameter to wait(). This lets alternative
#               methods be used besides time.sleep(). In particular
#               this is used by threads who need Event.wait().
#
#   2.0.11  2006-10-26  Todd Valentic
#           Added currentTime() and utc() methods.
#
#   2.0.12  2007-03-17  Todd Valentic
#           Use os.path.sep
#           Make sure to read config files in path.group
#
#   2.0.13  2009-05-03  Todd Valentic
#           Added path.exec config option
#
#   2.0.14  2010-05-25  Todd Valentic
#           Because stop() now blocks, we cannot issue logout() in the
#               signal handler. Not really needed anymore.
#
#   2.0.15  2010-08-16  Todd Valentic
#           Add support to wait() for the ConfigMixin.Rate object.
#
#   2016-07-10  Todd Valentic
#               Use atexit to call logoutclient()
#
#   2016-12-23  Todd Valentic
#               Use datetime.timezone.utc for UTC
#
#   2020-01-08  Todd Valentic
#               Add atStart support to wait()
#
#   2020-10-09  Todd Valentic
#               Python3: xmlrpc.client
#               Drop datefunc (replace with new standard methods)
#
#   2021-07-13  Todd Valentic
#               Add show_thread option for logging
#
#   2022-10-07  Todd Valentic
#               Fix wait()
#                   Signal handling changed in Python 3.5 to that
#                   sleep.time() isn't interrupted. We had relied on
#                   the interrupt to exit on demand. Rework to use
#                   threading.Event(). For details, see:
#
#                   "break-interrupt-a-time-sleep-in-python"
#                       https://stackoverflow.com/a/46346184
#
#                   https://peps.python.org/pep-0475/
#
#               Make running a property
#               Convert API to snake case naming
#                   CurrentTime -> current_time
#
#   2023-07-09  Todd Valentic
#               Use TransportConfig find_config_files()
#
#   2023-07-25  Todd Valentic
#               Add set() and options() to config proxy
#               Do not map getters from config, use config object               
#               current_time() renamed to now()
#
###########################################################################

import atexit
import datetime
import fnmatch
import glob
import logging
import os
import signal
import sys
import threading
import time
import xmlrpc.client

from functools import partial
from logging.handlers import RotatingFileHandler
from logging.handlers import SocketHandler

import sapphire_config as sapphire

from . import Root
from . import TransportConfig

# For the get methods forwarded to the config
# pylint: disable=no-member


class ProcessClient(Root):
    """ProcessClient"""

    def __init__(self, argv):
        self.groupname = argv[1]
        self.name = argv[2]
        self.utc = datetime.timezone.utc
        self.subprocs = set()
        self.started_rates = {}
        self.exit_event = threading.Event()
        config_files = self.load_config()

        url = self.config.parser.get("TransportServer", "url")
        self.server = xmlrpc.client.ServerProxy(url)

        self.setup_signals()
        self.setup_log()
        self.setup_environment()
        self.setup_working_dir()

        self.server.loginclient(self.groupname, self.name, os.getpid())

        self.log.debug("Configuration files:")
        for filename in config_files:
            self.log.debug("  - %s", filename)

        atexit.register(self.on_exit)

    @property
    def running(self):
        """Indictate if process should continue running"""
        return not self.exit_event.is_set()

    def on_exit(self):
        """Called when process exits"""
        if not self.is_running():
            self.server.logoutclient(self.groupname, self.name, os.getpid())

    def setup_signals(self):
        """Setup signal handlers"""

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGHUP, self.signal_handler)

        # Restore the normal child signal handling. The TransportServer
        # overrides this signal to ignore child process return codes
        # preventing zombie (defunct) processes. However, this also
        # has the effect of preventing the commands.* methods from
        # working as expected. Restoring the default behaviour returns
        # things to normal.

        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

    def signal_handler(self, signum, _frame):
        """Handle signal even, exit if requested"""

        if self.is_running():
            self.exit_event.set()
            self.log.info("Exit request")

            for proc in self.subprocs:
                if proc.poll() is None:
                    proc.send_signal(signum)

    def _setup_log_socket_handler(self, formatter):
        """Add a socket log handler"""

        host = self.config.get("log.socket.host", fallback="localhost")
        port = self.config.get_int("log.socket.port", fallback=9020)

        socket_handler = SocketHandler(host, port)
        socket_handler.setFormatter(formatter)

        return socket_handler

    def _setup_log_file_handler(self, formatter):
        """Add a rotating file log handler"""

        filename = self.config.get("log.file")
        maxbytes = self.config.get_bytes("log.maxbytes", fallback="100kb")
        backup_count = self.config.get_int("log.backupcount", fallback=3)

        rotating_handler = RotatingFileHandler(filename, "a", maxbytes, backup_count)
        rotating_handler.setFormatter(formatter)

        return rotating_handler

    def setup_log_formatter(self):
        """Initialize a log formatter"""

        msgfmt = "[%(asctime)s.%(msecs)03d %(levelname)7s] %(name)s"

        if self.config.get_boolean("log.showthread", fallback=False):
            msgfmt += " [%(threadName)s]"

        msgfmt = msgfmt + ": %(message)s"

        datefmt = "%Y-%m-%d %H:%M:%S"

        return logging.Formatter(msgfmt, datefmt)

    def setup_log(self):
        """Setup log handlers"""

        level = self.config.get("log.level", "info")
        formatter = self.setup_log_formatter()

        root_logger = logging.getLogger("")
        self.log = logging.getLogger(f"{self.groupname}/{self.name}")

        if self.config.get_boolean("log.file.enable", True):
            root_logger.addHandler(self._setup_log_file_handler(formatter))

        if self.config.get_boolean("log.socket.enable", True):
            root_logger.addHandler(self._setup_log_socket_handler(formatter))

        if level == "warning":
            root_logger.setLevel(logging.WARNING)
        elif level == "info":
            root_logger.setLevel(logging.INFO)
        else:
            root_logger.setLevel(logging.DEBUG)

    def load_config(self):
        """Load the configuration files"""

        defaults = {
            "client.name": self.name,
            "group.name": self.groupname,
            "group.basename": os.path.basename(self.groupname),
            "group.dirname": os.path.dirname(self.groupname),
        }

        config = TransportConfig(defaults)
        basepath = config["TransportServer"].get_path("path.groups")
        hostname = config["TransportServer"].get("hostname")
        config_files = config.find_config_files(self.groupname, basepath, hostname)

        # Read one at a time so we know if one has an error

        for filename in config_files:
            config.read(filename)

        self.config = config[self.name]
        self.config.set = self.config.__setitem__
        self.config.options = self.config._options
        self.config.get_components = partial(self.config.get_components, parent=self)

        self.hostname = config.get("DEFAULT", "hostname")

        return config_files

    def setup_environment(self):
        """Setup up environment variables"""

        self.log.debug("Setting environment variables:")

        os.environ["PATH"] = self.config.get("path.exec", "/usr/local/bin:/bin:/usr/bin")
        os.environ["PATH"] += ":" + self.config.get("group.bin")
        os.environ["PATH"] += ":" + self.config.get("path.bin")

        options = self.config.options()

        setoptions = fnmatch.filter(options, "environ.set.*")
        addoptions = fnmatch.filter(options, "environ.add.*")

        for option in setoptions:
            value = self.config.get(option)
            var = option.split(".")[2].upper()
            os.environ[var] = value
            self.log.debug("  set: [%s] = %s", var, value)

        for option in addoptions:
            value = self.config.get(option)
            var = option.split(".")[2].upper()
            if var in os.environ:
                # only add if not there
                if os.environ[var].find(value) == -1:
                    os.environ[var] += ":" + value
            else:
                os.environ[var] = value
            self.log.debug("  add: [%s] %s", var, value)

        keys = sorted(os.environ.keys())

        self.log.debug("Current environment:")

        for key in keys:
            self.log.debug("  [%s] = %s", key, os.environ[key])

    def setup_working_dir(self):
        """Change to working directory"""

        workingdir = os.path.join(self.config.get("group.work"), self.name)

        if not os.path.exists(workingdir):
            os.makedirs(workingdir)

        os.chdir(workingdir)

    def abort(self, msg="Exiting", status=1):
        """Exit process with error"""
        self.log.error(msg)
        self.exit_event.set()
        sys.exit(status)

    def exit(self, msg="Exiting", status=0):
        """Exit process"""
        self.log.info(msg)
        self.exit_event.set()
        sys.exit(status)

    def stop(self):
        """Request to stop"""
        self.exit_event.set()

    def is_running(self):
        """Indicate the process is running"""
        return self.running

    def is_stopped(self):
        """Indicate the processes has stopped"""
        return not self.running

    def now(self):
        """Return current time as datetime with UTC timezone"""
        return datetime.datetime.now(self.utc)

    def wait(self, pollrate, offset=None, sync=False):
        """Wait for a given time, short circuit if we have stopped running"""

        if not self.running:
            return 0

        if isinstance(pollrate, sapphire.Rate):
            period = pollrate.period
            sync = pollrate.sync
            offset = pollrate.offset

            # Short circuit first time if at_start is set

            if pollrate.at_start:
                pollrate.at_start = False
                return self.running
        else:
            period = pollrate

        if isinstance(period, datetime.timedelta):
            secs = period.total_seconds()
        else:
            secs = int(period)

        if offset is None:
            offset_secs = 0
        elif isinstance(offset, datetime.timedelta):
            offset_secs = offset.total_seconds()
        else:
            offset_secs = float(offset)

        if sync:
            curtime = time.time() - offset_secs
            waittime = max(0, secs - curtime % secs + 0.000)
        else:
            waittime = secs

        self.exit_event.wait(waittime)

        return self.is_running()

    def main(self):
        """Main application"""

    def run(self):
        """Run main application, capture any errors to log"""
        try:
            self.init()
        except:  # pylint: disable=bare-except
            self.log.exception("Problem detected in init")
            self.abort()

        try:
            self.main()
        except:  # pylint: disable=bare-except
            self.log.exception("Problem detected in main")
            return  # No clean exit so the watchdog will restart us

        self.exit()
