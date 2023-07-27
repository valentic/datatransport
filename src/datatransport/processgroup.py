#!/usr/bin/env python
"""Process Group"""

#############################################################################
#
#   ProcessGroup
#
#   2005-04-04  Todd Valentic
#               Added ability to load extra config files.
#
#   2005-06-22  Todd Valentic
#               Changed default PATH to be /usr/local/bin:/bin:/usr/bin
#
#   2005-11-30  Todd Valentic
#               Show configuration files in debug log output.
#
#   2006-02-03  Todd Valentic
#               Code cleanups. Removed deprecated verbose. Removed
#                   unused references to grouphome.
#
#   2007-03-17  Todd Valentic
#               Use os.path.sep and pick up config files in group root dir
#
#   2008-11-12  Todd Valentic
#               Set defaults for autostart and group label. If the
#                   group was unset, it defaulted to None which wasn't
#                   passed through the XML-RPC interface.
#
#               Pass parent log to record failures before our logging
#                   is setup.
#
#   2009-05-04  Todd Valentic
#               Use path.exec config option to set default path.
#
#   2009-05-11  Todd Valentic
#               Use builtin set type
#
#   2010-01-19  Todd Valentic
#               Added priority config parameters
#
#   2016-07-10  Todd Valentic
#               Set pid to 0 on logout
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#
#   2023-07-09  Todd Valentic
#               Use TransportConfig find_config_files()
#               Use place holde {client.name} when showing config in debug 
#
#   2023-07-20  Todd Valentic
#               Change error to debug if no clients listed
#               Reduce default shutdown_timeout to 30s
#               Change shutdown_timeout to timedelta 
#
#############################################################################

import configparser
import copy
import fnmatch
import glob
import logging
import os
import sys
import time

from . import TransportConfig
from .transportlogger import create_transport_logger


class ClientInfo:
    """Process client tracker"""

    def __init__(self, name, label, group):
        self.name = name
        self.label = label
        self.pid = 0
        self.group = group

    def alive(self):
        """Check if the process is still alive"""

        if self.pid and str(self.pid) in os.listdir("/proc"):
            return True

        self.pid = 0
        return False

    def stop(self):
        """Stop the process via TERM signal"""

        try:
            os.kill(self.pid, 15)
        except (PermissionError, ProcessLookupError) as err:
            self.group.log.info("PID %d: %s", self.pid, str(err))

    def kill(self):
        """Stop the process via KILL signal"""

        try:
            os.kill(self.pid, 9)
            self.pid = 0
        except (PermissionError, ProcessLookupError) as err:
            self.group.log.info("PID %d: %s", self.pid, str(err))


