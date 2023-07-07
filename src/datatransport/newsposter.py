#!/usr/bin/env python
"""NewsPoster"""

##############################################################################
#
#   Data Transport NewsPoster
#
#   This class provides news posting functionality.
#
#   History:
#
#   1999-??-??  Todd Valentic
#               Initial implementation.
#
#   2000-04-26  Todd Valentic
#               Code cleanup, added enable checks, quiet flag.
#
#   2000-04-29  Todd Valentic
#               Now have the group creation part spin until group shows up.
#
#   2001-09-06  Todd Valentic
#               Added support for cross-posting. newsgroup can now be a
#                   list of groups.
#
#   2001-09-25  Todd Valentic
#               Set server default to be localhost.
#
#   2001-11-09  Todd Valentic
#               Renamed newstool -> NewsTool
#
#   2001-12-26  Todd Valentic
#               Changed tav -> sri
#
#   2002-01-24  Todd Valentic
#               Major changes.
#               Renamed config parameters so they use the prefix (default: post)
#               Server defualt is now localhost
#               Can now name the created object (default: newsPoster)
#
#   2002-03-22  Todd Valentic
#               Moved the mojority of the ctor code into createNewsPoster().
#                   This factory method can then be called multiple times and
#                   avoid the kludge idiom of calling the ctor again and again
#                   when more then one NewsPoster is needed.
#
#   2002-03-27  Todd Valentic
#               Fixed bug in reimplementation of createNewsPoster().
#
#   2002-08-28  Todd Valentic
#               sri.transport -> Transport
#
#   2003-04-15  Todd Valentic
#               Remove usage of string module - use string methods instead.
#               Cleaned up code createNewsPoster.
#
#   2004-02-05  Todd Valentic
#               Added enable config option.
#
#   2004-05-26  Todd Valentic
#               Change test for no news group.
#
#   2004-08-17  Todd Valentic
#               Changed to new logging interface.
#               Improved error reporting.
#
#   2005-01-06  Todd Valentic
#               Changed NewsTool import.
#
#   2005-03-06  Todd Valentic
#               Added creategroup option.
#
#   2005-06-13  Todd Valentic
#               Added ability to set extra post headers in config file.
#
#   2007-11-16  Todd Valentic
#               Make sure news group names are lower case
#
#   2008-07-18  Todd Valentic
#               Print news server and group names in error messages.
#
#   2008-08-11  Todd Valentic
#               Make sure we can connect to the news server at start.
#
#   2008-08-12  Todd Valentic
#               Correctly implement feature in 2.0.13.
#
#   2008-08-14  Todd Valentic
#               Fix another bug with 2.0.13 update. self.running not
#                   exposed in AccessMixin.
#
#   2008-08-18  Todd Valentic
#               Fix yet another (!) bug with 2.0.13 update. Only check
#                   news server connection if there are groups to create.
#
#   2009-05-05  Todd Valentic
#               Use setattr() instead of exec()
#
#   2009-05-11  Todd Valentic
#               Update to minor changes in NewsTool
#
#   2009-06-18  Todd Valentic
#               Fixed typo in createNewsPoster (post -> poster)
#
#   2009-07-23  Todd Valentic
#               Only check news server connection if we are creating
#                   groups (another 2.0.13 fix).
#
#   2012-10-05  Todd Valentic
#               Support setting server port
#
#   2021-07-04  Todd Valentic
#               Allow setting mulitple headers with .headers config
#
#   2022-10-06  Todd Valentic
#               Port to transport3 / python3
#                   newsPoster -> news_poster
#                   createNewsPoster -> _poster_create
#
#   2023-07-04  Todd Valentic
#               Convert fom being a mixin class
#
##############################################################################

import fnmatch
import nntplib
import socket

from datatransport import newstool


class NewsPoster:
    """Data Transport NewsPoster"""

    def __init__(self, parent, **kwargs):
        self._poster = self._create_news_poster(parent, **kwargs)

    def __getattr__(self, name):
        return getattr(self._poster, name)

    def _get_headers(self, parent, prefix):
        headers = {}

        for header in parent.get_list(f"{prefix}.headers"):
            try:
                name, value = [v.strip() for v in header.split("=", 1)]
            except (AttributeError, ValueError):
                parent.log.error(f"Failed to process header: {header}")
                continue

            headers[name.upper()] = value

        for key in fnmatch.filter(parent.options(), f"{prefix}.header.*"):
            name = key.replace(f"{prefix}.header.", "").strip().upper()
            headers[name] = parent.get(key).strip()

        if headers:
            parent.log.info("Extra headers:")
            for name, value in headers.items():
                parent.log.info(f"  {name}={value}")

        return headers

    def _create_newsgroups(self, parent, control, newsgroups):
        host = f"{control.server_host}:{control.server_port}"

        control.open_server()

        for newsgroup in newsgroups:
            if not control.has_newsgroup(newsgroup):
                control.newgroup(newsgroup)
                parent.log.info(f"Creating the post newsgroup {newsgroup} on {host}")

                while not control.has_newsgroup(newsgroup):
                    parent.log.info("Waiting for newsgroup to show up")

                    if not parent.wait(15):
                        parent.abort("Exiting")

                parent.log.info(f"Newsgroup {newsgroup} on {host} is ready")

    # pylint: disable=too-many-locals

    def _create_news_poster(self, parent, prefix="post", quiet=False):
        """Create a news poster"""

        newsserver = parent.get(f"{prefix}.newsserver", "localhost")
        port = parent.get_int(f"{prefix}.newsserver.port", 119)
        newsgroups = parent.get_list(f"{prefix}.newsgroup")
        enable = parent.get_boolean(f"{prefix}.enable", True)
        creategroup = parent.get_boolean(f"{prefix}.creategroup", True)

        headers = self._get_headers(parent, prefix)

        newsgroups = [name.strip().lower() for name in newsgroups]

        if not newsgroups and not quiet:
            parent.log.warning(
                f"No posting news group specified (expected {prefix}.newsgroup)"
            )

        from_header = parent.get(f"{prefix}.from", "transport@localhost.net")
        subject_header = parent.get(f"{prefix}.subject", "Unknown subject")

        poster = newstool.NewsPoster()
        poster.set_server(newsserver, port)
        poster.set_newsgroup(",".join(newsgroups))
        poster.set_enable(enable and newsgroups)
        poster.set_from(from_header)
        poster.set_subject(subject_header)
        poster.set_log(parent.log)

        for key, value in headers.items():
            poster.set_header(key, value)

        # Create the group if we need to

        control = newstool.NewsControl()
        control.set_server(newsserver, port)

        if creategroup:
            while parent.is_running():
                try:
                    self._create_newsgroups(parent, control, newsgroups)
                    break
                except socket.error as e:
                    parent.abort(
                        f"Error connecting to news server: {newsserver}:{port} {e}"
                    )
                except nntplib.NNTPError as e:
                    parent.abort(f"Error creating news group: {newsserver}:{port} {e}")
                except:  # pylint: disable=bare-except
                    parent.log.exception("Error creating group:")
                    parent.abort("Cannot create the posting newsgroup")

                parent.wait(15)

        return poster
