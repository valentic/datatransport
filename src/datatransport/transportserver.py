#!/usr/bin/env python
"""Transport Server"""

##########################################################################
#
#   Transport Server
#
#   2005-11-08  Todd Valentic
#               Only list process groups with clients in listgroups().
#
#   2006-09-15  Todd Valentic
#               Check if process is alive in expire().
#
#   2007-03-11  Todd Valentic
#               Added ident() method to API to make callable from
#                   directory services.
#               Register introspection services.
#
#   2008-11-10  Todd Valentic
#               Pass sever log file to process groups to record any
#                   initial failures.
#
#   2009-05-11  Todd Valentic
#               Since we now require Python 2.4 or greater, we don't
#                   need to import the sets module anymore.
#
#   2010-01-19  Todd Valentic
#               Add group priority start/stop
#
#   2010-01-25  Todd Valentic
#               Rework stopping groups. Stop the clients in each group
#                   and wait until they are stopped before continuing on.
#                   One significant change is that stop() will block.
#
#   2010-05-07  Todd Valentic
#               Make sure to return value in addgroup()
#
#   2016-07-10  Todd Valentic
#               Make a threaded server - note that there are no saftey
#                   checks for concurent access! Made this change to
#                   allow clients to log out (otherwise stop blocked).
#
#   2016-11-08  Todd Valentic
#               Make try..finally compatible with python 2.4
#
#   2023-10-07  Todd Valentic
#               Reorder imports
#               Python3: xmlrpc.server
#               Python3: socketserver
#               Use new get_* methods
#
##########################################################################

import os
import pathlib
import resource

from threading import Thread
from socketserver import ThreadingMixIn
from xmlrpc.server import SimpleXMLRPCServer

from .transportlogger import create_transport_logger
from . import ProcessGroup
from . import TransportConfig

# pylint: disable=too-many-public-methods


