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

from irc import protocol

class Bot(protocol.Connection):

    def __init__(self, host, nick='pyuser', name='test', mode=0):
        protocol.Connection.__init__(self, host, nick, name, mode)
        self.join('#bytehouse')
        self.authUsers = ['xor', 'iddqd']       # only respond to commands from
        self.options = {'VERSION': '0.01a', 'REVISION':'Revision 21'}

    def defaultNumericHandler(self, prefix, command, args):   # overriden from protocol
        if command == '433':
            print 'DEBUG: Nick Collision'
        else:
            print 'DEBUG: Unhandled num reply:', command

    def onError(self, prefix, args):
        print ' '.join(args)                                  # currently only prints out the args, needs to handle errors

    def onKick(self, prefix, args):
        protocol.Connection.onPart(self, prefix, args)
        print 'KICK: ', ' '.join(args)
        if args[1] == self.myNick:                              # if kicked rejoin channel
            self.channels.remove(args[0].lower())
            self.join(args[0])

    def onJoin(self, prefix, args):                      # XXX: super() doesnt work, its for types not classes apparently
        protocol.Connection.onJoin(self, prefix, args)     # call the protocol joinHandler, adds channel to channels list, ugly way of doing it :(
        user = prefix[:prefix.find('!')]
        if user != self.myNick:                                 # if not me, then welcome user
            if user.lower() in self.authUsers:
                self.privateMsg(args[0],'Welcome to %s, the all powerful %s, thank you for blessing us with your presence' % (args[0], user))
            else:
                self.privateMsg(args[0],'Welcome to %s, %s' % (args[0], user))
            
    def onPrivmsg(self, prefix, args):
        user = prefix[:prefix.find('!')]
        if user.lower() in self.authUsers:                          # is the message from an authorised user?
            if args[0] in self.channels:    
                if args[1].startswith(self.myNick + ':'):             # if from channel, then only process if proceeded by nick: or !nick:
                    args[1] = args[1][len(self.myNick)+1:].strip()    # strip nick:
                elif args[1].startswith('!' + self.myNick + ':'):     # if !nick: msg back to channel not user
                    args[1] = args[1][len(self.myNick)+2:].strip()    # strip !nick:
                    user = args[0]
                else:
                    return
               
            space = args[1].find(' ')                               # find space between command and parameters
            if space != -1:
                command = args[1][:space].upper()                   # grab the command
                params = args[1][space:].strip()                    # grab the params, strip any spaces between
            else:
                command = args[1].upper()                           # command is the whole message
                params = ''                                         # no parameters

            # logging - should be replaced in the near future... logging object/handler :) iddqd...

            print 'DEBUG: Remote Command %s from %s with parameters: %s' % (command, user, params)
            
            if command == 'QUIT':
                self.quit(params)                                   # send QUIT message
            elif command == 'SAY':                                  # allow talking through bot
                space = params.find(' ')                            # parse say params into   
                if space != -1:                                     # channel/user and message
                    dest = params[:space]
                    params = params[space:].strip()                   
                else:
                   self.privateMsg(user,'Error: Not enough parameters')
                self.privateMsg(dest,params)
            elif command == 'JOIN':                                 
                for param in params.split(','):                     # check if already on channel
                    if param.lower() in self.channels:
                        self.privateMsg(user,'ERROR: Already on channel: ' + param)
                        return
                
                self.join(params)                                   # send JOIN message
            elif command == 'LEAVE':
                space = params.find(' ')                            # parse leave params into   
                if space != -1:                                     # channels and leave message (if any)
                    chan = params[:space]
                    params = params[space:].strip()                   
                else:
                    chan = params
                    params = ''                  
                    
                if chan.lower() == 'all':                           # special case, send JOIN message
                    self.join(0)                                    # with a 0, leave all channels
                    return
                
                for ch in chan.split(','):                          # check if on channel
                    if ch.lower() not in self.channels:
                        self.privateMsg(user,'Error: Not on channel: ' + ch)
                        return

                self.leave(chan,params)                             # send PART message
            elif command == 'RENAME':
                self.nick(params)                                   # change NICK, send NICK message
            elif command == 'COMMANDS':
                self.privateMsg(user,'<begin commands>')
                self.privateMsg(user,'COMMANDS AVAILABLE:')
                self.privateMsg(user,'JOIN - join channel(s): JOIN <channel list (seperated by a comma)>')
                self.privateMsg(user,'LEAVE - leave channel(s): LEAVE <channel list (seperated by a comma)> <message>')
                self.privateMsg(user,'QUIT - quit server: QUIT <quit msg>')
                self.privateMsg(user,'STATS - displays stats: STATS')
                self.privateMsg(user,'SAY - speak through the bot: SAY <channel/user> <what to say>')
                self.privateMsg(user,'RENAME - changes the bots name: RENAME <new name>')     
                self.privateMsg(user,'<end commands>')
            elif command == 'STATS':
                self.privateMsg(user,'<begin stats>')
                self.privateMsg(user,'pychat Project: Python IRC Client')
                self.privateMsg(user,'http://pychat.berlios.de/')
                self.privateMsg(user,'NICK: ' + self.myNick)
                self.privateMsg(user,'NAME: ' + self.name) 
                self.privateMsg(user,'VERSION: ' + self.options['VERSION'])                 
                self.privateMsg(user,'REVISION: ' + self.options['REVISION'])                 
                self.privateMsg(user,'CHANNELS: ' + ','.join(self.channels))
                self.privateMsg(user,'This is a test bot written to test the functionality of the pychat protocol handler')
                self.privateMsg(user,'<end stats>')
            else:
                self.privateMsg(user,'Error: Unrecognized command: ' + command)  # error, not recognised
                
def main():
    a = Bot('za.shadowfire.org')
    protocol.asyncore.loop()

if __name__ == '__main__':
    main()
