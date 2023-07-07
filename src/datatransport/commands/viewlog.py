#!/usr/bin/env python

##########################################################################
#
#   ViewLog
#
#   This program displays either the server or a process group's log file
#   in a manner like "tail -F".
#
#   1.0.0   2000-??-??  Todd Valentic
#           Original implementation.
#
#   1.0.1   2002-08-26  Todd Valentic
#           Modified to be setup via configure script.
#
#   2.0.0   2005-01-07  Todd Valentic
#           Completely rewritten and no longer depends on the
#               system's tail command. Checks are made for
#               new files periodically to handle rotating log
#               files.
#
#   2.0.1   2005-04-07  Todd Valentic
#           Sort lines at start to order by time.
#
#   2.0.2   2005-11-08  Todd Valentic
#           Added key parameter to line sorting so we only sort
#               on the date.
#
#   2.0.3   2007-04-14  Todd Valentic
#           Only print log entry lines (those starting with "[")
#               at start to avoid printing part of an traceback.
#               
#   2016-12-23  Todd Valentic
#               Use datatransport package format
#               Use print()
#
#   2022-10-06  Todd Valentic
#               Move into datatransport/commands
#               Convert from optparse -> argparse
#
##########################################################################

import argparse
import glob
import os
import signal
import sys
import time

from pathlib import Path

from datatransport import TransportConfig

class FileTracker:

    def __init__(self,name):

        self.name       = name
        self.file       = None
        self.size       = 0
        self.inode      = 0
        self.dev        = 0
        self.firsttime  = True

        self.n_unchanged_stats = 0
        self.n_consecutive_size_changes = 0

        self.reopen()

    def reopen(self):

        try:
            file  = open(self.name)
            stats = os.stat(self.name)
        except:
            self.file  = None
            self.inode = 0
            self.dev   = 0
            return

        self.n_unchanged_stats = 0
        self.n_consecutive_size_changes = 0

        if self.inode!=stats.st_ino or self.dev!=stats.st_dev:
            self.inode  = stats.st_ino
            self.dev    = stats.st_dev
            self.size   = 0
            self.file   = file

            if self.firsttime:
                offset = 500
                self.firsttime=False
                self.size = max(stats.st_size-offset,0)
            else:
                self.size = 0

    def poll(self):

        if not self.file:
            self.reopen()
            return None

        try:
            stat = os.stat(self.name)
        except:
            self.file = None
            return None

        if self.size==stat.st_size:
            self.n_unchanged_stats+=1
            self.n_consecutive_size_changes=0
            if self.n_unchanged_stats>5:
                self.reopen()
            return None

        self.n_unchanged_stats=0
        self.n_consecutive_size_changes+=1

        if self.n_consecutive_size_changes>200:
            self.reopen()
            return None

        if self.size>stat.st_size:
            self.reopen()
            return None

        self.file.seek(self.size)
        data = self.file.read()
        self.size = self.file.tell()

        return data

def parsedate(line):
    return line.split(']')[0][1:].rsplit(' ',1)[0].strip()

class Tail:

    def __init__(self,filenames):

        self.rate   = 0.5
        self.trackers  = [FileTracker(f) for f in filenames]

    def run(self):
        
        # Print the last 10 lines or so of each file. Sort the lines
        # to put in time order.

        lines = []

        for tracker in self.trackers:
            output = tracker.poll()
            if output:
                for line in output.split('\n')[1:][-10:]:
                    if line.startswith('['):
                        lines.append(line)

        lines.sort(key=parsedate)

        for line in lines:
            print(line)

        # Tail forever

        while True:

            for tracker in self.trackers:
                output = tracker.poll()
                if output:
                    print(output.strip())

            time.sleep(self.rate)


def display (args):

    if args.group:

        defaults =  {   'group.name':       args.group,
                        'group.basename':   os.path.basename(args.group),
                        'group.dirname':    os.path.dirname(args.group)
                    }

        config  = TransportConfig(defaults)
        logpath = Path(config.get('DEFAULT','log.path'))
        logfiles = list(logpath.glob('*.log'))

        if args.client:
            logfiles = [fn for fn in logfiles if Path(fn).stem in args.clients]

    else:
        logfiles = [TransportConfig().get('TransportServer','log.file')]

    if not logfiles:
        print('No log files found')
        return

    print()
    print('Watching:')
    for filename in logfiles:
        print('  %s' % filename)
    print()

    Tail(logfiles).run()

def handler(signum,frame):
    sys.exit(0)

def main():

    signal.signal(signal.SIGINT,handler)

    usage   = 'viewlog [options] [group] [client client ....]'
    desc    = 'Data Transport Log Viewer'
    parser  = argparse.ArgumentParser(description=desc)

    parser.add_argument('group', nargs="?", help='Group name')
    parser.add_argument('client', nargs='*', help='Client names')

    args = parser.parse_args()

    display(args)

