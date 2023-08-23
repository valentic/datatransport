#!/usr/bin/env python3
"""Create a newsgroup"""

#####################################################################
#
#   CreateNewsgroup
#
#   This script creates a newsgroup on the news server.
#
#   2002-03-04	Todd Valentic
#               Initial implementation
#
#   2016-12-25  Todd Valentic
#               Use datatransport package
#
#   2023-08-23  Todd Valentic
#               Updated for transport3 / python3
#               Add command line options
#
#####################################################################

import argparse
import sys
import time

from datatransport import newstool

VERSION = "1.0"


def main():
    """Script entry point"""

    desc = "Remove a newsgroup from the news server"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("-V", "--version", action="version", version=VERSION)

    parser.add_argument(
        "-s", "--server", default="localhost", help="News server (default: localhost)"
    )
    parser.add_argument(
        "-p", "--port", default=119, type=int, help="News server port (default: 119)"
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Automatically confirm removal"
    )

    parser.add_argument("newsgroups", nargs="+", metavar="newsgroup")

    args = parser.parse_args()

    server = newstool.NewsControl()
    server.set_server(args.server, port=args.port)

    for newsgroup in args.newsgroups:
        if server.has_newsgroup(newsgroup):
            print(f"The newsgroup already exists: {newsgroup}")
            continue

        print(f"Creating the newsgroup: {newsgroup}")

        server.newgroup(newsgroup)

        print("Waiting for group to show up:  ", end="", flush=True)

        deadline = time.time() + 120

        wheel = ["-", "/", "|", "\\"]
        curpos = 0

        while not server.has_newsgroup(newsgroup):
            print(f"\b{wheel[curpos]}", end="", flush=True)
            curpos = (curpos + 1) % len(wheel)
            time.sleep(1)

            if time.time() > deadline:
                print("")
                print("Timeout. Failed to create newsgroup")
                sys.exit(1)

        print("\bDone")

    sys.exit(0)
