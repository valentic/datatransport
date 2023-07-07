#!/usr/bin/env python
"""Transport Manager"""

##########################################################################
#
#   Create and run a transport server instance.
#
#   2022-10-07  Todd Valentic
#               Add header comment block
#               Reorder imports
#
##########################################################################

import os
import queue
import signal
import subprocess
import time

from . import TransportServer


def handler(_signum, _frame):
    """Signal handler"""
    os.wait()


class TransportManager:
    """Create and run a TransportServer"""

    def __init__(self):
        signal.signal(signal.SIGINT, self.handler)
        signal.signal(signal.SIGTERM, self.handler)
        signal.signal(signal.SIGHUP, self.handler)
        signal.signal(signal.SIGCHLD, handler)

        self.queue = queue.Queue()

        self.tasks = []
        self.server = TransportServer(self.queue)

    def handler(self, _signum, _frame):
        """Handle stop signals"""

        self.server.stop()

    def launch(self, args, environ):
        """Start running a client process"""

        return subprocess.Popen(
            args, env=environ, stderr=subprocess.PIPE, bufsize=1, text=True
        )

    def check(self, tasks):
        """Check the status of launched tasks"""

        running = []

        for task in tasks:
            if task.poll() is None:
                running.append(task)
                continue

            _stdout, stderr = task.communicate()

            if stderr:
                self.server.log.error("Problem with %s:", ' '.join(task.args))

                for line in stderr.split("\n"):
                    self.server.log.error(line)

        return running

    def run(self):
        """Main loop"""

        self.server.start()

        delay = self.server.config.get_timedelta("client.delay", 0.5)
        tasks = []

        while self.server.running:
            tasks = self.check(tasks)

            try:
                _cmd, args, environ = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                # --pylint: disable=consider-using-with
                task = self.launch(args, environ)
            except (PermissionError, subprocess.SubprocessError) as err:
                self.server.log.error("Problem starting %s: %s", args, err)

            time.sleep(delay.total_seconds())
            tasks.append(task)

        self.server.shutdown()
        self.server.join()

        return 0
