#!/usr/bin/env python3
"""Create a data transport application"""

##########################################################################
#
#   Create initial data transport application directory layout.
#
#   2020-10-09  Todd Valentic
#               Initial implementation
#
##########################################################################

import argparse
import grp
import logging
import os
import platform
import pwd
import shutil
import sys

from pathlib import Path

import datatransport

if sys.version_info < (3, 10):
    import importlib_resources as resources
else:
    from importlib import resources

def parse_args(args=None):
    """Parse command line"""

    if not args:
        args = sys.argv[1:]

    user = pwd.getpwuid(os.getuid()).pw_name
    group = grp.getgrgid(os.getgid()).gr_name
    hostname = platform.node().split(".", 1)[0]

    parser = argparse.ArgumentParser(
        description="Create a new data transport application"
    )

    parser.add_argument("-d", "--dir", help="Installation directory", default=".")

    parser.add_argument("-u", "--user", help=f'Run as user "{user}"', default=user)

    parser.add_argument("-g", "--group", help=f'Run as group "{group}"', default=group)

    parser.add_argument(
        "-n", "--hostname", help=f'Hostname "{hostname}"', default=hostname
    )

    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true")
    return parser.parse_args(args)


def create_dirs(basepath):
    """Create directory layout"""

    basepath.mkdir(exist_ok=True, parents=True)

    dirs = ["bin", "etc", "var", "tmp", "log", "groups"]

    for leaf in dirs:
        basepath.joinpath(leaf).mkdir(exist_ok=True)

    basepath.joinpath("groups").chmod(0o2775)


def install_config(args, basepath):
    """Install configuration files"""

    for entry in resources.files("datatransport.templates.etc").iterdir():
        contents = entry.read_text()
        contents = contents.replace("@PREFIX@", str(basepath.absolute()))
        contents = contents.replace("@PACKAGE_VERSION@", datatransport.__version__)
        contents = contents.replace("@USER@", args.user)
        contents = contents.replace("@GROUP@", args.group)
        contents = contents.replace("@HOSTNAME@", args.hostname)

        output_path = basepath / "etc" / entry.name

        with output_path.open(mode="w") as output:
            output.write(contents)


def link_programs(basepath):
    """Link programs into bin"""

    venv_path = Path(os.environ["VIRTUAL_ENV"], "bin")
    dest_path = basepath.joinpath("bin")

    programs = [
        "cancelnewsgroup",
        "console",
        "createnewsgroup",
        "listnewsgroups",
        "rmnewsgroup",
        "transport-create-app",
        "transport-get-article",
        "transport-post-article",
        "transportctl",
        "transportd",
        "transportps",
        "viewlog",
    ]

    for program in programs:
        src = venv_path.joinpath(program)
        dst = dest_path.joinpath(program)
        dst.symlink_to(src)


def install_groups(package, basepath):
    """Install default process groups"""

    basepath.mkdir(exist_ok=True)
    basepath.chmod(0o2775)

    for entry in [r.name for r in resources.files(package).iterdir()]:
        if resources.files(package).joinpath(entry).is_file():
            with resources.path(package, entry) as srcpath:
                destpath = basepath / entry
                shutil.copyfile(srcpath, destpath)
                destpath.chmod(0o775)
                logging.debug("Copy %s -> %s", srcpath, basepath)
        else:
            install_groups(f"{package}.{entry}", basepath / entry)


def main():
    """Script entry point"""

    args = parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    basepath = Path(args.dir)

    create_dirs(basepath)
    install_config(args, basepath)
    link_programs(basepath)
    install_groups("datatransport.templates.groups", basepath / "groups")

    print(f"Created in {basepath}")
