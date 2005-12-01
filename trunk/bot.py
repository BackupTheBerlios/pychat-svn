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

# twisted imports
from twisted.protocols import ident
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, error
from twisted.application.internet import TimerService

# python imports
from os import sys, getcwd, chdir, mkdir
from time import localtime, asctime, strftime, time
from exceptions import UnicodeEncodeError
import string
import textwrap

# modules
from modules.options import BotOptions
from modules.svn import SVNInterface
from modules.ident import IdentServer, IdentFactory
from modules.logging import MessageLogger
from modules.search import GoogleSearch
from modules.utils import *

_admin_commands = ['disable', 'enable', 'open', 'close']

class TehBot(irc.IRCClient):
    """A IRC bot."""

    def connectionMade(self):
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("[connected at %s]" % asctime(localtime(time())))
        self.options = self.factory.options
        self.svn = self.factory.svn
        self.nickname = self.options.nick
        self.realname = self.options.name
        self.authQ = []
        self.loggedIn = []
        self.topics = {}
        self.redos = {}
        self.undos = {}
        self.userWatch = {}
        self.undo = False
        self.lastSearchStart = -1
        self.lastSearchQuery = None
        self.init()
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s]" % asctime(localtime(time())))
        self.logger.close()

    def init(self):
        # set vars that may change during execution
        self.versionName = self.options.options['CLIENTNAME']
        self.versionNum = self.options.options['VERSION']
        self.versionEnv = sys.platform
        self.options.options['REVISION'] = self.svn.lastRev()
        self.readWatchDataFromFile()
        
        # SVN announce code
        if self.options.announce:    # if svn announce commits mode
            # create/start timer
            self.timer = TimerService(self.options.frequency, self.svnAnnounce)
            self.timer.startService()
        else:
            if hasattr(self, 'timer') and self.timer.running:  # if running
                self.timer.stopService() # stop it
    
    def svnAnnounce(self):
        rev = self.svn.lastRev()

        if rev == -1:
            print 'ERROR: Error connecting to SVN repo'
            return
        
        if rev != self.options.options['REVISION']: # check against stored revision
            # new commit, yay :)
            temp = int(self.options.options['REVISION'])
            temp += 1
            self.options.options['REVISION'] = str(temp)
            for target in self.options.announce_targets:    # tell everybody about it
                self.cmd_lastlog(target, target, [])

    def writeWatchDataToFile(self):
        """Outputs watch data to permanent storage (disk)"""
        if not self.checkDir('watchdata'):
            mkdir('watchdata')

        current = getcwd()
        chdir('watchdata')

        for user in self.userWatch:
            f = open('user' + '.watch', 'w')
            for message in self.userWatch[user]:
                f.write('%s<*!*>%s' % (message, self.userWatch[user][message]))
            f.close()   

        chdir(current)

    def readWatchDataFromFile(self):
        """Outputs watch data to permanent storage (disk)"""
        if not self.checkDir('watchdata'):
            mkdir('watchdata')

        current = getcwd()
        chdir('watchdata')

        for user in self.options.watchUsers:
            if not self.userWatch.has_key(user):
                self.userWatch[user] = {}
            try:
                f = open(user + '.watch', 'r')
                for line in f:
                    message, count = line.split('<*!*>')
                    self.userWatch[user][message.strip()] = int(count)
                f.close()
            except IOError:
                continue
            
        chdir(current)

    def checkDir(self, dir):
        """Checks that directory is valid"""

        # get current directory
        current = getcwd()
        
        try:
            # try cd into directory
            chdir(dir)
            
            # if that succeeds, switch back to previous directory...
            chdir(current)
        except OSError:
            # invalid directory, thus return False
            return False
        
        return True

    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        if self.options.registeredNick:
            self.msg('nickserv','identify ' + self.options.nickPassword)
        for chan in self.options.chanstojoin:
            self.join(chan)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.options.channels.append(channel.lower())
        for user in self.options.authUsers:
            if user.lower() not in self.loggedIn:
                print ' *** Attempting login for %s on %s' % (user, channel)
                self.cmd_login(user, channel, [])

    def userJoined(self, user, channel):
        """Called when a user joins a channel Im on"""
        user = user.split('!', 1)[0]
        if user != self.nickname:
            print 'JOIN: %s on %s' % (user, channel)
            self.logger.log('JOIN: %s on %s' % (user, channel))
            
            if self.options.welcome:
                if user.lower() in self.options.authUsers:
                    self.msg(channel, 'Welcome to %s, the all powerful %s, thank you for blessing us with your presence' % (channel, user))
                else:
                    self.msg(channel, 'Welcome to %s, %s' % (channel, user))

            if user in self.options.authUsers:
                print ' *** Attempting login for %s on %s' % (user, channel)
                self.cmd_login(user, channel, [])

    def kickedFrom(self, channel, kicker, message):
        """Called when Im kicked from a channel"""
        if self.options.rejoin:
            self.join(channel)
            self.msg(channel, '%s: thanks for that (%s)' % (kicker, message))

    def action(self, user, channel, data):
        """Called when another user performs an action"""
        user = user.split('!', 1)[0]
        msg = data.strip()
        self.logger.log('(%s): *%s %s ' % (channel, user, msg))
   
    def cmd_login(self, user, channel, params):
        """Gains usage access to bot. Usage: LOGIN"""
        #XXX:   this is non-RFC standard message (307), so may not 
        #       work on other servers, besides Shadowfire
        if user.lower() in self.options.authUsers:
            self.authQ.append(user)
            self.sendLine("WHOIS %s" % user)
        else:
            self.msg(user, 'ERROR: You Are Not Authorised!')
    
    def cmd_logout(self, user, channel, params):
        """Removes usage access to bot. Usage: LOGOUT"""
        if user.lower() in self.loggedIn:
            self.loggedIn.remove(user.lower())
        else:
            self.msg(user, 'ERROR: Not Logged In')
    
    def irc_307(self, prefix, params):
        """Reply from WHOIS message, indicates a registered nick"""

        if len(params) == 3:
            user = params[1].lower()
            msg = params[2]

            if user in self.authQ:
                self.authQ.remove(user)
                if user not in self.loggedIn:
                    if msg == 'is a registered nick':
                        self.loggedIn.append(user)
                
                        if self.options.announceLogins:
                            self.msg(user, 'You are now Logged In!')
   
    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        message = msg.strip()
        checkUser = user.lower()

        self.logger.log('%s (%s): %s' % (user, channel, msg))

        if channel in self.options.channels:
        # if from channel,then only process if proceeded by nick: or !nick:
        # if nick, then respond to user from which msg originated
        # if !nick, then respond to channel
            if message.startswith(self.nickname + ':'):
                message = message[len(self.nickname)+1:].strip()
            elif message.startswith('!' + self.nickname + ':'):
                message = message[len(self.nickname)+2:].strip()
                user = channel
            elif message.startswith('::'):
                message = message[2:].strip()
                user = channel
            else:
                return
        elif self.nickname != channel:
            return

        params = message.split()
        command = params.pop(0)

        # empty command like "::", just ignore
        if not command:
            return
        
        # is the message from an authorised user? or open command? 
        if checkUser in self.loggedIn or command.lower() in self.options.openCommands:
            print 'DEBUG: Remote Command %s from %s with parameters: %s' % (command, user, params)
            self.logger.log('Remote Command: %s from %s with parameters: %s' % (command, user, params))

            # special cases
            if command.lower() == 'login':
                self.cmd_login(checkUser, channel, params)
            elif command.lower() == 'logout':
                self.cmd_logout(checkUser, channel, params)
            elif command.lower() in _admin_commands and checkUser not in self.options.authors:
                self.msg(user, 'ERROR: Administrator only command: %s' % command)
            elif command.lower() in self.options.disabledCommands and checkUser not in self.options.authors:
                self.msg(user, 'ERROR: Disabled command: %s' % command)
            else:
                # despatch command
                try:
                    handler = getattr(self, 'cmd_' + command.lower())
                except AttributeError:
                    self.msg(user, 'Unrecognised command: %s' % command)
                else:
                    # call the handler here in case it throws an AttributeError
                    handler(user, channel, params)

    # User commands

    def cmd_quit(self, user, channel, params):
        """Quits IRC. Usage: QUIT <quit message>"""
        self.factory.quit = True
        self.quit(' '.join(params))

    def cmd_op(self, user, channel, params):
        """Gives Channel operator status to a user. Usage: OP [channel] <user | me>"""
        if len(params) > 1:
            # they've specified a channel
            channel = params.pop(0)

        target = params[0]
        if (target.lower() == 'me'):
            target = user

        self.mode(channel, 1, 'o', user=target)

    def cmd_deop(self, user, channel, params):
        """Removes Channel operator status from a user. Usage: DEOP [channel] <user | me>"""
        if len(params) > 1:
            # they've specified a channel
            channel = params.pop(0)

        target = params[0]
        if (target.lower() == 'me'):
            target = user

        self.mode(channel, 0, 'o', user=target)

    def cmd_topic(self, user, channel, params):
        """ Updates the current channel's topic. Usage: TOPIC [channel] [command] <topic>

             Commands:

               add  - add to current topic. Usage: TOPIC [channel] add <text>
               del  - remove from topic, based on position (starting at 0). Usage: TOPIC [channel] del <index>
               edit - replaces topic in specified position with new text. Usage: TOPIC [channel] edit <index> <text>
               set  - sets the topic. Usage: TOPIC [channel] set <text>
               get  - gets the current topic. Usage: TOPIC [channel] get
               undo - undo the last topic change. Usage: TOPIC [channel] undo
               redo - redo the last topic undo. Usage: TOPIC [channel] redo
               
               replace - replaces one word with another throughout the whole topic. Usage: TOPIC [channel] replace <to replace> <with>
        """

        if len(params) > 1:
            if params[0] in self.options.channels:
                channel = params.pop(0)
            
            command = params.pop(0).lower()
    
            if not self.topics.has_key(channel): 
                self.topics[channel] = []
                
            current = self.topics[channel]

            if command == 'add':
                temp = current + [' '.join(params)]