class TransportServer(Thread, ThreadingMixIn, SimpleXMLRPCServer):
    """Transport Server"""

    def __init__(self, queue):
        Thread.__init__(self)
        self.daemon = True

        self.config = TransportConfig()["TransportServer"]
        self.log = create_transport_logger(self.config, "TransportServer")
        self.autostart = self.config.get_boolean("autostart", False)

        port = self.config.get_int("port", 8081)
        self.allow_reuse_address = 1
        self.request_queue_size = 100
        SimpleXMLRPCServer.__init__(self, ("", port), logRequests=False)
        self.socket.settimeout(1)
        self.timeout = 1

        self.setup_xmlrpc()
        self.setup_environ()

        self.queue = queue
        self.running = True

        self.groups = {}
        self.pidlist = {}

        self.log.info("---------- START ----------")

        self.loadgroups()

    def setup_xmlrpc(self):
        """Setup XMLRPC API"""

        self.register_introspection_functions()

        self.register_function(self.my_ident, "ident")
        self.register_function(self.status)
        self.register_function(self.stop)

        self.register_function(self.listgroups)
        self.register_function(self.reloadgroups)

        self.register_function(self.addgroup)
        self.register_function(self.removegroup)
        self.register_function(self.startgroup)
        self.register_function(self.stopgroup)
        self.register_function(self.reloadgroup)

        self.register_function(self.startclient)
        self.register_function(self.stopclient)
        self.register_function(self.listclients)
        self.register_function(self.loginclient)
        self.register_function(self.logoutclient)

    def setup_environ(self):
        """Run process groups in a controlled, pristine environment"""

        keep = ["PYTHONPATH", "PATH", "DATA_TRANSPORT_PATH"]

        environ = {}

        for key, value in os.environ.items():
            if key in keep:
                environ[key] = value

        environ["HOME"] = self.config.get("path.base")

        os.environ = environ

    def my_ident(self):
        """Return ID string"""

        return "Data transport server"

    def checkgroup(self, name, action):
        """Check if process group exists"""

        if name not in self.groups:
            self.log.error("Request to %s unknown group: %s", action, name)
            raise NameError(name)

    def findgroups(self, path):
        """Find all process groups in the file heirarchy"""

        groups = []

        for root, _dirs, files in os.walk(path, followlinks=True):
            configname = os.path.basename(root) + ".conf"
            if configname in files:
                groups.append(root.replace(path, "", 1)[1:])

        return groups

    def loadgroups(self):
        """Load group from config file"""

        path = self.config.get("path.groups")
        grouplist = self.findgroups(path)

        stalegroups = set(self.groups).difference(grouplist)
        newgroups = set(grouplist).difference(self.groups)
        curgroups = set(grouplist).intersection(self.groups)

        self.stopgroups(stalegroups)

        for name in stalegroups:
            del self.groups[name]

        for name in newgroups:
            self.creategroup(name)

        if self.autostart:
            # filter out new groups that failed being created
            self.startgroups(newgroups.intersection(self.groups))

        for name in curgroups:
            self.reloadgroup(name)

    def stopgroups(self, names):
        """Stop process groups according to priority"""

        priority_list = []

        for name in names:
            group = self.groups[name]
            priority_list.append((group.stop_priority, name))

        for _level, name in sorted(priority_list):
            self.stopgroup(name)

    def startgroups(self, names):
        """Start process groups according to priority"""

        priority_list = []

        for name in names:
            group = self.groups[name]
            if group.autostart:
                priority_list.append((group.start_priority, name))

        for _level, name in sorted(priority_list):
            self.startgroup(name)

    def removegroup(self, name):
        """Remove a process group"""

        self.checkgroup(name, "remove")

        self.log.info("Removing %s", name)
        self.groups[name].stop()
        del self.groups[name]

        return True

    def creategroup(self, name):
        """Create a new process group"""

        basedir = self.config.get("path.groups")

        if not os.path.isdir(os.path.join(basedir, name)):
            self.log.error("Request to add unknown process group: %s", name)
            raise NameError

        if name in self.groups:
            self.log.error("Cannot add group, already exists: %s", name)
            return False

        try:
            self.groups[name] = ProcessGroup(name, self.queue, self.log)
            self.log.info("Adding %s", name)
        except BaseException:  # pylint: disable=broad-except
            self.log.exception("Problem loading %s", name)
            return False

        return True

    def addgroup(self, name):
        """Add a process group (create, start)"""

        self.creategroup(name)
        self.startgroup(name)
        return True

    def reloadgroup(self, name):
        """Reload process group configuration"""

        self.checkgroup(name, "reload")
        self.log.info("Reloading %s", name)
        self.groups[name].reload()
        return True

    def reloadgroups(self):
        """Reload all process group configurations"""

        self.config = TransportConfig()["TransportServer"]
        self.loadgroups()
        return True

    def startgroup(self, name):
        """Start a process group running"""

        self.checkgroup(name, "start")
        group = self.groups[name]
        self.log.info("Starting [%d] %s", group.start_priority, name)
        group.start()
        return True

    def stopgroup(self, name):
        """Stop a process group"""

        self.checkgroup(name, "stop")
        group = self.groups[name]
        self.log.info("Stopping [%2d] %s", group.stop_priority, name)
        return group.stop()

    def listgroups(self):
        """List process groups"""

        results = {}

        for name, group in self.groups.items():
            if group.list_clients():
                results[name] = group.grouplabel

        return results

    def startclient(self, group, client, args=""):
        """Start a process group client"""

        self.checkgroup(group, "start client")
        self.groups[group].start_client(client, args)
        return True

    def stopclient(self, group, client):
        """Stop a process group client"""

        self.checkgroup(group, "stop client")
        self.groups[group].stop_client(client)
        return True

    def loginclient(self, group, client, pid):
        """Login a running client"""

        self.checkgroup(group, "login client")
        self.groups[group].login(client, pid)
        return True

    def logoutclient(self, group, client, pid):
        """Logout a client"""

        self.checkgroup(group, "logout client")
        self.groups[group].logout(client, pid)

        if pid in self.pidlist:
            del self.pidlist[pid]

        return True

    def listclients(self, group):
        """List all of the clients in a process group"""

        self.checkgroup(group, "listclients")
        return self.groups[group].list_clients()

    def stop(self):
        """Stop the server"""

        self.stopgroups(self.groups.keys())
        self.running = False
        return True

    def status(self):
        """Indicate we are alive"""

        pid = os.getpid()
        proc = pathlib.Path('/proc', str(pid), 'fd')
        numfiles = len(list(proc.iterdir()))
        numclients = sum(len(g.clients) for g in self.groups.values())
        numrunning = 0

        for group in self.groups.values():
            for client in group.clients.values():
                if client.pid:
                    numrunning += 1

        statm = pathlib.Path('/proc', str(pid), 'statm')
        vmrss = int(statm.read_text("UTF-8").split()[1])
        memusage = vmrss * resource.getpagesize()

        results = {}
        results["pid"] = os.getpid()
        results["open_files"] = numfiles
        results["memory"] = memusage
        results["groups"] = len(self.groups)
        results["clients"] = numclients
        results["running"] = numrunning

        return results

    def run(self):
        """Main loop"""

        self.log.info("Starting server thread")

        try:
            self.serve_forever()
        except BaseException as err:  # pylint: disable=broad-except
            self.log.exception("Problem: (%s) %s", type(err), str(err))
        finally:
            self.server_close()

        self.log.info("========== STOP  ==========")
