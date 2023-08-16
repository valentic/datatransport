#!/usr/bin/env python

#####################################################################
#
#   Demonstation of the eventmonitor class
#
#   Track the up/down state of servers.
#
#   2009-04-30  Todd Valentic
#               Initial implementation.
#
#####################################################################

from Transport              import ProcessClient
from Transport              import ConfigComponent
from Transport.Components   import EventMonitor

import sys
import os
import commands
import StringIO
import pytz
import datetime
import random

#####################################################################
#
#   Each thing that we track inherits from EventMonitor.Member.
#   It is a standard ConfigComponent. You need to define the
#   different states that are tracked in the "states" option.
#   The initial state is in states.unknown (and defaults to
#   "unknown"). It is not necessary to list the unknown state
#   in the states list, it will added automatically if it isn't
#   there.
#
#   The full list of options is:
#
#       .states = space separated list of names
#       .states.unknown = name of undefined state
#       .maxhistory = number of previous transitions to keep
#
#   The class needs to respond to save() and load() calls which
#   saves the state into a DefaultConfigParser object. You can
#   track class-specific information and save into the config
#   object as well.
#
#####################################################################

class Host(EventMonitor.Member):

    def __init__(self,*pos,**kw):
        EventMonitor.Member.__init__(self,'host',*pos,**kw)

        self.hostname   = self.get('hostname',self.name)
        self.label      = self.get('label',self.name)
        self.loadlevel  = 0

    def save(self,config):
        EventMonitor.Member.save(self,config)

        config.set(self.name,'host.name',self.hostname)
        config.set(self.name,'host.label',self.label)

        config.set(self.name,'loadlevel',str(self.loadlevel))

    def load(self,config):
        EventMonitor.Member.load(self,config)

        self.levelload = config.getfloat(self.name,'loadlevel',0.0)

    def check(self,up):

        if up:
            self.loadlevel = random.randrange(10)
            self.update('online')
        else:
            self.update('offline')
            self.loadlevel = 0

#####################################################################
#
#   Main application class
#
#   Include an EventMonitor() oject for tracking. Pass it a
#   dictionary of EventMontiorMembers, which can be obtained
#   from getComponentsDict().
#
#####################################################################

class HostMonitor (ProcessClient):

    def __init__(self,argv):
        ProcessClient.__init__(self,argv)

        self.hosts      = self.getComponentsDict('hosts',Host)
        self.tracker    = EventMonitor.EventMonitor(self.hosts)

        self.log.info('Target hosts:')
        for name,host in self.hosts.items():
            self.log.info('  - %s (%s)' % (name,host.hostname))

        # For testing, we want to start with a clean slate.
        # Normally, you would load the tracker state here.

        # self.loadTracker()

    def loadTracker(self):
        self.tracker.load('tracker')

    def saveTracker(self):
        self.tracker.save('tracker')

        # Post results to news groups here...

    def run(self):

        self.log.info('Setting server1 online, server2 offline')
        self.hosts['server1'].update('online')
        self.hosts['server2'].update('offline')

        self.log.info('Tracker changes: %s' % self.tracker.changed())

        self.wait(2)

        self.log.info('Setting server3 offline, server3 online')
        self.hosts['server1'].update('online')
        self.hosts['server2'].update('offline')
        self.hosts['server3'].update('offline')
        self.hosts['server3'].update('online')

        self.log.info('Tracker changes: %s' % self.tracker.changed())

        self.log.info('Current State:')

        for host in self.hosts.values():
            curState = host.curState
            self.log.info('  %s' % host.name)
            self.log.info('  %s' % curState)
            self.log.info('    start: %s' % host.states[curState].starttime)
            self.log.info('    elapsed: %s' % host.states[curState].elapsed)
            self.log.info('  history:')

            for entry in host.history:
                self.log.info('    %s' % entry)

        self.saveTracker()

        self.exit('Finished')

if __name__ == '__main__':
    HostMonitor(sys.argv).run()
