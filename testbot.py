#!/usr/local/bin/python
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

import ConfigParser
from irc import protocol

class Bot(protocol.Connection):

    def __init__(self):
        self.authUsers = ['xor', 'iddqd'] # only respond to commands from
        self.options = {'VERSION': '0.01a', 'REVISION': 'Revision 21'}
        config = ConfigParser.ConfigParser()
        config.read('altleech.cfg')
        self.channels = config.get('altleech', 'channels').split()
        server = config.get('altleech', 'server')
        nick = config.get('altleech', 'nick')
        name = config.get('altleech', 'name')
        mode = config.getint('altleech', 'mode')
        self.rejoin = config.getboolean('altleech', 'rejoin_on_kick')
        self.reconnect = config.getboolean('altleech', 'reconnect_on_drop')
        protocol.Connection.__init__(self, server, nick, name, mode)

    def onRegister(self, prefix, args):
        for chan in channels:
            self.join(chan)

    def defaultNumericHandler(self, prefix, command, args):
        user = args[0]
        if user == self.nick:
            print '***', ' '.join(args[1:])

    def ctcpOnVersion(self, prefix, args): # TODO: hardcoded atm... must change later
        user = prefix[:prefix.find('!')]
        self.notice(user, '\001VERSION %s %s %s\001' % ('mIRC', 'v6.03', 'Khaled Mardam-Bey'))

    def onError(self, prefix, args):
        print ' '.join(args)   # currently only prints out the args,
                               # TODO: needs to handle errors

    def onNotice(self, prefix, args):
        print 'SERVER NOTICE:', ' '.join(args)

    def onKick(self, prefix, args):
        print 'KICK:', ' '.join(args)
        channel = args[0]
        user = args[1]
        if user == self.nick:
            self.channels.remove(channel.lower())
            if self.rejoin:
                self.join(channel)

    def onPart(self, prefix, args):
        user = prefix[:prefix.find('!')]
        channel = args[0]
        if user == self.nick:
            self.channels.remove(channel.lower())
        print 'PART:', ' '.join(args)

    def onJoin(self, prefix, args):
        user = prefix[:prefix.find('!')]
        channel = args[0]
        if user != self.nick:
            print 'JOIN:', ' '.join(args)
            if user.lower() in self.authUsers:
                self.privmsg(channel, 'Welcome to %s, the all powerful %s, thank you for blessing us with your presence' % (args[0], user))
            else:
                self.privmsg(channel, 'Welcome to %s, %s' % (channel, user))
        else:
            self.channels.append(channel.lower())

    def onPrivmsg(self, prefix, args):
        protocol.Connection.onPrivmsg(self, prefix, args)
        # is there a message left? After CTCP processing...
        if len(args[1]) == 0:
            return
        user = prefix[:prefix.find('!')]
        # is the message from an authorised user?
        if user.lower() in self.authUsers:
            if args[0] in self.channels:
            # if from channel,then only process if proceeded by nick: or !nick:
            # if nick, then respond to user from which msg originated
            # if !nick, then respond to channel
                if args[1].startswith(self.nick + ':'):
                    args[1] = args[1][len(self.nick)+1:].strip()
                elif args[1].startswith('!' + self.nick + ':'):
                    args[1] = args[1][len(self.nick)+2:].strip()
                    user = args[0]
                else:
                    return

            space = args[1].find(' ')
            if space != -1:
                command = args[1][:space].upper()
                params = args[1][space:].strip()
            else:
                command = args[1].upper()
                params = ''

            print 'DEBUG: Remote Command %s from %s with parameters: %s' % (command, user, params)

            if command == 'QUIT':
                self.quit(params)
            elif command == 'SAY':
                space = params.find(' ')
                if space != -1:
                    dest = params[:space]
                    params = params[space:].strip()
                else:
                   self.privmsg(user, 'Error: Not enough parameters')
                self.privmsg(dest, params)
            elif command == 'JOIN':
                for param in params.split(','):
                    if param.lower() in self.channels:
                        self.privmsg(user, 'ERROR: Already on channel: ' + param)
                        return

                self.join(params)
            elif command == 'LEAVE':
                space = params.find(' ')
                if space != -1:
                    chan = params[:space]
                    params = params[space:].strip()
                else:
                    chan = params
                    params = ''

                if chan.lower() == 'all':
                    self.join(0)
                    return

                for ch in chan.split(','):
                    if ch.lower() not in self.channels:
                        self.privmsg(user, 'Error: Not on channel: ' + ch)
                        return

                self.part(chan, params)
            elif command == 'RENAME':
                self.newnick(params)
            elif command == 'COMMANDS':
                self.privmsg(user, '<begin commands>')
                self.privmsg(user, 'COMMANDS AVAILABLE:')
                self.privmsg(user, 'JOIN - join channel(s): JOIN <channel list (seperated by a comma)>')
                self.privmsg(user, 'LEAVE - leave channel(s): LEAVE <channel list (seperated by a comma)> <message>')
                self.privmsg(user, 'QUIT - quit server: QUIT <quit msg>')
                self.privmsg(user, 'STATS - displays stats: STATS')
                self.privmsg(user, 'SAY - speak through the bot: SAY <channel/user> <what to say>')
                self.privmsg(user, 'RENAME - changes the bots name: RENAME <new name>')
                self.privmsg(user, '<end commands>')
            elif command == 'STATS':
                self.privmsg(user, '<begin stats>')
                self.privmsg(user, 'pychat Project: Python IRC Client')
                self.privmsg(user, 'http://pychat.berlios.de/')
                self.privmsg(user, 'NICK: ' + self.nick)
                self.privmsg(user, 'NAME: ' + self.name)
                self.privmsg(user, 'VERSION: ' + self.options['VERSION'])
                self.privmsg(user, 'REVISION: ' + self.options['REVISION'])
                self.privmsg(user, 'CHANNELS: ' + ','.join(self.channels))
                self.privmsg(user, 'This is a test bot written to test the functionality of the pychat protocol handler')
                self.privmsg(user, '<end stats>')
            else:
                self.privmsg(user, 'Error: Unrecognized command: ' + command) 

def main():
    a = Bot()
    protocol.asyncore.loop()

if __name__ == '__main__':
    main()
