#!/usr/bin/env python3
"""Remove a newsgroup"""

#####################################################################
#
#   Remove a news group
#
#   2016-12-26  Todd Valentic
#               Use datatransport package
#
#   2023-08-23  Todd Valentic
#               Updated for transport3 / python3
#               Add command line options
#               Allow for multiple newsgroups
#               Allow for patterns
#
#####################################################################

import argparse
import fnmatch
import sys

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

    available_newsgroups = server.list_newsgroups()

    remove_newsgroups = set()

    for pattern in args.newsgroups:
        for newsgroup in available_newsgroups:
            if fnmatch.fnmatch(newsgroup, pattern):
                remove_newsgroups.add(newsgroup)

    if not remove_newsgroups:
        print("No newsgroups were found")
        sys.exit(0)

    if not args.yes:
        print("")
        print(f"Newsgroups to be removed on {args.server}:{args.port}:")

        for newsgroup in remove_newsgroups:
            print(f"  {newsgroup}")
        print("")

        reply = input("Confirm removal? (Y/N) ").lower()
        if reply != "y":
            sys.exit(1)

    for newsgroup in remove_newsgroups:
        print(f"Removing {newsgroup}")
        server.rmgroup(newsgroup)

    sys.exit(0)
