# Copyright (c) 2004, Marcel van Rensburg and Neil Rutherford.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
#  3. Neither the names of the copyright holders nor the names of the
#     contributors may be used to endorse or promote products derived from
#     this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNERS OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import socket
import asyncore
import re

from messages import nick, user, pong
from exceptions import connection, unhandled

class Connection(asyncore.dispatcher):

    def __init__(self, host, alias, name, mode, port=6667):
        asyncore.dispatcher.__init__(self)
        self.userRegistered = False
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.connect((host, port))
        except socket.error, inst:
            # need to work on this... I was thinkin something similar to the message handlers, 
            # like a dictionary of error codes linked to an exception class????
            #XXX: Temporary: if 61 (Connection refused) raise connection.Refused, else unhandled.ProtocolException
            if inst.args[0] == 61:
                raise connection.Refused(host)
            else:
                print inst.args[0]
                raise unhandled.ProtocolException(inst.args)
            
        self.tempOut = ''
        self.dataOut = ''
        self.dataIn = ''
        self.nick = alias
        self.name = name
        self.mode = mode
        self.serverOptions = {'SERVER': host,'SERVERVERSION': 'UNKNOWN', 'SERVERCREATED': 'UNKNOWN', 'PORT': port}
        self.channels = []

        # Must send NICK and USER messages to establish connection and
        # register the user.
        self.forceSendMsg(nick.NickMsg(self.nick))
        self.forceSendMsg(user.UserMsg(self.nick, self.mode, self.name))

        # By default, we respond to PING messages (by PONGing) 
        # 001 messages (by treating the user as registered)
        # 002 messages (by storing server name and version)
        # 003 messages (by storing compiled time of server)
        # 004 messages (by storing user and channel modes)
        # 005 messages (by storing all options supported by server)
        # NOTICE messages (by printing out the Notices)
        
        self.msgHandlers = {'PING': self.pingHandler,       # PING messages, respond with PONG
                            '001': self.welcomeHandler,     # welcome to irc network
                            '002': self.serverHandler,      # server name and version
                            '003': self.createdHandler,     # compiled date and time
                            '004': self.infoHandler,        # user and channel modes
                            '005': self.supportHandler,     # options present on server
                            '250': self.dummyHandler,       # highest connection count
                            '251': self.dummyHandler,       # no users on server
                            '252': self.dummyHandler,       # no operators online
                            '253': self.dummyHandler,       # unknown connections
                            '254': self.dummyHandler,       # no of channels formed
                            '255': self.dummyHandler,       # no of clients and servers
                            '265': self.dummyHandler,       # current local users
                            '266': self.dummyHandler,       # current global users
                            '375': self.dummyHandler,       # motd start
                            '372': self.dummyHandler,       # motd text
                            '376': self.ignoreHandler,      # motd end
                            '422': self.ignoreHandler,      # no motd
                            '332': self.ignoreHandler,      # topic
                            '333': self.ignoreHandler,      # unknown: channel founder I think not in rfc                   
                            '353': self.ignoreHandler,      # names list
                            '366': self.ignoreHandler,      # end of names list
                            '403': self.dummyHandler,       # no such channel
                            '404': self.ignoreHandler,      # cannot send to channel
                            '433': self.ignoreHandler,      # nick collision (TODO: need error checking)
                            '461': self.ignoreHandler,      # not enough parameters
                            '477': self.ignoreHandler,      # channel doesnt support modes (need registered nick???)
                            'MODE': self.dummyHandler,      # mode change (user or channel)
                            'JOIN': self.joinHandler,       # confirm join to channel
                            'QUIT': self.ignoreHandler,     # quit messages from other users
                            'KICK': self.ignoreHandler,     # kick message
                            'NICK': self.nickHandler,       # nick changes
                            'PART': self.partHandler,       # confirm leaving a channel
                            'ERROR': self.dummyHandler,     # error message handler, should be overriden
                            'PRIVMSG': self.dummyHandler,   # private message recv (to channel or client)
                            'TOPIC': self.ignoreHandler,    # topic message (when only person in topic)
                            'NOTICE': self.noticeHandler}   # server notices

    def registerHandler(self, command, handler):
        self.msgHandlers[command] = handler

    def unregisterHandler(self, command):
        if not self.msgHandlers.has_key(command):
            raise 'Not registered'
        del self.msgHandlers[command]

    def defaultHandler(self, prefix, command, args):
        raise 'Default handler called: ', command
    
    def nickHandler(self, prefix, args):
        user = prefix[:prefix.find('!')]
        if user == self.nick: 
            self.nick = args[0]
            
    def joinHandler(self, prefix, args):
        user = prefix[:prefix.find('!')]
        if user == self.nick: 
            self.channels.append(args[0].lower())
        
        print 'JOIN: ',' '.join(args)

    def partHandler(self, prefix, args):
        user = prefix[:prefix.find('!')]
        if user == self.nick: 
            self.channels.remove(args[0].lower())

        print 'PART: ',' '.join(args)

    def ignoreHandler(self, prefix, args):
        pass

    def callHandler(self, command, prefix='', args=''):
        if self.msgHandlers.has_key(command):
            self.msgHandlers[command](prefix, args)
        else:
            self.defaultHandler(prefix, command, args)

    def pingHandler(self, prefix, args):
        self.forceSendMsg(pong.PongMsg(args[0]))

    def welcomeHandler(self, prefix, args):
        self.userRegistered = True
        if self.tempOut:
            self.sendMsg(self.tempOut)
            del self.tempOut

    def serverHandler(self, prefix, args):
        # using regular expressions
        matches = re.match(r'^Your host is (\S+), running version (\S+)$',args[1])
        if matches:
            self.serverOptions['SERVER'] = matches.group(1)
            self.serverOptions['SERVERVERSION'] = matches.group(2)

    def createdHandler(self, prefix, args):
        matches = re.match(r'^This server was (cobbled together|created) ',args[1])
        if matches:
            self.serverOptions['SERVERCREATED'] = args[1][matches.end():]

    def infoHandler(self, prefix, args):
