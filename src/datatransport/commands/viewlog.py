#!/usr/bin/env python
"""Data Transport log viewer"""

##########################################################################
#
#   Viewlog
#
#   2026-03-07  Todd Valentic
#               Complete reimplementation using the watchdog package.
#               Handle both test and JSON formatted logs.
#               Try to remain compatible with original.
#               Release 3.2.0
#
#   2026-04-23  Todd Valentic
#               Look for stderr passed in extra field, show in panel
#
##########################################################################

import argparse
import heapq
import logging
import time
import json
import os
import re
import sys
import threading

from collections import namedtuple
from datatransport import TransportConfig
from datetime import datetime
from functools import total_ordering, cached_property
from pathlib import Path, PurePosixPath
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from rich import print
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

VERSION = "3.2.1"

console = Console()

# -------------------------------------------------------------------------
# utilitlies 
# -------------------------------------------------------------------------

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

# -------------------------------------------------------------------------
# parse block of text into records starting with [(asctime) (levelname)]
# -------------------------------------------------------------------------

text_parser = re.compile(
    r"""
    ^\[
        (?P<asctime>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)
        \s+
        (?P<levelname>[A-Z]+)
    \]
    \s+
    (?P<name>[^:]+)
    :
    \s*?
    (?P<full_message>
        [^\n]*                 # first message line
        (?:\n(?!\[\d{4}-\d{2}-\d{2})[^\n]*)*   # continuation lines
    )
    """,
    re.MULTILINE | re.VERBOSE,
)

# -------------------------------------------------------------------------
# multi pattern filter
#
#   exclude patterns starting with !
#   * = one level
#   ** = any depth
#   automatic leaf filtering
# -------------------------------------------------------------------------


class FilterManager:
    def __init__(self, patterns):
        self.rules = self.compile_patterns(patterns)
        self.include_names = set()
        self.exclude_names = set()

    def compile_patterns(self, patterns):
        rules = []

        for pat in patterns:
            include = True
            if pat.startswith("!"):
                include = False
                pat = pat[1:]

            pat = re.escape(pat)
            pat = pat.replace(r"\*\*", ".*")
            pat = pat.replace(r"\*", "[^/]+")

            regex = re.compile(rf"^{pat}$")
            rules.append((include, regex))

        return rules

    def check_name(self, name, leaf_only=True):
        path = PurePosixPath(name)

        s = str(path)
        keep = False

        for include, regex in self.rules:
            if regex.match(s):
                keep = include
                break

        if not keep:
            self.exclude_names.add(s)
            return False

        if leaf_only and path == path.parent:
            self.exclude_names.add(s)
            return False

        self.include_names.add(s)

        return True

    def match(self, name):

        if name in self.include_names:
            return True

        if name in self.exclude_names:
            return False

        return self.check_name(name)


# -------------------------------------------------------------------------
# merge queue
# -------------------------------------------------------------------------


@total_ordering
class RecordKey:
    def __init__(self, record):
        self.record = record

    @cached_property
    def key(self):
        return self.record["asctime"].replace(",", ".")

    @cached_property
    def ts(self):
        return datetime.strptime(self.key, "%Y-%m-%d %H:%M:%S.%f")

    def __lt__(self, other):
        return self.key < other.key

    def __eq__(self, other):
        return self.key == other.key

    def __repr(self):
        return f"{__class__.__name__}(record={self.record})"


class RecordQueue:
    def __init__(self, filters, level="notset", limit=None):
        self.filters = filters
        self.heap = []
        self.limit = limit  
        self.lock = threading.Lock()

        self.level_map = logging.getLevelNamesMapping()
        self.level = self.level_map[level.upper()]

    def set_limit(self, limit):
        self.limit = limit
        self.trim(limit)

    def trim(self, nitems):

        with self.lock:
            if len(self.heap) > nitems:
                self.heap = heapq.nlargest(nitems, self.heap)
                heapq.heapify(self.heap)

    def add(self, record):

        record_key = RecordKey(record)

        if not self.filters.match(record["name"]):
            return

        level = self.level_map.get(record["levelname"].upper(), None)
        if level is None or level < self.level: 
            return

        with self.lock:
            if self.limit is None or len(self.heap) < self.limit:
                heapq.heappush(self.heap, record_key)
            else:
               heapq.heappushpop(self.heap, record_key)

    def flush(self):

        while self.heap:
            with self.lock:
                record = heapq.heappop(self.heap).record
            print_record(record)

