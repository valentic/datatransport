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
#   2023-09-06  Todd Valentic
#               list() return format is now a dictionary
#
#   2023-19-07  Todd Valentic
#               Add pprint option
#
###########################################################################

import argparse
import fnmatch
import cmd
import os
import pprint
import socket
import xmlrpc.client

socket.setdefaulttimeout(100)

VERSION=1.1

class Console(cmd.Cmd):
    """XMLRPC Console"""

    def __init__(self, args):
        cmd.Cmd.__init__(self)

        self.intro = self.make_intro()
        self.prompt = "[not connected] >>> "
        self.options = args
        self.pprint = True

        self.configdir = os.path.expanduser("~/.acorn")
        self.configfile = os.path.join(self.configdir, "history")

        if not os.path.exists(self.configdir):
            os.makedirs(self.configdir)

        self.load_history()

        self.service_cache = {}

    def connect(self, service):
        """Connect to directory"""

        url = self.directory.get(service, "url")
        return xmlrpc.client.ServerProxy(url)

    def make_intro(self):
        """Banner"""

        width = 75
        intro = []
        intro.append("")
        intro.append("-" * width)
        intro.append(f"XML-RPC Service Control Console {VERSION}".center(width))
        intro.append('Type "help" for a list commands'.center(width))
        intro.append("-" * width)
        intro.append("")

        return "\n".join(intro)

    # -- History --------------------------------------------------------

    def load_history(self):
        """Load history"""

        self.history_cache = {}
        self.history_index = 0

        if not os.path.exists(self.configfile):
            return

        with open(self.configfile, "rt", encoding="utf-8") as f:
            for entry in f:
                index, command = entry.split(":", 1)
                index = int(index)
                self.history_cache[index] = command.strip()
                self.history_index = max(self.history_index, index)

        self.trim_history()

    def save_history(self):
        """Save history"""

        with open(self.configfile, "wt", encoding="utf-8") as output:
            keys = sorted(self.history_cache)

            for index in keys:
                output.write(f"{index}: {self.history_cache[index]}")

    def trim_history(self):
        """Trim history entries"""

        cutoff = self.history_index - self.options.maxhistory + 1

        for index in list(self.history_cache.keys()):
            if index < cutoff:
                del self.history_cache[index]

    def do_clear(self, _arg):
        """clear history cache"""

        self.history_cache = {}
        self.history_index = 0
        self.save_history()

    def do_shell(self, args):
        """Run previous commands"""

        args = [int(x) for x in args.split()]
        for index in args:
            if self.onecmd(self.history_cache[index]):
                return True

        return False

    def do_history(self, _args):
        """history - print a list of commands that have been entered"""

        for index in sorted(self.history_cache):
            print(f"{index:2}: {self.history_cache[index]}")

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
        except (ConnectionRefusedError, xmlrpc.client.Error) as err:
            print(f"Error connecting to directory on {host}:{port}: {err}")
            return ""

        print(f"Connected to directory at {host}:{port}")

        self.prompt = f"[{host}:{port}] >>> "

        return self.onecmd("refresh")

    def do_refresh(self, _arg):
        """refresh -- Refresh list of services for autocompletion"""

        print("Refreshing service list ...")
        self.service_cache = {}

        try:
            services = self.directory.list()
            if isinstance(services, list):
                # Handle older format 
                for service in services: 
                    label = self.directory.get(service, "label")
                    host = self.directory.get(service, "host")
                    port = self.directory.get(service, "port")
                    self.service_cache[service] = (label, host, port)
            else:
                for service, info in services.items():
                    label = info["label"]
                    host = info["host"]
                    port = info["port"]
                    self.service_cache[service] = (label, host, port)
        except (ConnectionRefusedError, xmlrpc.client.Error) as err:
            print(f"Error connecting to server: {err}")

        print(f"Refreshed -- {len(self.service_cache)} services")

        return False

    # -- Listing ------------------------------------------------------

    def do_services(self, _arg):
        """services -- list registered services"""

        # If we do not have a cache, refresh first

        if not self.service_cache:
            self.onecmd("refresh")

        if not self.service_cache:
            print("No services are registered")
            return False

        names = sorted(self.service_cache)

        print(f"There are {len(names)} services registered:")

        width = max(len(x) for x in names)

        for name in names:
            label, host, port = self.service_cache[name]
            print(f"[{host}:{port}] {name.ljust(width)} - {label}")

        return False

    def do_list(self, arg):
        """list <service> -- list commands in a service"""

        if not arg:
            return self.onecmd("services")

        if arg not in self.service_cache:
            print("no service by that name. need to refresh?")
            return False

        try:
            service = self.connect(arg)
            commands = sorted(service.system.listMethods())
        except (ConnectionRefusedError, xmlrpc.client.Error) as err:
            print(f"problem communicating with service: {err}")
            return False

        print(f"There are {len(commands)} commands in {arg}:")

        for name in commands:
            print(f"  {name}")

        return False

    def complete_list(self, text, line, _begidx, _endidx):
        """Autocompletion handler"""

        names = self.service_cache.keys()
        prefix = line.split()[1].strip()
        matches = fnmatch.filter(names, prefix + "*")
        matches = [name.replace(prefix, text) for name in matches]

        return matches

    # -- Execute ---------------------------------------------------------

    def do_run(self, arg):
        """Run command handler"""

        arg = arg.split()

        if len(arg) < 2:
            print("Need to specify service and method names")
            return False

        try:
            service = self.connect(arg[0])
        except (ConnectionRefusedError, xmlrpc.client.Error) as err:
            print(f"Failed to connect to {arg[0]}: {err}")
            return False

        method = arg[1]
        params = arg[2:]

        func = getattr(service, method)

        try:
            output = func(*params)
        except (ConnectionRefusedError, xmlrpc.client.Error) as err:
            print(f"Problem running command: {err}")
            return False

        if self.pprint:
            pprint.pprint(output)
        else:
            print(output)

        return False

    # -- Options ---------------------------------------------------------

    def do_pprint(self, state):
        """Set pretty printing state (on | off)"""

        if state == "on":
            self.pprint = True 
        elif state == "off":
            self.pprint = False 
        else:
            print(f"pprint is {'on' if self.pprint else 'off'}")

        return False 

    # -- Control ---------------------------------------------------------

    def do_quit(self, _arg):
        """quit -- terminates the application"""
        return True

    def preloop(self):
        cmd.Cmd.preloop(self)
        self.service_cache = {}

    def postloop(self):
        cmd.Cmd.postloop(self)
        self.save_history()
        print("Exiting...")

    def precmd(self, line):
        if line and not line.startswith("!"):
            self.history_index += 1
            self.history_cache[self.history_index] = line.strip()
            self.trim_history()
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
    """Script entry point"""

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

    try:
        Console(args).cmdloop()
    except KeyboardInterrupt:
        print("")

    print("Exiting")
