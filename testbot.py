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
from irc.messages import join,quit,priv,nick,leave

class Bot(protocol.Connection):

    def __init__(self, host, nick='pyuser', name='test', mode=0):
        protocol.Connection.__init__(self, host, nick, name, mode)
        self.registerHandler('PRIVMSG', self.privmsgHandler)  # overrides the one in protocol.py
        self.registerHandler('ERROR', self.errorHandler)      # overrides the one in protocol.py
        self.registerHandler('KICK', self.kickHandler)        # overrides the one in protocol.py
        self.registerHandler('JOIN', self.joinHandler)        # overrides the one in protocol.py
        self.registerHandler('433', self.collisionHandler)    # overrides the one in protocol.py
        self.sendMsg(join.JoinMsg('#bytehouse'))
        self.authUsers = ['xor','iddqd','dickshinnery']       # only respond to commands from
        self.options = {'VERSION': '0.01a', 'REVISION':'Revision 16'}

    def collisonHandler(self, prefix, args):                  # TODO: actually handle this somehow, for the moment just output error...
        print 'DEBUG: Nick Collision'


    def errorHandler(self, prefix, args):
        print ' '.join(args)                                  # currently only prints out the args, needs to handle errors

    def kickHandler(self, prefix, args):
        print 'KICK: ', ' '.join(args)
        if args[1] == self.nick:                              # if kicked rejoin channel
            self.sendMsg(join.JoinMsg(args[0]))

    def joinHandler(self, prefix, args):                      # XXX: super() doesnt work, its for types not classes apparently
        protocol.Connection.joinHandler(self,prefix,args)     # call the protocol joinHandler, adds channel to channels list, ugly way of doing it :(
        user = prefix[:prefix.find('!')]
        if user != self.nick:                                 # if not me, then welcome user
            if user.lower() in self.authUsers:
                self.sendMsg(priv.PrivMsg(args[0],'Welcome to %s, the all powerful %s, thank you for blessing us with your presence' % (args[0], user)))    
            else:
                self.sendMsg(priv.PrivMsg(args[0],'Welcome to %s, %s' % (args[0], user)))
            
    def privmsgHandler(self, prefix, args):
        user = prefix[:prefix.find('!')]
        if user.lower() in self.authUsers:                          # is the message from an authorised user?
            if args[0] in self.channels:    
                if args[1].startswith(self.nick + ':'):             # if from channel, then only process if proceeded by nick: or !nick:
                    args[1] = args[1][len(self.nick)+1:].strip()    # strip nick:
                elif args[1].startswith('!' + self.nick + ':'):     # if !nick: msg back to channel not user
                    args[1] = args[1][len(self.nick)+2:].strip()    # strip !nick:
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
                self.sendMsg(quit.QuitMsg(params))                  # send QUIT message
            elif command == 'SAY':                                  # allow talking through bot
                space = params.find(' ')                            # parse say params into   
                if space != -1:                                     # channel/user and message
                    dest = params[:space]
                    params = params[space:].strip()                   
                else:
                   self.sendMsg(priv.PrivMsg(user,'Error: Not enough parameters'))
                self.sendMsg(priv.PrivMsg(dest,params))
            elif command == 'JOIN':                                 
                for param in params.split(','):                     # check if already on channel
                    if param.lower() in self.channels:
                        self.sendMsg(priv.PrivMsg(user,'ERROR: Already on channel: ' + param))
                        return
                
                self.sendMsg(join.JoinMsg(params))                  # send JOIN message
            elif command == 'LEAVE':
                space = params.find(' ')                            # parse leave params into   
                if space != -1:                                     # channels and leave message (if any)
                    chan = params[:space]
                    params = params[space:].strip()                   
                else:
                    chan = params
                    params = ''                  
                    
                if chan.lower() == 'all':                           # special case, send JOIN message
                    self.sendMsg(join.JoinMsg(0))                   # with a 0, leave all channels
                    return
                
                for ch in chan.split(','):                          # check if on channel
                    if ch.lower() not in self.channels:
                        self.sendMsg(priv.PrivMsg(user,'Error: Not on channel: ' + ch))
                        return

                self.sendMsg(leave.LeaveMsg(chan,params))           # send PART message
            elif command == 'RENAME':
                self.sendMsg(nick.NickMsg(params))                  # change NICK, send NICK message
            elif command == 'COMMANDS':
                self.sendMsg(priv.PrivMsg(user,'<begin commands>')) 
                self.sendMsg(priv.PrivMsg(user,'COMMANDS AVAILABLE:'))
                self.sendMsg(priv.PrivMsg(user,'JOIN - join channel(s): JOIN <channel list (seperated by a comma)>'))
                self.sendMsg(priv.PrivMsg(user,'LEAVE - leave channel(s): LEAVE <channel list (seperated by a comma)> <message>'))
                self.sendMsg(priv.PrivMsg(user,'QUIT - quit server: QUIT <quit msg>'))
                self.sendMsg(priv.PrivMsg(user,'STATS - displays stats: STATS'))
                self.sendMsg(priv.PrivMsg(user,'SAY - speak through the bot: SAY <channel/user> <what to say>'))
                self.sendMsg(priv.PrivMsg(user,'RENAME - changes the bots name: RENAME <new name>'))                
                self.sendMsg(priv.PrivMsg(user,'<end commands>')) 
            elif command == 'STATS':
                self.sendMsg(priv.PrivMsg(user,'<begin stats>')) 
                self.sendMsg(priv.PrivMsg(user,'pychat Project: Python IRC Client')) 
                self.sendMsg(priv.PrivMsg(user,'http://pychat.berlios.de/'))
                self.sendMsg(priv.PrivMsg(user,'NICK: ' + self.nick)) 
                self.sendMsg(priv.PrivMsg(user,'NAME: ' + self.name)) 
                self.sendMsg(priv.PrivMsg(user,'VERSION: ' + self.options['VERSION']))                 
                self.sendMsg(priv.PrivMsg(user,'REVISION: ' + self.options['REVISION']))                 
                self.sendMsg(priv.PrivMsg(user,'SERVER: ' + self.serverOptions['SERVER'])) 
                self.sendMsg(priv.PrivMsg(user,'SERVERPORT: ' + str(self.serverOptions['PORT']))) 
                self.sendMsg(priv.PrivMsg(user,'SERVERVERSION: ' + self.serverOptions['SERVERVERSION'])) 
                self.sendMsg(priv.PrivMsg(user,'SERVERCREATED: ' + self.serverOptions['SERVERCREATED'])) 
                self.sendMsg(priv.PrivMsg(user,'CHANNELS: ' + ','.join(self.channels)))
                self.sendMsg(priv.PrivMsg(user,'This is a test bot written to test the functionality of the pychat protocol handler'))
                self.sendMsg(priv.PrivMsg(user,'<end stats>')) 
            else:
                self.sendMsg(priv.PrivMsg(user,'Error: Unrecognized command: ' + command))  # error, not recognised
                
def main():
    a = Bot('za.shadowfire.org')
    protocol.asyncore.loop()

if __name__ == '__main__':
    main()
