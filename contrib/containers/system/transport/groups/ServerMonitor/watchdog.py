#!/usr/bin/env python
"""Watchdog"""

############################################################################
#
#   watchdog
#
#   This script monitors the process group clients and reports any that
#   were started but have seemed to stop running (they are registered but
#   don't show up as an active process). In this case, the client is
#   restarted. Messages are also sent to the watchdog list in this case.
#
#   History:
#
#   2000-04-24  TAV
#               Initial implementation
#
#   2002-01-20  Todd Valentic
#               Improved wording of notification message.
#
#   2002-01-24  Todd Valentic
#               Added timestamp to message body.
#
#   2002-01-25  Todd Valentic
#               Added check for self.running
#
#   2002-05-19  Todd Valentic
#               Fixed call to restart client (now include arg string).
#
#   2002-08-28  Todd Valentic
#               sri.transport -> Transport
#               python -> python2
#
#   2003-04-15  Todd Valentic
#               Changed config parameter pollrate -> rate
#               Rate now specified in days/hours/mins/secs
#
#   2004-02-08  Todd Valentic
#               Use DeltaTime for rate
#               Use string methods
#
#   2004-08-08  Todd Valentic
#               Updated to new XML-RPC server interface
#
#   2004-08-25  Todd Valentic
#               Converted to directly reading /proc instead of using ps
#
#   2004-12-30  Todd Valentic
#               Convert from mx.DateTime to datetime
#
#   2022-10-06  Todd Valentic
#               Updated for transport3/python3
#   
#   2023-07-26  Todd Valentic
#               Use config getters
#
############################################################################

import pathlib
import sys

from datatransport import ProcessClient
from datatransport import NewsPoster


class Watchdog(ProcessClient):
    """Watchdog Process Client"""

    def __init__(self, argv):
        ProcessClient.__init__(self, argv)

    def init(self):
        super().init()

        self.news_poster = NewsPoster(self)
        self.rate = self.config.get_rate("rate", "5m")

    def get_client_pids(self):
        """Query server for expected client PIDs"""

        pids = {}

        for group in self.server.listgroups():
            for client, info in self.server.listclients(group).items():
                pid = info[1]
                if pid:
                    pids[pid] = (group, client)

        return pids

    def get_running_pids(self):
        """Get list of running PIDs on system"""

        proc = pathlib.Path("/proc")
        return [int(x.name) for x in proc.iterdir() if x.name.isdigit()]

    def post_message(self, pid, group_name, client_name):
        """Post a trouble message"""

        body = []
        body.append("")
        body.append(
            "  The watchdog has detected the following client has stopped running:"
        )
        body.append("")
        body.append(f"      Client name: {client_name}")
        body.append(f"       Group name: {group_name}")
        body.append(f"       Process ID: {pid}")
        body.append(f"       Time stamp: {self.now()}")
        body.append("")
        body.append("  The client has been restarted.")
        body.append("")

        header = f"Watchdog restart {client_name}"

        try:
            self.news_poster.set_subject(header)
            self.news_poster.post_text("\n".join(body))
        except:  # pylint: disable=bare-except
            self.log.error("Error posting notification message to the news server.")

    def restart(self, pid, group, client):
        """Restart the client process"""

        self.log.info("Process '%s %s' (PID %s) is missing", group, client, pid)
        self.log.info("  Attempting to restart")

        self.post_message(pid, group, client)

        try:
            self.server.startclient(group, client)
        except:  # pylint: disable=bare-except
            self.log.info("  Error detected in client restart!")

    def checkup(self):
        """Check to see if any clients have unexpectedly stopped"""

        self.log.info("Checking processes")

        try:
            self.server.status()
        except:  # pylint: disable=bare-except
            self.log.error("Cannot connect to the transport server!")
            return

        client_pids = self.get_client_pids()
        running_pids = self.get_running_pids()

        for pid, entry in client_pids.items():
            group, client = entry

            if not pid in running_pids:
                self.restart(pid, group, client)

    def main(self):
        """Main application"""

        while self.wait(self.rate):
            self.checkup()


if __name__ == "__main__":
    Watchdog(sys.argv).run()
