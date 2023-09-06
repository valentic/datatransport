#!/usr/bin/env python3
"""Transport command line interface"""

############################################################################
#
#   transportctl
#
#   This script controls the transport server from the command line.
#
#   History:
#
#   1.0.0   1999.??.??  TAV
#           Initial implementation
#
#   1.2.0   2000.04.20  TAV
#           Updated to use omniORB for CORBA functions.
#
#   1.3.0   2000-06-22  TAV
#           Added ability to change options for the web-site users.
#
#   1.3.1   2000-08-08  TAV
#           Fixed bug if no option given on command line, call help.
#
#   1.3.2   2001-08-29  TAV
#           Handle new list of config files in the ProcessGroupInfo struct.
#
#   1.3.3   2001-10-23  TAV
#           Fixed a bug in the "user set" command. The user's values were
#               being reset to the defaults with each change.
#
#   1.3.4   2002-02-11  Todd Valentic
#           Added ability to pass args to start client command.
#
#   1.3.5   2002-08-28  Todd Valentic
#           Setup via configure script
#           sri.transport -> Transport
#           Removed web-site user functions.
#
#   1.3.6   2004-08-16  Todd Valentic
#           Cleanup for XML-RPC.
#           Removed log rotation.
#           Removed TransportClient.
#
#   2016-12-23  Todd Valentic
#               Migrate to datatransport package format
#
#   2020-10-09  Todd Valentic
#               Python3: xmlrpc.client
#               Python3: print
#
#   2023-08-17  Todd Valentic
#               Improve error checking
#               PEP8 compliance
#
#   2023-08-29  Todd Valentic
#               Missing f-string in list clients
#
############################################################################

import json
import os
import shutil
import subprocess
import sys
import time
import xmlrpc.client

from pathlib import Path

from datatransport import TransportConfig


