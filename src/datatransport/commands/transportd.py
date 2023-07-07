#!/usr/bin/env python
"""Data Transport Service"""

###########################################################################
#
#   transportd
#
#   Start an instance of the TransportServer.
#
#   History:
#
#   1.0.0   2000-06-18  TAV
#           Initial implementation.
#           Separated startup code from TrasnportServer.py
#
#   2.0.0   2002-02-22  Todd Valentic
#           Modified daemon routine to not set the uid/gid. We are now
#               started by the transport user in the /etc/init.d/transportd
#               script. This sets the supplemental groups properly until
#               we are running under python2 (which has os.setgroups).
#               Once we are running python2, make this back into a proper
#               daemon setup.
#
#   2.0.1   2002-08-28  Todd Valentic
#           sri.transport -> Transport
#           Setup with configure
#
#   2.0.2   2002-09-04  Todd Valentic
#           Set the supplementary groups. With the change to python2, we
#               now can use os.setgroups() to set all of the groups that
#               the transport user is part of.
#           Set umask to 0 in daemon mode.
#
#   2.0.3   2003-07-01  Todd Valentic
#           Setting umask to 0 isn't exactly what we want. Now take it
#               as a parameter from the config file (default is 0002).
#
#   2.1.0   2004-08-02  Todd Valentic
#           Converted from CORBA to XML-RPC.
#
#   2.1.1   2005-01-06  Todd Valentic
#           Changed imports for TransportManager and TransportConfig
#
#   2016-12-23  Todd Valentic
#               Migrate to datatransport package format
#
#   2022-10-06  Todd Valentic
#               Move into datatransport/commands
#               Only change user/group if started as root
#
############################################################################

import argparse
import grp
import os
import pwd
import sys

from datatransport import TransportConfig
from datatransport import TransportManager


def initgroups(user, gid):
    """Initialize all of groups for which the user is a member"""

    db = grp.getgrall()

    groups = set(gid)

    for _name, _passwd, gr_gid, gr_mem in db:
        if user in gr_mem:
            groups.add(gr_gid)

    os.setgroups(list(groups))


def daemon(config):
    """Launch as a daemon"""

    os.chdir("/")

    if os.fork():
        os._exit(0)

    os.setsid()

    # pylint: disable=consider-using-with

    sys.stdin = sys.__stdin__ = open("/dev/null", "rb")
    sys.stdout = sys.__stdout__ = open("/dev/null", "wb")
    sys.stderr = sys.__stderr__ = os.dup(sys.stdout.fileno())

    os.umask(config.get_int("umask"))

    username = config.get("username")
    groupname = config.get("groupname")

    if os.getuid() == 0 and username:
        uid = pwd.getpwnam(username).pw_uid
        gid = pwd.getgrnam(groupname).gr_gid

        initgroups(username, gid)
        os.setgid(gid)
        os.setuid(uid)


def main():
    """Main application"""

    config = TransportConfig()["TransportServer"]
    parser = argparse.ArgumentParser(description="Data Transport Network server")

    parser.add_argument(
        "-b", "--daemon", action="store_true", help="Run in the background"
    )

    args = parser.parse_args()

    if args.daemon:
        daemon(config)

    pidfile = config.get_path("pid.file")
    pidfile = pidfile.absolute()
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    pidfile.write_text(f"{os.getpid()}")

    manager = TransportManager()

    status = manager.run()

    pidfile.unlink(missing_ok=True)

    return status
