#!/usr/bin/env python
"""List running transport processes"""

##########################################################################
#
#   List running transport processes
#
#   2020-10-26  Todd Valentic
#               Initial implementation. Based on original transportps
#
##########################################################################

from pathlib import Path


def find_server(name):
    """Find data transport server process ID"""
    for pid in Path("/proc").iterdir():
        if pid.name.isdigit():
            comm = pid.joinpath("comm").read_text().strip()
            if comm == name:
                return pid

    return None


def list_processes():
    """Show data transport processes"""

    parent = find_server("transportd")

    if parent is None:
        print("No transport processes found")
        return

    ppid = parent.name

    children = parent.joinpath("task", ppid, "children").read_text()

    pids = [ppid]
    pids.extend(children.split())

    for pid in pids:
        path = Path(f"/proc/{pid}/cmdline")
        cmdline = path.read_bytes().replace(b"\0", b" ").decode()
        _interpreter, cmd, args = cmdline.split(" ", 2)
        cmd = Path(cmd).name
        print(f"[{pid:>7}] {cmd} {args}")


def main():
    """Main application"""

    print("-" * 75)
    list_processes()
    print("-" * 75)
