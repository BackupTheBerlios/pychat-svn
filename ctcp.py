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

from time import strftime, localtime

class protocol:
    def ctcpParse(self, prefix, args):
        print 'DEBUG: CTCP:', args
        # CTCP messages can be embedded... so have to find and remove them...
        ctcpMsgs = []
        # XXX: i think I should leave this the way it is... 
        # or I could neaten it up with a seperate variable, 
        # and then return that... what do you think?
        while args[1].count('\001') > 0:
            start = args[1].find('\001')
            end = args[1].find('\001', start+1)
            ctcpMsgs.append(args[1][start+1:end])
            args[1] = args[1][:start] + args[1][end+1:]

        for msg in ctcpMsgs:
            space = msg.find(' ')

            if space != -1:
                command = msg[:space]
                params = (msg[space+1:])
            else:
                command = msg
                params = ''

            self.ctcpCallHandler(prefix, command, params)

    def ctcpDefaultHandler(self, prefix, command, args):
        pass

    def ctcpCallHandler(self, prefix, command, args):
        try:
            getattr(self, "ctcpOn" + command.capitalize())(prefix, args)
        except AttributeError:
            self.ctcpDefaultHandler(prefix, command, args)

    def ctcpOnVersion(self, prefix, args):
        pass

    def ctcpOnDcc(self, prefix, args):
        print args
        user = prefix[:prefix.find('!')]
        params = args.split()
        if params[0] == 'CHAT':
            # just reject... up to client to override
            self.notice(user,'\001ERRMSG DCC CHAT Rejected\001')
            # uncomment to call dcc.protocol.dccChat()
#           self.dccChat(user, params[2],params[3]) 
        elif params[0] == 'SEND':
            # just reject... up to client to override
            self.notice(user,'\001ERRMSG DCC SEND %s Rejected\001' % params[1])
            # uncomment to call dcc.protocol.dccReceive()            
#           self.dccReceive(user, params[2], params[3], params[4], params[5]) 
        else:
            self.notice(user,'\001ERRMSG DCC %s Not Implemented\001' % params[0])

    def ctcpOnPing(self, prefix, args):
        user = prefix[:prefix.find('!')]
        self.notice(user,'\001PING %s\001' % args)

    def ctcpOnTime(self, prefix, args):
        user = prefix[:prefix.find('!')]
        self.notice(user,'\001TIME %s\001' % strftime("%a, %d %b %Y %H:%M:%S %Z", localtime()))
