#!/usr/bin/env python
"""Transport Config"""

#############################################################################
#
#   Transport Config
#
#   This object provides a simple interface to load the global transport
#   configuration file.
#
#   Revision history:
#
#   1.0.0   2000-06-19  TAV
#           Initial implementation
#
#   1.0.1   2001-09-03  TAV
#           Added the getUserInfo() method to return uid/gid.
#
#   1.0.2   2002-08-27  Todd Valentic
#           Setup by configure script.
#           Read hostname and user/group info from config file.
#
#   1.0.3   2004-08-08  Todd Valentic
#           Added umask.
#           Use DefaultConfigParser
#
#   1.0.4   2005-01-06  Todd Valentic
#           Changed DefaultConfigParser to be a local import
#
#   1.0.5   2006-06-03  Todd Valentic
#           Moved default location from server -> etc
#
#   1.0.6   2009-09-07  Todd Valentic
#           Read other .conf files in main config directory
#
#   1.0.7   2019-04-10  Todd Valentic
#           Lookup uid/gid at start instead of from config file
#
#   2016-12-23  Todd Valentic
#               Use DATA_TRANSPORT_PATH environment variable
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#
#   2023-06-27  Todd Valentic
#               Use SapphireConfigParser
#               Remove unused abort() method
#               Remove uid, gid, username, groupname, hostname, umask
#
#   2023-07-09  Todd Valentic
#               Add find_config_files() method
#
#############################################################################

import os
import pathlib

import sapphire_config as sapphire


class TransportConfig(sapphire.Parser):
    """Transport configuration"""

    def __init__(self, defaults=None):
        try:
            prefix = os.environ["DATA_TRANSPORT_PATH"]
        except KeyError:
            prefix = "/opt/transport"

        confdir = pathlib.Path(prefix, "etc")

        mainconf = confdir.joinpath("transportd.conf")

        filenames = sorted(confdir.glob("*.conf"))

        # make sure transportd.conf is read first

        if mainconf in filenames:
            filenames.remove(mainconf)
            filenames.insert(0, mainconf)

        super().__init__(defaults=defaults)

        self.read(filenames)

    def find_config_files(self, groupname, basepath, hostname):

        def glob_conf(curpath, ext):
            mainconf = curpath.joinpath(f"{curpath.name}.{ext}")
            paths = sorted(list(curpath.glob(f"*.{ext}")))

            if mainconf in paths:
                paths.remove(mainconf)
                paths.insert(0, mainconf)

            return paths

        configpaths = []

        for path in reversed(pathlib.Path(groupname,'x').parents):
            curpath = basepath.joinpath(path)

            configpaths.extend(glob_conf(curpath, 'conf'))
            configpaths.extend(glob_conf(curpath, f'conf-{hostname}'))

        return configpaths

