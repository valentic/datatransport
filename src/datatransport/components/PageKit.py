#!/usr/bin/env python

#############################################################################
#
# Name:     PageKit
# Author:   Todd Valentic
# Company:  SRI International
#
# Purpose:  Base HTML page class for the transport network's dynamically
#           created pages.
#
# History:
#
#   1.0.0   1999-10-06  TAV
#           Initial implementation.
#
#   2.0.0   2000-03-13  TAV
#           Major cleanup and simplification (TransportPage disappeared).
#
#   2.0.1   2000-06-16  TAV
#           Added ability to delete as user.
#
#   2.0.2   2000-07-03  TAV
#           Added Boulder and Platteville to site name list (this *really*
#               needs to be fixed up and extracted outside of this file).
#
#   2.0.3   2000-08-15  TAV
#           Added Summitcamp to site name list. When am I going to fix this?
#
#   2.0.4   2001-05-02  TAV
#           Added SouthPole to site name list.
#
#   2.0.5   2001-10-23  TAV
#           Added the concept of user "roles" to generalize the admin
#               privledges, similar to a unix user's groups.
#
#   2.0.6   2001-11-09  TAV
#           Added InfoMessage class.
#
#   2.0.7   2001-12-26  TAV
#           Changed tav -> sri
#
#   2.0.8   2002-08-28  Todd Valentic
#           sri.transport -> Transport
#
#   3.0.0   2002-08-28  Todd Valentic
#           Reduced to basic layout tool.
#           Removed user features.
#
#   3.2.0   2002-11-11  Todd Valentic
#           Updated to modern stylesheet format.
#           Major code cleanup.
#
#   2022-10-07  Todd Valentic
#               Reorder imports
#               Python3 updates
#                   print()
#
#############################################################################

import sys

from datatransport import TransportConfig


class Navbar:
    def __init__(self):

        self.choices = []
        self.title = "Navigation"

    def add_choice(self, label, url):
        self.choices.append((label, url))

    def show(self):

        print("<div id=navbar>")
        print("<h4>%s</h4>" % self.title)

        for name, ref in self.choices:
            print('<a href="%s">%s</a>' % (ref, name))

        print("</div>")


class Table:
    def __init__(self, width="100%", title=""):

        self.width = width
        self.cellspacing = 2
        self.cellpadding = 5
        self.title = title
        self.title_class = "title"
        self.table_class = "table"
        self.num_cols = 1

    def show(self):

        print("<table class=%s cellspacing=%d>" % (self.table_class, self.cellspacing))

        if self.title:
            print("<tr>")
            print("<th class=%s colspan=%d>" % (self.title_class, self.num_cols))
            print(self.title)
            print("</th>")
            print("</tr>")

        self.body()

        print("</table>")

    def body(self):
        pass

    def save(self, filename):
        tmp = sys.stdout
        sys.stdout = open(filename, "w")
        self.show()
        sys.stdout.close()
        sys.stdout = tmp


class ErrorMessage(Table):
    def __init__(self, msg="We have a problem", title="ERROR"):
        Table.__init__(self, title=title)

        self.msg = msg
        self.table_class = "errorTable"

    def body(self):
        print("<tr><td>%s</td></tr>" % self.msg)


class InfoMessage(Table):
    def __init__(self, msg="", title="INFORMATION", form=0):
        Table.__init__(self, title=title)

        self.form = form
        self.msg = msg
        self.table_class = "infoTable"

    def body(self):
        print("<tr><td>%s</td></tr>" % self.msg)


class Page:
    def __init__(self):

        sys.stderr = sys.stdout

        self.config = TransportConfig()
        self.sitedesc = self.config.get("DEFAULT", "sitedesc")

        self.refreshrate = 600
        self.stylesheet = "/stylesheet.css"
        self.title = self.sitedesc
        self.header = "DATA TRANSPORT NETWORK"
        self.doctype = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">'

        self.navbar = Navbar()

    def headers(self):
        print("Content-type: text/html")

        if self.refreshrate:
            print("Refresh:", self.refreshrate)

    def head(self):
        print("<head>")
        print("<title>%s</title>" % self.title)
        print(
            '<style type="text/css"><!-- @import url(%s); --></style>' % self.stylesheet
        )
        print("</head>")

    def banner(self):

        print("<span id=title>%s</span><br>" % self.header)
        print("<span id=site>%s</span><br>" % self.sitedesc)

    def sidebar(self):

        if self.navbar:
            self.navbar.show()

    def body(self):
        pass

    def footer(self):
        return

        website = "http://transport.sri.com/TransportDevel"

        print('<a href="%s">Data Transport Network</a><br>' % website)
        print("<span>Copyright (C) 2002  SRI International</span>")

    def show(self):

        # print('Content-type: text/plain')
        # print()

        self.headers()

        print()
        print(self.doctype)
        print("<html>")
        self.head()
        print("<body>")

        print("<h1 id=banner>")
        self.banner()
        print("</h1>")

        print("<div id=content>")
        print("<div class=spacer></div>")

        print("<div id=sidebar>")
        self.sidebar()
        print("</div>")

        print("<div id=main>")
        print('<a name="pagetop"></a>')
        self.body()
        print("</div>")

        print("<div class=spacer></div>")
        print("</div>")

        print("<div id=footer>")
        self.footer()
        print("</div>")

        print("</body>")
        print("</html>")


def main():
    # Used as a component in other classes
    Page().show()