# -------------------------------------------------------------------------
# record handling
# -------------------------------------------------------------------------


def print_record(record):
    
    styles = {
        "CRITICAL": "red",
        "ERROR":    "bold red",
        "WARNING":  "yellow",
        "INFO":     "green",
        "DEBUG":    "cyan",
    }

    level = record.get("levelname", "")
    msg = record.get("message", "")
    ts = record.get("asctime", "")
    name = record.get("name", "")
    exc = record.get("exc_info", None)
    stderr = record.get("stderr", None)
    threadname = record.get("threadName", "")

    if threadname:
        name = f"{name} [{threadname}]"

    style = styles.get(level, "white")

    if level == "ERROR":
        msg_style = styles.get(level)
    else:
        msg_style = "white" 

    text = Text.assemble(
        (f"[{ts} "),
        (f"{level:>7}", style),
        (f"] {name}: "),
        (f"{msg}", msg_style),
    )

    console.print(text, soft_wrap=True)

    if exc:
        line = f"{exc}"
        text = Panel(line, style=style)
        console.print(text, soft_wrap=True)

    if stderr:
        line = f"{stderr}"
        text = Panel(line, style=style)
        console.print(text, soft_wrap=True)

def plain_print_record(record):

    try:
        if "threadName" in record:
            print("[{asctime} {levelname}] {name}: {message}".format(**record))
        else:
            print("[{asctime} {levelname}] {name}: {message}".format(**record))

        if "exc_info" in record:
            print(record["exc_info"])

        if "stderr" in record:
            print(record["stderr"])

    except KeyError:
        pass

def split_message(full_message):
    """Split trackback from message if present"""
    idx = full_message.find("Traceback")
    if idx == -1:
        return full_message, None 
    return full_message[:idx].rstrip(), full_message[idx:]

def parse_records(content):
    """Parse the contents (text or json) into a list of records"""

    records = []

    # First try to parse as a text file

    for m in text_parser.finditer(content):
        record = m.groupdict()
        msg, exc = split_message(record.pop("full_message"))
        record["message"] = msg
        record["exc_info"] = exc
        records.append(record)

    if records:
        return records

    # Otherwise it is a JSON file

    records = []

    for line in content.split("\n"):
        try:
            record = json.loads(line)
            if isinstance(record, dict) and "asctime" in record:
                records.append(record)
        except json.JSONDecodeError:
            continue

    return records


# -------------------------------------------------------------------------
# file reader
# -------------------------------------------------------------------------

FileMetadata = namedtuple("FileMetadata", ["pos", "ino", "dev"])


class FileReader:
    def __init__(self, path, record_queue):
        self.path = path.resolve()
        self.record_queue = record_queue
        self.metadata = self.reset(self.path)

        self.read_new_content()

    def reset(self, path):
        """Reset file metadata"""

        stat = path.stat()
        return FileMetadata(0, stat.st_ino, stat.st_dev)

    def read_new_content(self):
        """Read from a file position and update metadata."""

        curr = self.path.stat()
        prev = self.metadata

        # Check for rotation or turncation

        if (
            curr.st_ino != prev.ino
            or curr.st_dev != prev.dev
            or curr.st_size < prev.pos
        ):
            self.metadata = self.reset(self.path)

        with self.path.open("r", encoding="utf-8") as f:
            f.seek(self.metadata.pos)
            content = f.read()
            self.metadata = FileMetadata(f.tell(), curr.st_ino, curr.st_dev)
            for record in parse_records(content.rstrip("\n")):
                self.record_queue.add(record)


# -------------------------------------------------------------------------
# file manager
# -------------------------------------------------------------------------


