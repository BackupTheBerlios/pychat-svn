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

from messages import nick, user, pong

class Connection(asyncore.dispatcher):

    def __init__(self, host, alias, name, mode, port=6667):
        asyncore.dispatcher.__init__(self)
        self.userRegistered = False
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.tempOut = ''
        self.dataOut = ''
        self.dataIn = ''
        self.nick = alias
        self.name = name
        self.mode = mode

        # Must send NICK and USER messages to establish connection and
        # register the user.
        self.forceSendMsg(nick.NickMsg(self.nick))
        self.forceSendMsg(user.UserMsg(self.nick, self.mode, self.name))

        # By default, we respond to PING messages (by PONGing) and 001
        # messages (by treating the user as registered).
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
        self.forceSendMsg(pong.PongMsg(args[0]))

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
            if len(params) == 15:
                # If the last parameter starts with a colon, remove it.
                if params[14].startswith(':'):
                    params[14] = params[14][1:]
            else:
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
        print '[>>>]\t', self.dataOut
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