#       self.serverOptions['SERVER'] = args[1] # uncomment if want only the host name, not the host[ip/port] from message 002
        self.serverOptions['USERMODES'] = args[3]
        self.serverOptions['CHANNELMODES'] = args[4]

    def supportHandler(self, prefix, args):
        for arg in args[1:-3]:
            option = arg.split('=',1)
            if len(option) > 1:
                self.serverOptions[option[0]] = option[1]
            else:
                self.serverOptions[option[0]] = True

    def dummyHandler(self, prefix, args):
        print ' '.join(args)
        
    def noticeHandler(self, prefix, args):
        print 'SERVER NOTICE: ' + ' '.join(args)

    def handle_connect(self):
        """Called when connection established."""
        pass

    def handle_close(self):
        """Called when socket/connection is closed."""
        print 'Closed!'

    def handle_read(self):
        """Called when there is data to be read."""
        data = self.recv(512)
        if not data:
            self.close()
            return
     #   print '[<<<]\t', data
        self.dataIn += data

        # buffering... check if last message is complete
        lastEnd = self.dataIn.rfind('\r\n')
        if lastEnd == -1:
            return

        # Loop through messages, parse them and call the associated handler.
        for msg in self.dataIn[:lastEnd].split('\r\n'):
            msg.strip()

            # Make sure message is long enough.
            # This code also allows CR-LF messages to be sent and silently
            # ignored, as dictated by the standard. (2.3.1)
            if len(msg) <= 4:
                continue

            # Handle prefix if it exists.
            prefix = ''
            if msg.startswith(':'):
                endPrefix = msg.find(' ')
                prefix = msg[1:endPrefix]
                msg = msg[endPrefix+1:]

            # Extract the command.
            endCommand = msg.find(' ')
            command = msg[:endCommand]
            msg = msg[endCommand+1:]

            # Parse parameters if present.
            params = msg.split(' ', 14)
            if len(params) == 1 and not params[0]:
                params = []
            else:
                for i, item in enumerate(params):
                    if item.startswith(':'):
                        # A parameter has been found starting with a colon.
                        # This parameter, and any remaining parameters,
                        # must be joined.
                        finalparam = ' '.join(params[i:])
                        del params[i:]
                        params.append(finalparam[1:]) # Exclude colon.
                        break

            self.callHandler(command, prefix, params)

        self.dataIn = self.dataIn[lastEnd+2:] # Exclude '\r\n'.

    def handle_write(self):
        """Called when data has been sent"""
      #  print '[>>>]\t', self.dataOut
        sent = self.send(self.dataOut)
        self.dataOut = self.dataOut[sent:]

    def writable(self):
        """Indicates if anything needs to be written."""
        return len(self.dataOut) > 0

    def forceSendMsg(self, message):
        """Forces a message to be sent."""

        self.dataOut += str(message) + '\r\n'

    def sendMsg(self, message):
        """Queues a message for sending to the IRC server.

        Appends CRLF.
        """

        # Messages can only be 510 characters long. (512 with terminator.)
        if len(str(message)) >= 510:
            raise 'Message is too long. Must be no more than 510 characters.'

        if self.userRegistered:
            self.dataOut += str(message) + '\r\n'
        else:
            self.tempOut += str(message) + '\r\n'
