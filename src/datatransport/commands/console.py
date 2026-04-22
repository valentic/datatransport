#!/usr/bin/env python
"""Console Command"""

###########################################################################
#
#   XML-RPC Service Command Console
#
#   Run commands from an XML-RPC service.
#
#   Note - history saving
#
#   There is an issue using the readline module history file with different
#   versions of Python. In particular, it is which readline backend an
#   interpreter uses. Most distribution Pythons use the GNU Readline while
#   MacOS Homebrew and uv's standalone Python releases use libedit. There is
#   an issue when the history length is truncated with set_history_length().
#   Under libedit, the saved file is missing the header and a subsequent
#   read results in an OSError [Errno 22] Invalid argument error. This can
#   also happen if the program is first run under one version of Python and
#   then run with another at a later time. The standalone python version
#   made this change starting with 3.10. This program works around this by
#   managing its own writing and reading of the history file.
#
#   readline.set_history_length results in unreadable history files
#   https://github.com/astral-sh/python-build-standalone/issues/281
#
#   readline.set_history_length corrupts history files when used in a libedit build
#   https://github.com/python/cpython/issues/121160
#
#   https://gregoryszorc.com/docs/python-build-standalone/main/quirks.html#use-of-libedit-on-linux
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
#   2026-04-20  Todd Valetnic
#               Add -V / --version
#               Add -v / --verbose
#               Change host option to be -s (was -r) for consistency
#                   with other transport programs.
#               Use rich for printing instead of pprint
#               Use standalone directory class
#               No longer need to set global socket timeout
#               Use pathlib
#               Use readline for history
#               Auto connect at start
#               Use tables in listings
#               Show method descriptions when listing a service
#
###########################################################################

import argparse
import fnmatch
import cmd
import logging
import os
from pathlib import Path
import textwrap

import xmlrpc.client
import readline

from datatransport.directory.standalone import Directory
from rich import print, box
from rich.table import Table

VERSION = "1.1.1"


