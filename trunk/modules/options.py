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

import ConfigParser

class BotOptions:
    """
        Options Wrapper for Bot
    """

    def __init__(self, configFile):
        self.options = {}
        self.channels = []
        self.retries = 0;

        self.configFile = configFile
          
        self.config = ConfigParser.ConfigParser()
        self.loadOptions()
          
        self.config.read(self.configFile)
        self.server = self.config.get('irc', 'server')
        self.nick = self.config.get('irc', 'nick')
        self.name = self.config.get('irc', 'name')
        self.mode = self.config.getint('irc', 'mode')
        self.port = self.config.getint('irc', 'port')
        self.repo = self.config.get('svn', 'repo')

    def loadOptions(self):
        self.config.read(self.configFile)
        self.chanstojoin = self.config.get('irc', 'channels').split()
        self.authUsers = self.config.get('general', 'remote_users').split() # only respond to commands from
        self.rejoin = self.config.getboolean('irc', 'rejoin_on_kick')
        self.reconnect = self.config.getboolean('irc', 'reconnect_on_drop')
        self.welcome = self.config.getboolean('general', 'welcome_user')
        self.options['VERSION'] = self.config.get('about', 'version')
        self.options['REVISION'] = self.config.get('about', 'revision')
        self.options['CLIENTNAME'] = self.config.get('about', 'client-name')
        self.registeredNick = self.config.getboolean('general', 'registered_nick')
        self.nickPassword = self.config.get('general', 'nick_password')
        self.announce = self.config.get('svn', 'announce')
        self.announce_targets = self.config.get('svn', 'who').split()
        self.frequency = self.config.getint('svn', 'frequency')
        self.authors = ['xor', 'iddqd']
        self.retries = self.config.getint('irc', 'retries')
        self.openCommands = self.config.get('functions', 'open_commands').split()
        self.disabledCommands = self.config.get('functions', 'disabled_commands').split()
        self.announceLogins = self.config.getboolean('general', 'announce_logins')
        self.wrapWidth = self.config.getint('general', 'wrap_width')
        self.proxy = self.config.get('google', 'proxy')
        self.key = self.config.get('google', 'key')
        self.maxUndo = self.config.getint('general', 'max_undo')
        self.watchUsers = self.config.get('fun', 'watch_users').split()