class FileManager:
    """Manage group of FileReader objects"""

    def __init__(self, record_queue):
        self.record_queue = record_queue
        self.file_readers = {}

    def process(self, path):
        """Read new content from path"""

        if path not in self.file_readers:
            self.add(path)

        try:
            self.file_readers[path].read_new_content()
        except FileNotFoundError:
            pass

    def add(self, path):
        """Add a new FileReader to the managed group"""
        self.file_readers[path] = FileReader(path, self.record_queue)


# -------------------------------------------------------------------------
# event handler
# -------------------------------------------------------------------------


class EventHandler(FileSystemEventHandler):
    """Process new records on file change"""

    def __init__(self, file_manager, file_ext=".log"):
        self.file_ext = file_ext
        self.file_manager = file_manager

    def on_modified(self, event):
        """Read new content on change"""

        path = Path(event.src_path).resolve()

        if event.is_directory or self.file_ext != path.suffix: 
            return

        self.file_manager.process(path)


# -------------------------------------------------------------------------
# main
# -------------------------------------------------------------------------


def parse_command_line():
    """Parse command line"""

    try:
        config = TransportConfig()
    except FileNotFoundError as e:
        print(e)
        if "DATA_TRANSPORT_PATH" not in os.environ:
            print("DATA_TRANSPORT_PATH is not set")
        sys.exit(1)

    logpath = config.get_path("DEFAULT", "path.logfiles")
    ext = config.get_path("TransportServer", "log.file").suffix

    defaults = dotdict({"logpath": logpath, "ext": ext, "limit": 30})

    desc = f"Data Transport Log Viewer {VERSION}"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument(
        "filters", nargs="*", default=["*"], help="group and/or client names"
    )

    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Show child log files"
    )

    parser.add_argument(
        "-u", "--parents", action="store_true", help="Show parent log files"
    )

    parser.add_argument(
        "-s", "--server", action="store_true", help="Show TransportServer logs"
    )

    parser.add_argument(
        "-b", "--no-follow", action="store_true", help="Show existing logs and exit"
    )

    parser.add_argument(
        "-l", "--level", 
        choices=["notset", "debug", "info", "warning", "error", "critical"],
        default="notset",
        help="Show messages from this level and higher"
    )

    parser.add_argument(
        "-n",
        "--limit",
        metavar="N",
        type=int,
        default=defaults.limit,
        help=f"Limit to last N records (default {defaults.limit})",
    )

    parser.add_argument(
        "-p",
        "--logpath",
        type=Path,
        default=defaults.logpath,
        metavar="PATH",
        help=f"Base path for log files (default {defaults.logpath})",
    )

    parser.add_argument(
        "-e", "--ext", default=ext, help=f"Log file extension (default {defaults.ext})"
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.add_argument("-V", "--version", action="version", version=VERSION)

    args = parser.parse_args()

    if args.server:
        args.filters.append("TransportServer")

    if args.parents:
        for pattern in list(args.filters):
            # skip the last parent, which will be . or /
            for parent in Path(pattern).parents[:-1]:
                args.filters.append(str(parent))

    for pattern in list(args.filters):
        if args.recursive:
            args.filters.append(f"{pattern}/**")
        else:
            args.filters.append(f"{pattern}/*")

    return args


def scan_existing_files(file_manager, args):
    """Initialize tracking for existing files"""

    logfiles = [p.resolve() for p in args.logpath.glob(f"**/*{args.ext}*")]

    for path in sorted(logfiles, reverse=True):
        file_manager.add(path)


def main():
    """Main application"""

    args = parse_command_line()
    filters = FilterManager(args.filters)

    record_queue = RecordQueue(filters, level=args.level, limit=args.limit)
    file_manager = FileManager(record_queue)

    scan_existing_files(file_manager, args)

    if args.no_follow:
        record_queue.flush()
        sys.exit(0)

    # Make sure we can buffer a reasonable number between flushes
    record_queue.set_limit(1000)

    event_handler = EventHandler(file_manager, args.ext)

    observer = Observer()
    observer.schedule(event_handler, args.logpath, recursive=True)
    observer.start()

    try:
        while True:
            record_queue.flush()
            time.sleep(0.1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