class XMLRPC_Console(cmd.Cmd):
    """XMLRPC Console"""

    def __init__(self, options):
        cmd.Cmd.__init__(self)

        self.log = logging.getLogger()

        self.prompt = "[not connected] >>> "
        self.options = options
        self.directory = None
        self.service_cache = {}

        state_home = Path(os.environ.get("XDG_STATE_HOME", "~/.local/state"))
        state_home = state_home.expanduser()
        self.history_file = state_home / "transport" / "console.history"
        readline.set_auto_history(False)

        self.do_connect("")

    # -- History --------------------------------------------------------

    def do_clear(self, _arg):
        """clear history cache"""
        readline.clear_history()

    def do_shell(self, args):
        """Run previous commands with !<index>"""

        try:
            index = int(args)
        except ValueError:
            print("Error: cannot parse index")
            return False

        if index < readline.get_current_history_length():
            self.onecmd(readline.get_history_item(index))

        return False

    def do_history(self, _args):
        """Show the command history"""

        # readline history index is one-based

        for index in range(1, readline.get_current_history_length() + 1):
            print(f"{index:3}: {readline.get_history_item(index)}")

        return False

    # -- Connection ------------------------------------------------------

    def do_connect(self, arg):
        """connect [host[:port] or port] -- connect to directory service"""

        if ":" in arg:
            arg = arg.split(":")
        else:
            arg = arg.split()

        if not arg:
            host, port = self.options.host, self.options.port
        elif len(arg) == 1:
            if arg[0].isdigit():
                host, port = self.options.host, int(arg[0])
            else:
                host, port = arg[0], self.options.port
        else:
            host, port = arg

        self.directory = Directory(host=host, port=port, hold=False)

        print(f"Connecting to directory at {host}:{port}")

        self.prompt = f"[{host}:{port}] >>> "

        return self.onecmd("refresh")

    def do_refresh(self, _arg):
        """refresh -- Refresh list of services for autocompletion"""

        print("Refreshing service list ...")
        self.service_cache = {}

        try:
            services = self.directory.list()
            self.service_cache = {name: info for name, info in services.items()}
            print(f"Refreshed -- {len(self.service_cache)} services")
        except Exception as err:
            print(f"Error connecting to directory: {err}")

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

        print()
        print(f"There are {len(names)} services registered:")

        table = Table(box=box.ROUNDED)

        table.add_column("Service")
        table.add_column("Description")
        table.add_column("Source")

        for name in names:
            info = self.service_cache[name]
            label = info["label"]
            host = info["host"]
            port = str(info["port"])

            table.add_row(name, label, f"{host}:{port}")

        print(table)

        return False

    def do_list(self, arg):
        """list <service> -- list commands in a service"""

        if not arg:
            return self.onecmd("services")

        name = arg.split()[0]

        if name not in self.service_cache:
            print("Unkonwn service. Do you need to refresh?")
            return False

        try:
            service = self.directory.connect(name, hold=False)
            methods = sorted(service.system.listMethods())
            methods = [m for m in methods if not m.startswith("system.")]
            docs = {name: service.system.methodHelp(name) for name in methods}
        except (ConnectionRefusedError, xmlrpc.client.Error) as err:
            print(f"Problem communicating with service: {err}")
            return False

        print()
        print(f"There are {len(methods)} methods in the {name} service:")

        table = Table(box=box.ROUNDED, show_header=False)
        table.add_column("Method")
        table.add_column("Description")

        for name in methods:
            table.add_row(name, docs[name])

        print(table)

        return False

    def complete_list(self, text, line, _begidx, _endidx):
        """Autocompletion handler"""

        nargs = len(line.split())

        if nargs==2 and text=="": 
            match = []
        else:
            match = fnmatch.filter(self.service_cache, f"{text}*") 

        return match

    def complete_run(self, text, line, _begidx, _endidx):
        """Autocompletion handler"""

        args = line.split()
        nargs= len(args)

        if nargs==1 or (nargs==2 and text):
            matches = fnmatch.filter(self.service_cache, f"{text}*")
        else:
            service = self.directory.connect(args[1], hold=False)
            methods = service.system.listMethods()
            matches = fnmatch.filter(methods, f"{text}*")

        if len(matches)==1 and not matches[0].endswith(" "):
            matches = [matches[0]+" "]

        #print(f"{matches=}")

        return matches

    # -- Execute ---------------------------------------------------------

    def do_run(self, arg):
        """Run command handler"""

        try:
            arg = arg.split()
            service_name = arg[0]
            method_name = arg[1]
            params = arg[2:]
        except IndexError:
            print("Need to specify service and method names")
            return False

        try:
            service = self.directory.connect(service_name, hold=False)
        except Exception as err:
            print(f"Failed to connect to {service_name}: {err}")
            return False

        try:
            func = getattr(service, method_name)
            output = func(*params)
        except Exception as err:
            print(err)
            return False

        print(output)

        return False

    # -- Control ---------------------------------------------------------

    def do_quit(self, _arg):
        """quit -- terminates the application"""
        return True

    def read_history(self, filename):
        """Read the history file - work around libedit bug"""

        readline.clear_history()

        with filename.open("r", encoding="utf-8") as file:
            for line in file:
                readline.add_history(line.strip())

    def write_history(self, filename):
        """Write the hisory to file - work around libedit bug"""

        filename.parent.mkdir(parents=True, exist_ok=True)

        max_history = 10
        current_len = readline.get_current_history_length()
        start_index = max(0, current_len - max_history)

        with filename.open("w", encoding="utf-8") as file:
            for index in range(start_index, current_len):
                file.write(f"{readline.get_history_item(index + 1)}\n")

    def preloop(self):
        # Load history at startup

        if self.history_file.exists():
            self.read_history(self.history_file)

    def postloop(self):
        # Save history on exit
        self.write_history(self.history_file)

    def valid_history(self, line):
        """Valid line to save in history file"""

        if not line:
            return False

        if line.startswith("!"):
            return False

        if line in ["h", "history", "help", "EOF"]:
            return False

        history_len = readline.get_current_history_length()
        if history_len:
            if line == readline.get_history_item(history_len):
                return False

        return True

    def precmd(self, line):
        line = line.strip()
        if self.valid_history(line):
            readline.add_history(line)
        return line

    def emptyline(self):
        pass

    # shortcuts

    do_EOF = do_quit
    do_q = do_quit
    do_exit = do_quit
    do_h = do_history

    #complete_run = complete_list


# -------------------------------------------------------------------------
# Main application
# -------------------------------------------------------------------------


def parse_command_line():
    """Parse command line arguments"""

    desc = f"Data Transport XMLRPC Service Console {VERSION}"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument(
        "-s",
        "--host",
        default="localhost",
        help="direcotry host (%(default)s)",
    )

    parser.add_argument(
        "-p",
        "--port",
        default=8411,
        type=int,
        help="port (%(default)s)",
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-V", "--version", action="version", version=VERSION)

    options = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    return options


def show_banner():
    """Banner"""

    title = f"XML-RPC Service Console {VERSION}"

    width = 75
    print(textwrap.dedent(f"""
        {"":->{width}}
        {title:^{width}}
        {'Type "help" for a list commands, "exit" when done.':^{width}}
        {"":->{width}}
    """
    ))

def main():
    """Script entry point"""

    show_banner()

    options = parse_command_line()
    console = XMLRPC_Console(options)

    print()

    while True:
        try:
            console.cmdloop()
            break
        except KeyboardInterrupt:
            print()

    print()
    print("Exiting")
