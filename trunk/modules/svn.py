# Copyright (c) 2005, Marcel van Rensburg and Neil Rutherford.
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

# system imports
from time import asctime, localtime

#pysvn imports
from pysvn import Client, Revision, opt_revision_kind, ClientError

class SVNInterface: #XXX: for Testing pysvn, add new features as desired
        """
            Provides an interface to SVN repositories
        """

        def __init__(self, repo):
            self.repo = repo
            self.client = Client()

        def lastRev(self):
            ret = self.lastLog()
            if ret == 'Error connecting to SVN repo':
                return -1
            else:
                return ret[0]['revision']
                
        def lastLog(self, num=1, files=False):
            
            if num == 1:
                end = Revision(opt_revision_kind.head)
            else:
                end = Revision(opt_revision_kind.number, int(self.lastRev()) - (num - 1))

            try:
                log = self.client.log(self.repo, revision_end=end, discover_changed_paths=files)
            except ClientError, message:
                msg = 'Error connecting to SVN repo: %s' % (message, )
                print msg
                return 'Error connecting to SVN repo'

            for entry in log:
                entry['date'] = asctime(localtime(entry['date']))      # convert EPOCH seconds to human readable
                entry['revision'] = str(entry['revision'].number)      # str -> converts int -> string
                entry['author'] = str(entry['author'])                 # str -> converts unicode -> ascii
                entry['message'] = str(entry['message'])               # str -> converts unicode -> ascii
                       
                if files:
                    files = []
                    for file in entry['changed_paths']:
                        filename = str(file['path'])
                        mode = str(file['action'])
                        files.append('%s (%s)' % (filename, mode))

                entry['files'] = files
                    
            return log
