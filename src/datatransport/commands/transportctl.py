#!/usr/bin/env python

############################################################################
#
#   transportctl
#
#   This script controls the transport server from the command line.
#
#   History:
#
#   1.0.0   1999.??.??  TAV
#           Initial implementation
#
#   1.2.0   2000.04.20  TAV
#           Updated to use omniORB for CORBA functions.
#
#   1.3.0   2000-06-22  TAV
#           Added ability to change options for the web-site users.
#
#   1.3.1   2000-08-08  TAV
#           Fixed bug if no option given on command line, call help.
#
#   1.3.2   2001-08-29  TAV
#           Handle new list of config files in the ProcessGroupInfo struct.
#
#   1.3.3   2001-10-23  TAV
#           Fixed a bug in the "user set" command. The user's values were
#               being reset to the defaults with each change.
#
#   1.3.4   2002-02-11  Todd Valentic
#           Added ability to pass args to start client command.
#
#   1.3.5   2002-08-28  Todd Valentic
#           Setup via configure script
#           sri.transport -> Transport
#           Removed web-site user functions.
#
#   1.3.6   2004-08-16  Todd Valentic
#           Cleanup for XML-RPC.
#           Removed log rotation.
#           Removed TransportClient.
#
#   2016-12-23  Todd Valentic
#               Migrate to datatransport package format
#
#   2020-10-09  Todd Valentic
#               Python3: xmlrpc.client
#               Python3: print
#
############################################################################

from datatransport import TransportConfig

import os
import shutil
import subprocess
import sys
import time
import xmlrpc.client

