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
import string
import sys

from messages import nick, user, pong

class Connection(asyncore.dispatcher):

    def __init__(self, host, alias, name, mode, port=6667):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.dataOut = ''
        self.dataIn = ''
        self.nick = alias
        self.name = name
        self.mode = mode
        self.sendMsg(nick.NickMsg(self.nick))
        self.sendMsg(user.UserMsg(self.nick, self.mode, self.name))

        # Must send NICK and USER messages to establish connection and
        # register the user.
        self.forceSendMsg(nick.NickMsg(self.nick))
        self.forceSendMsg(user.UserMsg(self.nick, self.mode, self.name))

        # By default, we process PING, 376, and 422 messages.
        self.msgHandlers = {'PING': self.pingHandler,
                            '001': self.welcomeHandler}

    def registerHandler(self, command, handler):
        self.msgHandlers[command] = handler

    def unregisterHandler(self, command):
        if not self.msgHandlers.has_key(command):
            raise 'Not registered'
        del self.msgHandlers[command]

    def defaultHandler(self, prefix, command, args):
        #raise 'Default handler called'
        #XXX: passing for now...
        pass

    def callHandler(self, command, prefix='', args=''):
        if self.msgHandlers.has_key(command):
            self.msgHandlers[command](prefix, args)
        else:
            self.defaultHandler(prefix, command, args)

    def pingHandler(self, prefix, args):
        self.sendMsg(pong.PongMsg(args[0]))

    def welcomeHandler(self, prefix, args):
        self.userRegistered = True
        if self.tempOut:
            self.sendMsg(self.tempOut)
            del self.tempOut

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
        print '[<<<]\t', data
        self.dataIn += data

        # buffering... check if last message is complete
        lastEnd = self.dataIn.rfind('\r\n')
        if lastEnd == -1:
            return

        # Loop through messages, parse them and call the associated handler.
        for msg in self.dataIn[:lastEnd].split('\r\n'):
            msg.strip()

            # Reset variables between iterations.
            command = ''
            prefix = ''
            arguments = ''

            # Make sure message is valid.
            # Continuing here allows us to silently ignore CR-LF pairs between
            # messages, which is dictated by the standard. (2.3.1)
            if len(msg) <= 4:
                continue

            # Handle prefix if it exists.
            if msg.startswith(':'):
                endPrefix = msg.find(' ')
                prefix = msg[1:endPrefix]
                msg = msg[endPrefix+1:]

            endCommand = msg.find(' ')
            command = msg[:endCommand]
            msg = msg[endCommand+1:]
#
# Argument parser... 
# ---> iddqd should we move this to a seperate file/class?
# ---> I think it is fine where it is
# ---> (Marcel): what are the benefits of moving it?!??
#
# Developer Note (XoR):
# (IRC Protocol arguments: no more than 15 arguments)
#
# Based on my limited knowledge of BNF notation, I deduce there are 2 ways arguments 
# have to parsed, as they can occur in 2 different formats, namely:
#
# First type: n number of args then : and the rest which is treated as one 
# (in this type n <= 14 and : must be present)
#
# Second type 14 arguments a space and more text, as there are 14 arguments preceding
# the rest of the text, the : is not necessary however everything following the 14th
# argument is treated as one argument
#

# Neil, for comments on your above idea and your logic below
            if len(msg) > 1:
                trailBeg = msg.find(':')
                if trailBeg == 0:
                    # The rest of the message is a single argument.
                    # Skip the leading colon.
                    arguments = [msg[1:]]
                elif trailBeg != -1:
                    # case 1 or 2
                    trailing = msg[trailBeg+1:]
                    msg = msg[:trailBeg].strip()
                    arguments = msg.split(' ').append(trailing)
                else:
                    # has to be case 2...
                    # if there is no :, we are either not bothered with n > 14
                    # or there is no argument containing spaces, so if we split a max
                    # of 14 times, then anything after 14 will be joined together
                    arguments = msg.split(' ', 14)

            self.callHandler(command, prefix, arguments)

        self.dataIn = self.dataIn[lastEnd+2:] # skip '\r\n'

    def handle_write(self):
        """Called when data has been sent"""
        print '[>>>]\t', self.dataOut
        sent = self.send(self.dataOut)
        self.dataOut = self.dataOut[sent:]

    def writable(self):
        """Indicates if anything needs to be written."""
        return len(self.dataOut) > 0

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

