#!/usr/bin/env python3
"""Post files to a newsgroup"""

#####################################################################
#
#   Post a files in a message to a newsgroup
#
#   2016-12-26  Todd Valentic
#               Use datatransport package
#
#   2023-08-23  Todd Valentic
#               Updated for transport3 / python3
#
#####################################################################

import argparse
import pathlib
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
        "-t", "--text", action="store_true", help="Post file contents as body text"
    )
    parser.add_argument("-n", "--newsgroup", help="Newsgroup name", required=True)
    parser.add_argument("-b", "--subject", help="Subject header")
    parser.add_argument("filenames", nargs="+", metavar="filename", type=pathlib.Path)

    args = parser.parse_args()

    poster = newstool.NewsPoster()
    poster.set_server(args.server, port=args.port)
    poster.set_newsgroup(args.newsgroup)
    if args.subject:
        poster.set_subject(args.subject)

    if not poster.has_newsgroup(args.newsgroup):
        print(f"The newsgroup does not exist: {args.newsgroup}")
        sys.exit(1)

    if args.text:
        content = args.filenames[0].read_text("utf-8")
        poster.post_text(content)
    else:
        poster.post(args.filenames)

    sys.exit(0)
