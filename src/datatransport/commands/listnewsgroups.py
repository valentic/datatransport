#!/usr/bin/env python3
"""List newsgroups"""

#####################################################################
#
#   List news groups on a news server
#
#   2012-09-24  Todd Valentic
#               Initial implementation
#
#   2022-10-07  Todd Valentic
#               Python3 updates
#                   optparse -> argparse
#
#   2023-08-17  Todd Valentic
#               Add port option
#
#####################################################################

import argparse
import nntplib


def lister(args):
    """Newsgroup lister"""

    server = nntplib.NNTP(args.newsserver, port=args.port)
    groups = server.list()[1]

    counts = {}

    for group in groups:
        name = group[0]
        first = int(group[2])
        last = int(group[1])
        counts[name] = last - first + 1

    if args.sort == "name":
        key = None
    else:
        key = counts.__getitem__

    for group in sorted(counts, key=key, reverse=args.reverse):
        line = ""
        if args.showcount:
            line += f"{counts[group]:10d} "
        line += group

        print(line)


def main():
    """Script entry point"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-n",
        "--newsserver",
        default="127.0.0.1",
        help="News server address (default is %(default)s)",
    )

    parser.add_argument(
        "-p", "--port", default=119, type=int, help="New server port (default 119)"
    )

    parser.add_argument(
        "-c", "--showcount", action="store_true", help="Show message counts"
    )

    parser.add_argument(
        "-s", "--sort", default="name", choices=["name", "count"], help="Sort"
    )

    parser.add_argument(
        "-r", "--reverse", action="store_true", help="Reverse sort order"
    )

    args = parser.parse_args()

    lister(args)

    return 0
