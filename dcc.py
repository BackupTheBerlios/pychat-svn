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
import struct

class protocol:
    def dccChat(self, user, host, port):
        raise "Not Done Yet... Try again later..."
    
    def dccReceive(self, user, host, filename, port, size):
#       raise "Not Done Yet... Try again later..."
        
        #XXX: Really *buggy* code, basic idea from internet source...
        # http://www.zob.ne.jp/~hide-t/comp/mysoftware/dccrecv.py
        #
        #TODO: should rewrite the code to use asyncore or threads
        #
        
        IP = '%d.%d.%d.%d' % struct.unpack('>BBBB', struct.pack('>L', host))
        
        print 'DEBUG: DCC RECV %s From %s' % (filename,IP)
        
        dccCon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dccCon.connect((IP, port))
        rFile = open(filename, 'wb')

        received = 0
        remain = size
        while remain:
            data = dccCon.recv(remain)
            if not data: break
            rFile.write(data)
            received = received + len(data)
            dccCon.send(struct.pack('!i', received))
            remain = size - received
            print 'DEBUG: DCC RECV: (%i recv, %i left)' % (received, remain)
        
        dccCon.close()
        rFile.close()

        print 'DEBUG: DCC RECV Finished'
