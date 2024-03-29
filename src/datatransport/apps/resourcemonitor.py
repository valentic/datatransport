#!/usr/bin/env python3
"""Resource monitor"""

# pylint: disable=broad-exception-caught

##########################################################################
#
#   Resource Monitor
#
#   Collect and post a snapshot of the computer health:
#
#       - disk usage
#       - memory usage
#       - processor load
#       - uptime
#       - network usage
#
#   1.0.0   2004-02-01  Todd Valentic
#           Initial implementation.
#
#   1.0.1   2004-02-17  Todd Valentic
#           Handle rollover in tx/rx rate computation.
#           Tx/Rx rates were swapped.
#
#   1.0.2   2004-08-24  Todd Valentic
#           Changed memory section to just pass on values
#               found in /proc/meminfo (the summary format
#               was dropped in the 2.6.X kernels).
#
#   1.0.3   2004-09-19  Todd Valentic
#           Added swap statistics from /proc/swaps
#
#   1.0.4   2004-012-27 Todd Valentic
#           Convert from mx.DateTime to datetime
#
#   1.0.5   2008-11-10  Todd Valentic
#           Use SafeConfigParser
#
#   1.0.6   2008-12-08  Todd Valentic
#           Make sure all set() calls use strings
#
#   1.0.7   2009-11-24  Todd Valentic
#           Use currentTime()
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               Python3 updates:
#                   ConfigParser -> configparser
#                   StringIO -> io.StringIO
#               Use get_rate()
#               Use NewsPoster
#
#   2023-08-11  Todd Valentic
#               Updated for transport3 / python3
#
##########################################################################

import io
import os
import sys

from pathlib import Path

from datatransport import ProcessClient
from datatransport import NewsPoster
import sapphire_config as sapphire


class ResourceMonitor(ProcessClient):
    """Resource Monitor"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

        self.news_poster = NewsPoster(self)
        self.rate = self.config.get_rate("rate", 600)

        self.lasttx = {}
        self.lastrx = {}

    def read_proc(self, path):
        """Read data from /proc path"""

        return Path("/proc", path).read_text('utf-8').split("\n")

    def update_mounts(self, stats):
        """Update status of file mounts"""

        mounts = self.read_proc("mounts")
        mounts = [mount.split()[0:4] for mount in mounts if mount]

        paths = []

        for device, path, fstype, access in mounts:
            try:
                info = os.statvfs(path)
            except OSError:
                continue

            if device == "none":
                continue

            if info.f_blocks == 0:
                continue

            if stats.has_section(path):
                continue

            paths.append(path)

            totalbytes = info.f_blocks * info.f_bsize
            freebytes = info.f_bavail * info.f_bsize
            reserved = info.f_bfree * info.f_bsize - freebytes
            totalavail = totalbytes - reserved
            usedbytes = totalavail - freebytes
            usedpct = usedbytes / float(totalavail) * 100

            stats.add_section(path)
            stats.set(path, "device", device)
            stats.set(path, "fstype", fstype)
            stats.set(path, "access", access)
            stats.set(path, "totalbytes", str(totalavail))
            stats.set(path, "freebytes", str(freebytes))
            stats.set(path, "usedbytes", str(usedbytes))
            stats.set(path, "usedpct", str(usedpct))

        stats.set("System", "mounts", " ".join(paths))

    def update_memory(self, stats):
        """Update memory usage stats"""

        lines = self.read_proc("meminfo")

        if "total:" in lines[0]:  # old style format
            lines = lines[3:]

        section = "Memory"
        stats.add_section(section)

        for line in lines:
            try:
                key, value = line.split(":")
                value = int(value.split()[0]) * 1024
                stats.set(section, key, str(value))
            except Exception:
                pass

    def update_load(self, stats):
        """Update load stats"""

        info = self.read_proc("loadavg")
        load = info[0].split()

        section = "Load"

        stats.add_section(section)
        stats.set(section, "1min", load[0])
        stats.set(section, "5min", load[1])
        stats.set(section, "15min", load[2])

    def update_swaps(self, stats):
        """Update swap usage"""

        section = "Swaps"
        stats.add_section(section)

        info = self.read_proc("swaps")

        swaps = []

        for line in info[1:-1]:
            if not line:
                continue
            try:
                dev, fstype, size, used, priority = line.split()
            except ValueError:
                continue
            swaps.append(dev)
            stats.set(section, dev + ".type", fstype)
            stats.set(section, dev + ".size", str(int(size) * 1024))
            stats.set(section, dev + ".used", str(int(used) * 1024))
            stats.set(section, dev + ".priority", priority)

        stats.set(section, "mounts", " ".join(swaps))

    def update_uptime(self, stats):
        """Update uptime stats"""

        info = self.read_proc("uptime")
        secs = float(info[0].split()[0])

        section = "Uptime"
        stats.add_section(section)
        stats.set(section, "seconds", str(secs))

    def compute_rate(self, prevbytes, prevtime, curbytes, curtime):
        """Update network data rates"""

        if prevbytes > curbytes:
            # Counter rollover
            deltabytes = 2**32 - prevbytes + curbytes
        else:
            deltabytes = curbytes - prevbytes
        return deltabytes / (curtime - prevtime).seconds

    def update_network(self, stats):
        """Update networks"""

        info = self.read_proc("net/dev")[2:-1]

        section = "Network"
        stats.add_section(section)

        devs = []
        now = self.now()

        for device in info:
            name, data = device.split(":")
            name = name.strip()
            data = data.split()

            if name in self.lasttx:
                txbytes, txtime = self.lasttx[name]
                rxbytes, rxtime = self.lastrx[name]
                txrate = self.compute_rate(txbytes, txtime, float(data[8]), now)
                rxrate = self.compute_rate(rxbytes, rxtime, float(data[0]), now)
            else:
                txrate = 0
                rxrate = 0

            stats.set(section, name + ".rx.rate", str(rxrate))
            stats.set(section, name + ".rx.bytes", data[0])
            stats.set(section, name + ".rx.packets", data[1])
            stats.set(section, name + ".rx.errs", data[2])
            stats.set(section, name + ".rx.drop", data[3])

            stats.set(section, name + ".tx.rate", str(txrate))
            stats.set(section, name + ".tx.bytes", data[8])
            stats.set(section, name + ".tx.packets", data[9])
            stats.set(section, name + ".tx.errs", data[10])
            stats.set(section, name + ".tx.drop", data[11])

            self.lasttx[name] = (float(data[8]), now)
            self.lastrx[name] = (float(data[0]), now)

            devs.append(name)

        stats.set(section, "devices", " ".join(devs))

    def process(self):
        """Gather new status snapshot"""

        timestamp = self.now()

        stats = sapphire.Parser()
        stats.add_section("System")
        stats.set("System", "timestamp", str(timestamp))

        self.update_mounts(stats)
        self.update_memory(stats)
        self.update_load(stats)
        self.update_uptime(stats)
        self.update_network(stats)
        self.update_swaps(stats)

        buffer = io.StringIO()
        stats.write(buffer)

        self.news_poster.post_text(buffer.getvalue(), date=timestamp)

        self.log.info("Posting snapshot")

    def main(self):
        while self.wait(self.rate):
            try:
                self.process()
            except Exception:  # pylint: disable=broad-exception-caught
                self.log.exception("Error updating snapshot")


def main():
    """Script entry point"""
    ResourceMonitor(sys.argv).run()