#               current.append(' '.join(params))
                topic = ' | '.join(temp)
            elif command == 'del':
                index = int(params.pop(0))
                topic = current[:index]
                index += 1

                if index > 0:
                    topic.extend(current[index:])

                topic = ' | '.join(topic)
            elif command == 'edit':
                index = int(params.pop(0))
                current[index] = ' '.join(params)
                topic = ' | '.join(current)
            elif command == 'replace':
                what = params.pop(0)
                with = params.pop(0)
                topic = ' | '.join(current) 
                topic = topic.replace(what, with)
            elif command == 'get':
                self.msg(user, 'topic for %s is: %s' % (channel, ' | '.join(current)))
                return
            elif command == 'set':
                topic = ' '.join(params)    
            else:
                topic = command + ' ' + ' '.join(params)
        elif len(params) == 1:
            topic = params.pop(0)

            if topic == 'get':
                if self.topics.has_key(channel):
                    self.msg(user, 'topic for %s is: %s' % (channel, ' | '.join(self.topics[channel])))
                else:
                    self.msg(user, 'topic for %s is: %s' % (channel, ''))
                return
            elif topic == 'undo':
                if not self.undos.has_key(channel):
                    self.msg(user, 'ERROR: No undos available')
                    return
            
                if len(self.undos[channel]) == 0:
                    self.msg(user, 'ERROR: No more undos left')
                    return
                           
                try:
                    redo = self.redos[channel]
                except KeyError:
                    redo = []
                    
                temp = self.undos[channel].pop()
                topic = ' | '.join(temp)
                redo.append(self.topics[channel])
                self.redos[channel] = redo
                self.undo = True
                del self.redos[channel][:len(redo) - self.options.maxUndo]
            elif topic == 'redo':
                if not self.redos.has_key(channel):
                    self.msg(user, 'ERROR: No redos available')
                    return
    
                if len(self.redos[channel]) == 0:
                    self.msg(user, 'ERROR: No more redos left')
                    return

                try:
                    undo = self.undos[channel]
                except KeyError:
                    undo = []
                    
                temp = self.redos[channel].pop()
                topic = ' | '.join(temp)
        else:
            return
       
        self.topic(channel, topic)

    def cmd_kick(self, user, channel, params):
        """Kicks user from current channel. Usage: KICK [channel] <user> [message]"""
        if len(params) > 1:
            if params[0] in self.options.channels:
                channel = params.pop(0)
            target = params.pop(0)
            kickmsg = ' '.join(params)
        else:
            target = params[0]
            kickmsg = self.nickname
        print 'KICK: %s %s %s' % (channel, target, kickmsg)
        self.kick(channel, target, kickmsg)

    def cmd_say(self, user, channel, params):
        """Sends a private message. Usage: SAY [channel/user] <message>"""
        if len(params) > 1:
            if params[0] in self.options.channels:
                # correct target has been specified
                target = params.pop(0)
            else:
                target = channel
        else:
            target = channel
        self.msg(target, ' '.join(params))

    def cmd_suggest(self, user, channel, params):
        """Use google spell suggestion service to suggest a spelling. Usage: SUGGEST <word>"""
        if len(params) == 1:
            s = GoogleSearch(self.options.proxy, self.options.key)
            result = s.spell(params[0])
            self.msg(user, 'Suggestion(s): %s' % (result, ))
        else:
            self.msg(user, 'ERROR: No Parameters Given')

    def cmd_google(self, user, channel, params):
        """Do a google search for parameters. Usage: GOOGLE <query>"""
        #
        #XXX: Other features to follow, like specifying max, etc
        #
        
        if len(params) == 0:
            self.msg(user, 'ERROR: No Parameters')
            return
                         
        query = ' '.join(params)
        self.lastSearchStart = 0
        self.lastSearchQuery = query

        self.doGoogleSearch(user, query, 0, 5)

    def cmd_more(self, user, channel, params):
        """Return next 5 results (if available) for last Google search. Usage: MORE"""

        if self.lastSearchQuery and self.lastSearchStart > -1:
            self.doGoogleSearch(user, self.lastSearchQuery, self.lastSearchStart, 5)
        else:
            self.msg(user, 'ERROR: No Active Searches')
            
    def doGoogleSearch(self, user, query, start, max):
        """Perform Google search"""

        self.lastSearchStart += max

        s = GoogleSearch(self.options.proxy, self.options.key)
        result = s.search(query.decode('utf-8'), start, max)

        if result:      
            results = result.getResultElements()
            count = 0
            msg = 'Results: '

            for entry in results:
                title = htmlToText(entry.title.encode('utf-8'))
                url = entry.URL
                new = ' %s %s: <%s> |' % (msg, bold(title), url)
              
                if len(new) > 430:
                    msg = msg[:-1]
                    self.lastSearchStart -= count 
                    break
                else:
                    msg = new
                    count+= 1

            if msg[-1] == '|':
                msg = msg[:-1]

            msg += ' (search took %s seconds)' % (str(result.getSearchTime())[:6],)

            self.msg(user, msg.strip())
        else:
            self.msg(user, 'No Results')
      
    def toAscii(self, text):
        """Removes all non-ascii characters"""
        temp = ''
        
        for char in text:
            if char in string.printable:
                temp += char

        return temp
    
    def cmd_notice(self, user, channel, params):
        """Sends a NOTICE. Usage: NOTICE [channel/user] <message>"""
        if len(params) > 1:
            if params[0] in self.options.channels:
                # correct target has been specified
                target = params.pop(0)
            else:
                target = channel
        else:
            target = channel
        self.notice(target, ' '.join(params))
        
    def cmd_join(self, user, channel, params):
        """Joins specified channel(s). Usage: JOIN <channel> [channel] ..."""
        for param in params:
            if param.lower() in self.options.channels:
                self.msg(user, 'ERROR: Already on channel: ' + param)
                continue
            self.join(param)

    def cmd_leave(self, user, channel, params):
        """Leaves specified channel(s). Usage: LEAVE [channel] ..."""
        to_leave = []

        if 'all' in params:
            to_leave.extend(self.options.channels)
        else:
            if len(params) == 0:
                # if no channels are specified, leave current channel
                to_leave.append(channel)
            else:
                to_leave.extend(params)

        for chan in to_leave:
            if chan.lower() not in self.options.channels:
                self.msg(user, 'Error: Not on channel: ' + chan)
            self.leave(chan, 'Leaving')

    def cmd_authorise(self, user, channel, params):
        """Adds user to authorised users list. Usage: AUTHORISE nick [nick] ..."""
        for target in params:
            if target.lower() in self.options.authUsers:
                self.msg(user, 'ERROR: Already authorised: %s' % (target))
            else:
                self.options.authUsers.append(target.lower())
                self.cmd_login(target.lower(), channel, [])

    def cmd_unauthorise(self, user, channel, params):
        """Removes user from authorised users list. Usage: UNAUTHORISE nick [nick] ..."""
        for target in params:
            if target.lower() not in self.options.authUsers:
                self.msg(user, 'ERROR: Not authorised: %s' % (target))
            elif target.lower() in self.options.authors:
                self.msg(user, 'ERROR: Cannot remove owner: %s ' % (target))
            else:
                self.options.authUsers.remove(target.lower())
                if target.lower() in self.loggedIn:
                    self.loggedIn.remove(target.lower())

    def cmd_rename(self, user, channel, params):
        """Changes the bots name. Usage: RENAME <new name>."""
        self.setNick(params[0])

    def cmd_commands(self, user, channel, params):
        """Alias for HELP."""
        self.cmd_help(user, channel, params)

    def cmd_disable(self, user, channel, params):
        """Disable specific command. Administrator use only. Usage: DISABLE <command> [command] ..."""
        for command in params:
            if command in self.options.disabledCommands:
                self.msg(user, 'ERROR: Command %s is Already Disabled' % (command,))
                continue
            else:
                self.options.disabledCommands.append(command)
    
    def cmd_enable(self, user, channel, params):
        """Enable a disabled command. Administrator use only. Usage: ENABLE <command> [command] ..."""
        for command in params:
            if command not in self.options.disabledCommands:
                self.msg(user, 'ERROR: Command %s is Not Disabled' % (command,))
                continue
            else:
                self.options.disabledCommands.remove(command)

    def cmd_open(self, user, channel, params):
        """Allow public access to a specific command. Administrator use only. Usage: OPEN <command> [command] ..."""
        for command in params:
            if command in self.options.openCommands:
                self.msg(user, 'ERROR: Command %s is Already Public' % (command,))
                continue
            else:
                self.options.openCommands.append(command)
    
    def cmd_close(self, user, channel, params):
        """Disable a public command. Administrator use only. Usage: CLOSE <command> [command] ..."""
        for command in params:
            if command not in self.options.openCommands:
                self.msg(user, 'ERROR: Command %s is Not Public' % (command,))
                continue
            else:
                self.options.openCommands.remove(command)

    def cmd_admin(self, user, channel, params):
        """Restrict access to a specific command for administrators only. Administrator use only. Usage: ADMIN <command> [command] ..."""
        for command in params:
            if command in _admin_commands:
                self.msg(user, 'ERROR: Command %s is Already Restricted' % (command,))
                continue
            else:
                _admin_commands.append(command)
    
    def cmd_unadmin(self, user, channel, params):
        """Disable a admin command. Administrator use only. Usage: UNADMIN <command> [command] ..."""
        for command in params:
            if command not in _admin_commands:
                self.msg(user, 'ERROR: Command %s is Unrestricted' % (command,))
                continue
            else:
                _admin_commands.remove(command)

    def cmd_disabled(self, user, channel, params):
        """Returns list of disabled commands. Usage: DISABLED"""
        if len(self.options.disabledCommands) == 0:
            self.msg(user, 'ERROR: No Disabled Commands')
        else:
            self.msg(user, 'Disabled Commands: ' + ' '.join(self.options.disabledCommands))

    def cmd_restricted(self, user, channel, params):
        """Returns list of restricted commands. Usage: RESTRICTED"""
        if len(_admin_commands) == 0:
            self.msg(user, 'ERROR: No Restricted Commands')
        else:
            self.msg(user, 'Restricted Commands: ' + ' '.join(_admin_commands))

    def cmd_telldik(self, user, channel, params):
        """For fun. Will be removed soon. Tells DickShinnery how often he has timed out. Usage: TELLDIK [nick]"""
        if len(params) == 1:
            target = params.pop(0).lower()
        else:
            target = 'dickshinnery'
        
        if target in self.options.watchUsers:
            if target in self.userWatch:
                if 'ping timeout' in self.userWatch[target]:
                    self.msg(user, '%s has timed out %s times while Ive been here.' % (target, self.userWatch[target]['ping timeout']))
                else:
                    self.msg(user, '%s has not timed out while Ive been here!' % (target, ))
            else:
                self.msg(user, '%s has not timed out while Ive been here!' % (target, ))
        else:
            self.msg(user, '%s is not being watched' % (target,))

    def cmd_public(self, user, channel, params):
        """Returns list of public/open commands. Usage: PUBLIC"""
        if len(self.options.openCommands) == 0:
            self.msg(user, 'ERROR: No Public Commands')
        else:
            self.msg(user, 'Public Commands: ' + ' '.join(self.options.openCommands))

    def cmd_userlog(self, user, channel, params):
        """Displays the watch log for specified user. Usage: USERLOG <user>"""
        if len(params) > 0:
            target = params.pop(0).lower()
            if target in self.options.watchUsers:
                if target not in self.userWatch or len(self.userWatch[target]) == 0:
                    self.msg(user, 'Empty watch log for %s!' % (target,))
                else:
                    self.msg(user, 'Watch log for %s: ' % (target,))
                    for message in self.userWatch[target]:
                        self.msg(user, '\t%s: %s' % (message, self.userWatch[target][message]))
                    self.msg(user, '<end log>')
            else:
                self.msg(user, 'ERROR: Not watching %s!' % (target,))
        else:
            self.msg(user, 'ERROR: No user specified')

    def cmd_help(self, user, channel, params):
        """This screen. Displays available commands and descriptions (if available)"""
        to_say = ['<commands>']

        if len(params) > 0: # Specific help
            for command in params:
                try:
                    handler = getattr(self, 'cmd_' + command.lower())
                    doc = handler.__doc__.splitlines()
                    first = 'Help: %s: ' % (bold(command.upper()),)
                    self.msg(user, first + doc.pop(0)) 
                
                    for msg in doc:
                        self.msg(user, msg.strip()) 
                except AttributeError:
                    self.msg(user, 'No help found: %s' % bold(command))
        else: #general help
            for attr in dir(self):
                if attr.startswith('cmd_'):
                    doc = getattr(self, attr).__doc__.splitlines()
                    to_say.append('  %s: %s' % (attr[4:].upper(), doc[0]))
            to_say.append('</commands>')
            for msg in to_say:
                self.msg(user, msg)
    
    
    def cmd_lastlog(self, user, channel, params):
        """Displays the last n commit messages to our SVN repo. Usage: LASTLOG [num]"""
    
        arg = len(params) == 1 and int(params[0]) or 1
        log = self.svn.lastLog(arg, True)
   
        if log == 'Error connecting to SVN repo':
            print 'ERROR: Error connecting to SVN repo'
            return
                   
        for entry in log:
            common = entry['date'] + ' r' + entry['revision']
            messages = entry['message'].splitlines()
            filelist = ', '.join(entry['files'])
            files = ' - (' + filelist + ') [%s]' % (entry['author'], )
            count = 1
            
            for message in messages:
                if count > 1:
                   message = ('- %s' % (message,)).rjust(len(common) + len(message) + 3)
                else:    
                   message = '%s - %s' % (common, message)
    
                msgs = textwrap.wrap(message, self.options.wrapWidth)
                
                wrapN = 1
                
                for msg in msgs:
                    if wrapN > 1:
                        self.msg(user, msg.rjust(len(msg) + len(common) + 3))
                    else:
                        self.msg(user, msg)
                    wrapN += 1
    
                count += 1
            
            self.msg(user, files.rjust(len(common) + len(files)))

    def cmd_action(self, user, channel, params):
        """Performs action in specified channel. Usage: ACTION [channel] action"""
        if len(params) > 1 and params[0] in self.options.channels:
            # correct target has been specified
            target = params.pop(0)
        else:
            target = channel
        self.me(target, ' '.join(params))

    def cmd_stats(self, user, channel, params):
        """Displays some stats/info about the bot. Usage: STATS"""
        stats = [
            '<begin stats>',
            'pychat Project: Python IRC Client',
            'http://www.pychat.za.org',
            'NICK: ' + self.nickname,
            'NAME: ' + self.realname,
            'VERSION: ' + self.options.options['VERSION'],
            'REVISION: ' + self.options.options['REVISION'],
            'CHANNELS: ' + ','.join(self.options.channels),
            '<end stats>',
        ]

        for stat in stats:
            self.msg(user, stat)

    def cmd_reload(self, user, channel, params):
        """Reload the configuration file. Usage: RELOAD"""
        self.options.loadOptions()
        self.writeWatchDataToFile()
        self.readWatchDataFromFile()
        self.msg(user, 'Config File Reloaded')
        self.init()

    def cmd_authusers(self, user, channel, params):
        """Displays the list of users that the bot will respond to. Usage: AUTHUSERS"""
        if len(self.loggedIn) == 0:
            self.msg(user, 'ERROR: No Authorised Users Logged In')
        else:
            self.msg(user, 'I Respond to: ' + ' '.join(self.loggedIn))

    def cmd_hop(self, user, channel, params):
        """Leaves and Rejoins channel. Usage: HOP [channel]"""
        if len(params) > 0:
            channel = params[0]
        self.leave(channel, 'Hopping...')
        self.join(channel)

    def cmd_drop(self, user, channel, params):
        """Closes connection. Usage: DROP"""
        reactor.stop()

    def cmd_bark(self, user, channel, params):
        """BARKS LIKE A DOG!! Usage: BARK"""
        self.msg(channel, 'WOOF! WOOF!')

    def cmd_bendover(self, user, channel, params):
        """Behaves appropriately. Usage: BENDOVER"""
        self.me(channel, 'drops the soap')

    def cmd_insult(self, user, channel, params):
        """Retorts. Usage: INSULT"""
        self.msg(channel, 'RETORT!')

    # irc callbacks

    def userQuit(self, user, quitMessage):
        """Called when a user quits IRC"""
        if user.lower() in self.loggedIn:
            self.loggedIn.remove(user.lower())
        print 'QUIT: %s (%s)' % (user, quitMessage)

        if user.lower() in self.options.watchUsers:
            if self.userWatch.has_key(user.lower()):
                if self.userWatch[user.lower()].has_key(quitMessage.lower()):
                    self.userWatch[user.lower()][quitMessage.lower()] += 1
                else:
                    self.userWatch[user.lower()][quitMessage.lower()] = 1
            else:
                self.userWatch[user.lower()] = {}
                self.userWatch[user.lower()][quitMessage.lower()] = 1
        
        self.writeWatchDataToFile()
        self.logger.log('QUIT: %s (%s)' % (user, quitMessage))
            
    def topicUpdated(self, user, channel, newTopic):
        """Called when topic is updated and on first join to a channel"""
        if self.undo:
            self.undo = False
            self.topics[channel] = [entry.strip() for entry in newTopic.split('|') if len(entry.strip()) > 0]                
            return
        
        if self.undos.has_key(channel):
            if self.topics.has_key(channel):
                if len(self.undos[channel]) > 0:
                    if self.topics[channel] != self.undos[channel][-1]:
                        self.undos[channel].append(self.topics[channel])
                else:
                    self.undos[channel].append(self.topics[channel])
            else:
                self.undos[channel] = []
        else:
            self.undos[channel] = []
            if self.topics.has_key(channel):
                self.undos[channel].append(self.topics[channel])    
        
        self.topics[channel] = [entry.strip() for entry in newTopic.split('|') if len(entry.strip()) > 0]
        del self.undos[channel][:len(self.undos) - self.options.maxUndo]

    def left(self, channel):
      self.options.channels.remove(channel.lower())
      print 'PART: ', channel
      self.logger.log('PART: %s' % (channel,))

class TehBotFactory(protocol.ClientFactory):
    """A factory for TehBots.

       A new protocol instance will be created each time we connect to the server.
    """

    # the class of the protocol to build when new connection is made
    protocol = TehBot

    def __init__(self, options, svn, logfile):
        self.options = options
        self.svn = svn
        self.quit = False
        self.filename = logfile

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, ..."""
        if self.options.reconnect:
            if self.quit:
                reactor.stop()
            else:
                if self.options.retries:
                    self.options.retries -= 1
                    connector.connect()
                else:
                    reactor.stop()
        else:
            reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()

if __name__ == '__main__':
    
    # Create options object
    opt = BotOptions('bot.cfg')

    # Create SVN Interface object
    svn = SVNInterface(opt.repo)

    # generate logfile name
    logfile = strftime('logs/%d%m%Y-%H%M%S.log', localtime())

    # create factory protocol and application
    f = TehBotFactory(opt, svn, logfile)

    # connect factory to this host and port
    reactor.connectTCP(opt.server, opt.port, f)

    # listen for ident requests
    try:
        reactor.listenTCP(113, IdentFactory(opt.name))
    except error.CannotListenError:
        pass

    # run bot
    reactor.run()
