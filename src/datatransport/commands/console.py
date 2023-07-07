#!/usr/bin/env python
"""Console Command"""

###########################################################################
#
#   XML-RPC Service Command Console
#
#   Run commands from an XML-RPC service.
#
#   2006-02-20  Todd Valentic
#               Initial implementation.
#
#   2007-03-11  Todd Valentic
#               Added try..except around connect in do_run()
#
#   2022-10-25  Todd Valentic
#               Python3 port
#               optparse -> argparse
#
###########################################################################

import argparse
import cmd
import os
import sys
import fnmatch
import xmlrpc.client
import traceback
import socket

socket.setdefaulttimeout(100)


class Console(cmd.Cmd):
    def __init__(self, args):
        cmd.Cmd.__init__(self)

        self.intro = self.make_intro()
        self.prompt = "[not connected] >>> "
        self.options = args

        self.configdir = os.path.expanduser("~/.acorn")
        self.configfile = os.path.join(self.configdir, "history")

        if not os.path.exists(self.configdir):
            os.makedirs(self.configdir)

        self.loadHistory()

        self.serviceCache = {} 

    def connect(self, service):
        url = self.directory.get(service, "url")
        return xmlrpc.client.ServerProxy(url)

    def make_intro(self):

        width = 75
        intro = []
        intro.append("")
        intro.append("-" * width)
        intro.append("XML-RPC Service Control Console 1.0".center(width))
        intro.append('Type "help" for a list commands'.center(width))
        intro.append("-" * width)
        intro.append("")

        return "\n".join(intro)

    # -- History --------------------------------------------------------

    def loadHistory(self):

        self.historyCache = {}
        self.historyIndex = 0

        if not os.path.exists(self.configfile):
            return

        for entry in open(self.configfile):
            index, cmd = entry.split(":", 1)
            index = int(index)
            self.historyCache[index] = cmd.strip()
            self.historyIndex = max(self.historyIndex, index)

        self.trimHistory()

    def saveHistory(self):

        with open(self.configfile, "wt") as output:

            keys = sorted(self.historyCache)

            for index in keys:
                print(f"{index}: {self.historyCache[index]}", file=output)


    def trimHistory(self):

        cutoff = self.historyIndex - self.options.maxhistory + 1

        for index in list(self.historyCache.keys()):
            if index < cutoff:
                del self.historyCache[index]

    def do_clear(self, arg):
        """clear history cache"""

        self.historyCache = {}
        self.historyIndex = 0
        self.saveHistory()

    def do_shell(self, args):
        """Run previous commands"""

        args = [int(x) for x in args.split()]
        for index in args:
            if self.onecmd(self.historyCache[index]):
                return True

        return False

    def do_history(self, args):
        """history - print a list of commands that have been entered"""

        for index in sorted(self.historyCache):
            print(f"{index:2}: {self.historyCache[index]}")

        return False

    # -- Connection ------------------------------------------------------

    def do_connect(self, arg):
        """connect [directory [port]] -- connect to directory service"""

        arg = arg.split()

        if not arg:
            host, port = self.options.host, self.options.port
        elif len(arg) == 1:
            host, port = arg[0], self.options.port
        else:
            host, port = arg

        url = f"http://{host}:{port}"
        self.directory = xmlrpc.client.ServerProxy(url)

        try:
            self.directory.ident()
            print(f"Connected to directory at {host}:{port}")
        except:
            print(f"Error connecting to directory on {host}:{port}")

        self.prompt = f"[{host}:{port}] >>> "

        return self.onecmd("refresh")

    def do_refresh(self, arg):
        """refresh -- Refresh list of services for autocompletion"""

        print("Refreshing service list ...")
        self.serviceCache = {}

        try:
            for service in self.directory.list():
                label = self.directory.get(service, "label")
                host = self.directory.get(service, "host")
                port = self.directory.get(service, "port")
                self.serviceCache[service] = (label, host, port)
        except:
            print("Error connecting to server")

        print(f"Refreshed -- {len(self.serviceCache)} services")

        return False

    # -- Listing ------------------------------------------------------

    def do_services(self, arg):
        """services -- list registered services"""

        # If we do not have a cache, refresh first

        if not self.serviceCache:
            self.onecmd("refresh")

        if not self.serviceCache:
            print("No services are registered")
            return False

        names = sorted(self.serviceCache)

        print(f"There are {len(names)} services registered:")

        width = max([len(x) for x in names])

        for name in names:
            label, host, port = self.serviceCache[name]
            print(f"[{host}:{port}] {name.ljust(width)} - {label}")

        return False

    def do_list(self, arg):
        """list <service> -- list commands in a service"""

        if not arg:
            return self.onecmd("services")

        if arg not in self.serviceCache:
            print("no service by that name. need to refresh?")
            return False

        try:
            service = self.connect(arg)
            commands = sorted(service.system.listMethods())
        except:
            print("problem communicating with service")
            return False

        print(f"There are {len(commands)} commands in {arg}:")

        width = max([len(x) for x in commands])

        for name in commands:
            print(f"  {name}")

        return False

    def complete_list(self, text, line, begidx, endidx):
        names = self.serviceCache.keys()
        prefix = line.split()[1].strip()
        matches = fnmatch.filter(names, prefix + "*")
        matches = [name.replace(prefix, text) for name in matches]
        return matches

    # -- Execute ---------------------------------------------------------

    def do_run(self, arg):

        arg = arg.split()

        if len(arg) < 2:
            print("Need to specify service and method names")
            return False

        try:
            service = self.connect(arg[0])
        except:
            print(f"Failed to connect to {arg[0]}")
            return False

        method = arg[1]
        params = arg[2:]

        func = getattr(service, method)

        try:
            print(func(*params))
        except:
            print(f"Problem running command:")
            traceback.print_exc(1)

        return False

    # -- Control ---------------------------------------------------------

    def do_quit(self, arg):
        """quit -- terminates the application"""
        return True

    def preloop(self):
        cmd.Cmd.preloop(self)
        self.serviceCache = {}

    def postloop(self):
        cmd.Cmd.postloop(self)
        self.saveHistory()
        print("Exiting...")

    def precmd(self, line):
        if line and not line.startswith("!"):
            self.historyIndex += 1
            self.historyCache[self.historyIndex] = line.strip()
            self.trimHistory()
        return line

    def emptyline(self):
        pass

    # shortcuts

    do_EOF = do_quit
    do_q = do_quit
    do_exit = do_quit
    do_h = do_history

    complete_run = complete_list


def main():

    parser = argparse.ArgumentParser(
        description="Data Transport XMLRPC Service Console"
    )

    parser.add_argument(
        "-p",
        "--port",
        default=8411,
        type=int,
        help="port (default %(default)s)",
    )

    parser.add_argument(
        "-r",
        "--host",
        default="localhost",
        help="direcotry host (default %(default)s)",
    )

    parser.add_argument(
        "-d",
        "--maxhistory",
        default=100,
        type=int,
        metavar="COUNT",
        help="maximum history depth (default %(default)s",
    )

    args = parser.parse_args()

    Console(args).cmdloop()