class TransportControl:

    def __init__(self):

        self.command = {    'help':     self.help,
                            'list':     self.list,
                            'status':   self.status,
                            'cleanup':  self.cleanup,
                            'reload':   self.reload,
                            'add':      self.addGroup,
                            'remove':   self.removeGroup,
                            'restart':  self.restart,
                            'start':    self.start,
                            'stop':     self.stop       }

    def help(self):

        print()
        print('-'*70)
        print('Transport Control Commands:')
        print('-'*70)
        print('\thelp                     - Show this page')
        print('\tstatus                   - Transport server status')
        print('\tloglevel                 - Set log level on group or server')
        print('\treload <group>           - Reload group\'s config file')
        print('\treload server            - Reload process groups')
        print('\tlist                     - List all process groups')
        print('\tlist <group>             - List clients in a group')
        print('\tstart <group>            - Start a process group')
        print('\tstop <group>             - Stop a process group')
        print('\trestart <group>          - Stop/start a process group')
        print('\tadd <group>              - Notify server of new group')
        print('\tremove <group>           - Remove a group from the server')
        print('\tstart server             - Start the transport server')
        print('\tstop server              - Stop the transport server')
        print('\tstart <group> <client>   - Start the client in group')
        print('\tstop <group> <client>    - Stop the client in group')
        print('\tcleanup                  - Remove processes after crash')
        print('-'*70)
        print()

    def runCommand(self,argv):

        if len(argv)<2:
            self.help()
            sys.exit(1)

        cmd = argv[1]
        arg = argv[2:]

        if cmd not in self.command:
            print("Unknown command:",cmd)
            self.help()
            return 1

        if cmd=='cleanup':
            self.cleanup()
            return 0
        elif cmd=='help':
            self.help()
            return

        url = TransportConfig().get('TransportServer','url')
        self.server = xmlrpc.client.ServerProxy(url)

        if not (cmd=='start' and len(arg)==1 and arg[0]=='server'):
            # Skip if we need to start the server

            try:
                self.server.status()
            except:
                print("Cannot connect to the transport server")
                return 1

        return self.command[cmd](arg)

    def printProcessGroup(self,group):
        print(group)
        return

        info = group._get_info()

        print('[%s]' % info.name)
        print('\tRunning      :',info.running)
        print('\tLabel        :',info.label)
        print('\tConfig files :',info.configFiles[0])
        for name in info.configFiles[1:]:
            print('\t             :',name)
        print('\tLog          :',info.log)
        print('\tStatus       :',info.status)

    def printProcessClient(self,client):
        print(client)
        return

        print('[%s]' % client.name)
        print('\tRunning      :',client.running)
        print('\tLabel        :',client.label)
        print('\tProcess ID   :',client.pid)
        print('\tStatus       :',client.status)

    def status(self,arg):
        print('Server status:',self.server.status())
        return 0

    def reload(self,arg):

        if arg==[]:
            print('You need to specify a process group or "server"')
            return 1

        if arg[0]=='server':
            self.server.reloadgroups()
            return 0

        group  = arg[0]

        try:
            self.server.reloadgroup(group)
        except:
            print('The process group "%s" does not exist' % group)
            print('  Use the "list" command to print the available groups')
            return 1

        return 0

    def addGroup(self,arg):

        if arg==[]:
            print('You need to specify a process group')
            return 1

        try:
            self.server.addgroup(arg[0])
        except:
            print('There was a problem adding the group "%s"' % arg[0])
            return 1

        return 0

    def removeGroup(self,arg):

        if arg==[]:
            print('You need to specify a process group')
            return 1

        try:
            self.server.removegroup(arg[0])
        except:
            print('There was a problem remove the group "%s"' % arg[0])
            return 1

        return 0

    def list(self,arg):
        if len(arg)==1:
            return self.listClients(arg[0])
        else:
            return self.listGroups()

    def listClients(self,group):
        groups = self.server.listgroups()

        if group not in groups:
            print('The process group "%s" does not exist' % group)
            print('  Use the "list" command to print the available groups')
            return 1

        clients = self.server.listclients(group)
        print('There are',len(clients),'clients listed for the group',group)
        for client,info in clients.items():
            #self.printProcessClient(client)
            print(client,info)
        return 0

    def listGroups(self):
        groups = self.server.listgroups()
        if not groups:
            print('No process groups are registered')
        else:
            print('There are',len(groups),'groups are registered:')
            for group,label in groups.items():
                print('%20s - %s' % (group,label))
                #self.printProcessGroup(group)
        return 0

    def startClient(self,group,client,args):

        groups = self.server.listgroups()

        if group not in groups:
            print('The process group "%s" does not exist' % group)
            print('  Use the "list" command to print the available groups')
            return 1

        try:
            self.server.startclient(group,client,args)
        except:
            print('The client "%s" does not exist' % client)
            return 1

        return 0

    def stopClient(self,group,client):

        groups = self.server.listgroups()

        if group not in groups:
            print('The process group "%s" does not exist' % group)
            print('  Use the "list" command to print the available groups')
            return 1

        try:
            self.server.stopclient(group,client)
        except:
            print('The client "%s" does not exsit' % client)
            return 1

        return 0

    def start_server(self):
        args = [shutil.which("transportd"), "-b"]
        subprocess.Popen(args)

    def start(self,arg):

        if len(arg)==0:
            print('You need to specify the group name or "server"')
            return 1

        if len(arg)==1 and arg[0]=='server':
            return self.start_server()

        if len(arg)>1:
            if len(arg)==3:
                args=arg[2]
            else:
                args=''
            return self.startClient(arg[0],arg[1],args)

        name = arg[0]

        try:
            self.server.startgroup(name)
        except:
            print('The process group "%s" does not exist' % name)
            print('  Use the "list" command to print the available groups')
            return 1

        print('Group started:',name)

        return 0

    def stop(self,arg):

        if len(arg)==0:
            print('You need to provide a group name or server')
            return 1

        elif len(arg)==2:
            self.stopClient(arg[0],arg[1])

        elif arg[0]=='server':
            self.server.stop()
            time.sleep(1)

        else:
            name = arg[0]

            try:
                self.server.stopgroup(name)
            except:
                print('The process group "%s" does not exist' % name)
                print('  Use the "list" command to print the available groups')
                return 1

            print('Group stopped:',name)

        return 0

    def restart(self,arg):
        self.stop(arg)
        self.start(arg)

    def cleanup(self):

        uid = TransportConfig().uid

        for file in os.listdir('/proc'):
            data = {}
            try:
                for line in open('/proc/%s/status' % file).readlines():
                    key,value = line.split(':')
                    data[key] = value.strip()
            except:
                continue

            if uid != int(data['Uid'].split()[0]):
                continue

            pid = int(data['Pid'])

            print('Stopping %5d - ' % pid,end=' ')
            try:
                os.kill(pid,9)
                print('OK')
            except:
                print('Could not kill process')

        print('Finished')

        return 0

def main():

    try:
        control = TransportControl()
        sys.exit(control.runCommand(sys.argv))
    except KeyboardInterrupt:
        print("*** BREAK ***")
        sys.exit(1)