class ProcessGroup:
    """Manage groups of processes"""

    def __init__(self, name, queue, parent_log):
        self.name = name
        self.clients = {}
        self.running = False
        self.log = None
        self.queue = queue
        self.parent_log = parent_log

        self.environ = None
        self.config = None
        self.configfiles = None
        self.autostart = None
        self.grouplabel = None
        self.start_priority = None
        self.stop_priority = None
        self.shutdown_timeout = None
        self.report_rate = None

        self.reload()

    def reload(self):
        """Reload configuration files"""

        config_files = self.load_config()
        self.setup_log()
        self.setup_environ()
        self.load_clients()

        self.show_config(config_files)

        return True

    def show_config(self, config_files):
        """Display configuration options to log. Used for debugging"""

        self.log.debug("Configuration files:")
        for filename in config_files:
            self.log.debug("  - %s", filename)

        self.log.debug("Configuration values:")

        for section in self.config.sections():
            self.log.debug("  [%s]", section)

            for option in self.config.options(section):
                try:
                    value = self.config.get(section, option)
                    self.log.debug("    %s: %s", option, value)
                except configparser.Error as err:
                    self.log.debug("    %s: <-- ERROR (%s)", option, str(err))

    def setup_environ(self):
        """Setup environment variables"""

        self.log.debug("Environment:")

        self.environ = copy.deepcopy(os.environ)

        path = [os.path.dirname(sys.executable)]
        path.extend(self.config.get_list("ProcessGroup", "path.exec", sep=":"))
        path.extend(self.config.get_list("ProcessGroup", "group.bin", sep=":"))
        path.extend(self.config.get_list("ProcessGroup", "path.bin", sep=":"))

        # Filter out empty strings and duplicates

        filtered_path = []
        for entry in path:
            if entry and entry not in filtered_path:
                filtered_path.append(entry)

        self.environ["PATH"] = ":".join(filtered_path)

        options = self.config.options("ProcessGroup")

        setoptions = fnmatch.filter(options, "environ.set.*")
        addoptions = fnmatch.filter(options, "environ.add.*")

        for option in setoptions:
            value = self.config.get("ProcessGroup", option)
            var = option[12:].upper()
            self.environ[var] = value
            self.log.debug("  set: %s=%s", var, value)

        for option in addoptions:
            value = self.config.get("ProcessGroup", option)
            var = option[12:].upper()
            if var in self.environ:
                # only add if not there
                if self.environ[var].find(value) == -1:
                    self.environ[var] += ":" + value
            else:
                self.environ[var] = value
            self.log.debug("  add: %s=%s", var, self.environ[var])

        for key, value in self.environ.items():
            self.log.debug("  %s = %s", key, value)

    def setup_log(self):
        """Setup logging"""

        if not self.log:
            self.log = create_transport_logger(self.config["ProcessGroup"], self.name)
            self.log.info("---------- START ----------")

        level = self.config["ProcessGroup"].get("log.level", "info")
        self.log.info("Setting log level to %s", level)

        if level == "warning":
            self.log.setLevel(logging.WARNING)
        elif level == "info":
            self.log.setLevel(logging.INFO)
        else:
            self.log.setLevel(logging.DEBUG)

    def load_config(self):
        """Load configuration"""

        defaults = {
            "client.name": "{client.name}",
            "group.name": self.name,
            "group.basename": os.path.basename(self.name),
            "group.dirname": os.path.dirname(self.name),
        }

        self.config = TransportConfig(defaults)
        basepath = self.config["TransportServer"].get_path("path.groups")
        hostname = self.config["TransportServer"].get("hostname")
        config_files = self.config.find_config_files(self.name, basepath, hostname) 

        for filename in config_files:
            self.config.read(filename)

        processgroup = self.config["ProcessGroup"]

        self.autostart = processgroup.get_boolean("autostart", False)
        self.grouplabel = processgroup.get("label", self.name)
        self.start_priority = processgroup.get_int("priority.start", 50)
        self.stop_priority = processgroup.get_int("priority.stop", 50)
        self.shutdown_timeout = processgroup.get_timedelta("shutdown.timeout", 30)
        self.report_rate = processgroup.get_int("shutdown.report.rate", 15)

        return config_files

    def load_clients(self):
        """Load clients"""

        clientlist = self.config.get_list("ProcessGroup", "clients")

        staleclients = set(self.clients).difference(clientlist)
        newclients = set(clientlist).difference(self.clients)
        curclients = set(clientlist).intersection(self.clients)

        self.log.debug("Client list: %s", clientlist)
        self.log.debug("  remove   : %s", staleclients)
        self.log.debug("  add      : %s", newclients)
        self.log.debug("  existing : %s", curclients)

        for name in staleclients:
            self.remove_client(name)

        for name in newclients:
            self.add_client(name)

        for name in curclients:
            # Only thing we update is the label
            self.clients[name].label = self.config[name].get("label", "")

    def check_client(self, name, action):
        """Check if client has been definied"""

        if name not in self.clients:
            self.log.error("Request to %s an unknown client: %s", action, name)
            raise NameError(name)

    def login(self, name, pid):
        """Login a client"""

        self.check_client(name, "login")
        self.log.info("Logging in client: %s (pid=%d)", name, pid)
        self.clients[name].pid = pid

    def logout(self, name, pid):
        """Logout a client"""

        self.check_client(name, "logout")
        self.log.info("Logging out client: %s (pid=%d)", name, pid)
        self.clients[name].pid = 0

    def find_command(self, client):
        """Check if clients command file exists"""

        name = self.config[client].get("command")

        if not name:
            self.log.error("No command defined for client: %s", client)
            return None

        paths = self.environ["PATH"].split(":")

        for path in paths:
            cmd = os.path.join(path, name)
            if os.path.isfile(cmd):
                return cmd

        self.log.error("Cannot find program in search path!")
        self.log.error("  client: %s", client)
        self.log.error("  command: %s", name)
        self.log.error("  path: %s", self.environ["PATH"])

        return None

    def start_clients(self, clientnames=None, userargs=""):
        """Start running a process group's clients"""

        self.reload()

        if not clientnames:
            try:
                clientnames = self.config["ProcessGroup"].get("clients.start")
                clientnames = clientnames.split()
            except (configparser.Error, AttributeError):
                clientnames = self.clients.keys()

        if not clientnames:
            self.log.debug("No clients listed")
            return

        clientnames = set(clientnames).intersection(self.clients)

        for clientname in clientnames:
            cmd = self.find_command(clientname)
            args = [cmd, self.name, clientname]
            args.extend(userargs.split())

            if cmd:
                self.log.info("Starting client %s", clientname)
                self.log.debug("  %s", " ".join(args))
                self.queue.put((cmd, args, self.environ))

    def stop_clients(self, names):
        """Stop the specificed clients"""

        names = set(names).intersection(self.clients)
        num_running = 0

        for name in names:
            if self.clients[name].alive():
                self.parent_log.info("Stopping client %s", name)
                self.clients[name].stop()
                num_running += 1

        timeout = time.time() + self.shutdown_timeout.total_seconds()
        report_time = time.time() + self.report_rate

        while time.time() < timeout and num_running > 0:
            time.sleep(1)
            num_running = 0
            for name in names:
                if self.clients[name].alive():
                    if time.time() > report_time:
                        pid = self.clients[name].pid
                        self.parent_log.info("  - still running: %s (%d)", name, pid)
                        report_time = time.time() + self.report_rate
                    num_running += 1

        if num_running:
            for name in names:
                if self.clients[name].alive():
                    self.parent_log.info("Killing unresponsive client %s", name)
                    self.clients[name].kill()

        return True

    def start_client(self, name, args=""):
        """Start a process client"""

        self.check_client(name, "start")
        self.start_clients([name], args)

    def stop_client(self, name):
        """Stop a process client"""

        self.check_client(name, "stop")
        return self.stop_clients([name])

    def add_client(self, name):
        """Add a new client"""

        label = self.config[name].get("label", "")
        self.clients[name] = ClientInfo(name, label, self.name)
        self.log.info("Adding client %s", name)
        return True

    def remove_client(self, name):
        """Remove a client"""

        self.check_client(name, "remove")

        if self.clients[name].alive():
            self.clients[name].stop()

        del self.clients[name]
        self.log.info("Removing client %s", name)

        return True

    def start(self):
        """Start listed clients"""
        self.start_clients()

    def stop(self):
        """Stop running clients"""
        return self.stop_clients(list(self.clients))

    def list_clients(self):
        """List available clients"""

        results = {}

        for client in self.clients.values():
            results[client.name] = (client.label, client.pid)

        return results