class TransportControl:
    """Transport Control client"""

    def __init__(self):
        self.command = {
            "help": self.help,
            "list": self.list,
            "status": self.show_status,
            "cleanup": self.cleanup,
            "reload": self.reload,
            "add": self.add_group,
            "remove": self.remove_group,
            "restart": self.restart,
            "start": self.start,
            "stop": self.stop,
            "server": self.server_control,
        }

    def help(self):
        """Show help message"""

        print()
        print("-" * 70)
        print("Transport Control Commands:")
        print("-" * 70)
        print("\thelp                     - Show this page")
        print("\tstatus                   - Transport server status")
        print("\tloglevel                 - Set log level on group or server")
        print("\treload <group>           - Reload group's config file")
        print("\treload server            - Reload process groups")
        print("\tlist                     - List all process groups")
        print("\tlist <group>             - List clients in a group")
        print("\tstart <group>            - Start a process group")
        print("\tstop <group>             - Stop a process group")
        print("\trestart <group>          - Stop/start a process group")
        print("\tadd <group>              - Notify server of new group")
        print("\tremove <group>           - Remove a group from the server")
        print("\tserver start             - Start the transport server")
        print("\tserver stop              - Stop the transport server")
        print("\tstart <group> <client>   - Start the client in group")
        print("\tstop <group> <client>    - Stop the client in group")
        print("\tcleanup                  - Remove processes after crash")
        print("-" * 70)
        print()

    def run_command(self, argv):
        """Run command"""

        if len(argv) < 2:
            self.help()
            sys.exit(1)

        cmd = argv[1]
        arg = argv[2:]

        if cmd not in self.command:
            print("Unknown command:", cmd)
            self.help()
            return 1

        if cmd == "cleanup":
            self.cleanup()
            return 0

        if cmd == "help":
            self.help()
            return 0

        url = TransportConfig().get("TransportServer", "url")
        self.server = xmlrpc.client.ServerProxy(url)

        if cmd != "server":
            # Skip if we need to start the server

            try:
                self.status = self.server.status()
            except (ConnectionRefusedError, xmlrpc.client.Error) as err:
                print(f"Cannot connect to the transport server: {err}")
                return 1

        return self.command[cmd](arg)

    def has_group_or_exit(self, group):
        """Exit if group does not exist"""

        try:
            groups = self.server.listgroups()
        except xmlrpc.client.Error as err:
            print(f"Problem getting group list: {err}")
            sys.exit(1)

        if group in groups:
            return

        print(f'The process group "{group}" does not exist')
        print('  Use the "list" command to print the available groups')

        sys.exit(1)

    def has_client_or_exit(self, group, client):
        """Exit if group or client do not exist"""

        self.has_group_or_exit(group)

        clients = self.server.listclients(group)

        if client in clients:
            return

        print(f'The client "{client}" does not exist in {group}')
        print('  Use the "list" command to print the available clients')

        sys.exit(1)

    def show_status(self, _arg):
        """Show server status"""

        print("Server status:")
        print(json.dumps(self.status, sort_keys=True, indent=4))

        return 0

    def reload(self, arg):
        """Reload a process group or server"""

        if not arg:
            print('You need to specify a process group or "server"')
            return 1

        if arg[0] == "server":
            self.server.reloadgroups()
            return 0

        group = arg[0]

        self.has_group_or_exit(group)

        try:
            self.server.reloadgroup(group)
        except xmlrpc.client.Error as err:
            print(f"Problem reloading group: {err}")
            return 1

        return 0

    def add_group(self, arg):
        """Add a process group"""

        if len(arg) == 0:
            print("You need to specify a process group")
            return 1

        name = arg[0]

        try:
            self.server.addgroup(name)
        except xmlrpc.client.Error as err:
            print(f"Problem adding the group: {err}")
            return 1

        return 0

    def remove_group(self, arg):
        """Remove a group"""

        if not arg:
            print("You need to specify a process group")
            return 1

        name = arg[0]

        self.has_group_or_exit(name)

        try:
            self.server.removegroup(arg[0])
        except xmlrpc.client.Error as err:
            print(f"Problem removing the group: {err}")
            return 1

        return 0

    def list(self, arg):
        """List groups or the clients of a group"""

        if len(arg) == 1:
            return self.list_clients(arg[0])

        return self.list_groups()

    def list_clients(self, group):
        """List clients in a group"""

        self.has_group_or_exit(group)

        clients = self.server.listclients(group)
        print(f"There are {len(clients)} clients listed for the group {group}")
        for client, info in clients.items():
            print(client, info)
        return 0

    def list_groups(self):
        """List groups"""

        groups = self.server.listgroups()

        if not groups:
            print("No process groups are registered")
            return 0

        width = max(len(group) for group in groups)

        for group, label in groups.items():
            print(f"{group:{width}} - {label}")

        return 0

    def start_client(self, group, client, args):
        """Start a client"""

        self.has_client_or_exit(group, client)

        try:
            self.server.startclient(group, client, args)
        except xmlrpc.client.Error as err:
            print(f"Problem starting client: {err}")
            return 1

        return 0

    def stop_client(self, group, client):
        """Stop a client"""

        self.has_client_or_exit(group, client)

        try:
            self.server.stopclient(group, client)
        except xmlrpc.client.Error as err:
            print(f"Problem stopping client: {err}")
            return 1

        return 0

    def start_server(self):
        """Start the server daemon"""

        args = [shutil.which("transportd"), "-b"]

        # Long running process, can't use with, so disable warning
        # pylint: disable=consider-using-with

        subprocess.Popen(args)

    def stop_server(self):
        """Stop the server daemon"""

        try:
            self.server.stop()
            time.sleep(1)
        except ConnectionRefusedError:
            pass

        return 0

    def server_control(self, arg):
        """Control server daemon"""

        if len(arg) == 0:
            print("Specify start, stop or restart")
            return 1

        cmd = arg[0]

        if cmd == "start":
            return self.start_server()

        if cmd == "stop":
            return self.stop_server()

        if cmd == "restart":
            self.stop_server()
            return self.start_server()

        print(f"Unknown server command: {cmd}")

        return 1

    def start(self, arg):
        """Start a client or group"""

        if len(arg) == 0:
            print("You need to specify a group or client name ")
            return 1

        if len(arg) > 1:
            if len(arg) == 3:
                args = arg[2]
            else:
                args = ""
            return self.start_client(arg[0], arg[1], args)

        group = arg[0]

        try:
            self.server.startgroup(group)
        except xmlrpc.client.Error as err:
            print(f"Problem starting group: {err}")
            return 1

        print(f"Group started: {group}")

        return 0

    def stop(self, arg):
        """Stop client, group or server"""

        if not arg:
            print("You need to provide a group or client name")
            return 1

        if len(arg) == 2:
            group, client = arg
            return self.stop_client(group, client)

        group = arg[0]

        self.has_group_or_exit(group)

        try:
            self.server.stopgroup(group)
        except xmlrpc.client.Error as err:
            print(f"Porblem stopping group: {err}")
            return 1

        print(f"Group stopped: {group}")

        return 0

    def restart(self, arg):
        """Restart client or group"""

        self.stop(arg)
        self.start(arg)

    def cleanup(self):
        """Stop any transport clients"""

        uid = TransportConfig().uid

        for path in Path("/proc").glob("*"):
            if not path.name.isnumeric():
                continue

            statusfile = path.joinpath("status")

            data = {}

            with statusfile.open("r", encoding="utf=8") as f:
                for line in f.readlines():
                    key, value = line.split(":")
                    data[key] = value.strip()

            if uid != int(data["Uid"].split()[0]):
                continue

            pid = int(data["Pid"])

            print(f"Stopping {pid}: ", end=" ")
            try:
                os.kill(pid, 9)
                print("OK")
            except OSError as err:
                print(f"Error: {err}")

        print("Finished")

        return 0


def main():
    """Script entry point"""

    try:
        control = TransportControl()
        sys.exit(control.run_command(sys.argv))
    except KeyboardInterrupt:
        print("*** BREAK ***")
        sys.exit(1)
