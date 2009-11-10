# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.



import cherrypy
import os.path

from sickbeard import helpers
from sickbeard.logging import * 

from lib.irclib.irclib import ServerNotConnectedError

import sickbeard

def change_LOG_DIR(log_dir):

    if os.path.normpath(sickbeard.LOG_DIR) != os.path.normpath(log_dir):
        if helpers.makeDir(log_dir):
            Logger().shutdown()
            sickbeard.LOG_DIR = os.path.normpath(log_dir)
            Logger().log("Initialized new log file in " + log_dir)

            cherry_log = os.path.join(sickbeard.LOG_DIR, "cherrypy.log")
            cherrypy.config.update({'log.access_file': cherry_log})
            
            Logger().log("Changed cherry log file to " + cherry_log)
            
        else:
            return False

    return True

def change_NZB_DIR(nzb_dir):

    if os.path.normpath(sickbeard.NZB_DIR) != os.path.normpath(nzb_dir):
        if helpers.makeDir(nzb_dir):
            sickbeard.NZB_DIR = os.path.normpath(nzb_dir)
            Logger().log("Changed NZB folder to " + nzb_dir)
        else:
            return False

    return True


def change_IRC_BOT(irc_bot):

    if sickbeard.IRC_BOT == True and irc_bot == False:
        sickbeard.botRunner.abort = True
    elif sickbeard.IRC_BOT == False and irc_bot == True:
        sickbeard.botRunner.initThread()
        sickbeard.botRunner.thread.start()
    sickbeard.IRC_BOT = irc_bot 

def change_IRC_SERVER(irc_server):
    
    if sickbeard.IRC_SERVER != irc_server:
        sickbeard.botRunner.bot.jump_server(irc_server)
    sickbeard.IRC_SERVER = irc_server

def change_IRC_CHANNEL(irc_channel, irc_key):

    if sickbeard.IRC_CHANNEL != irc_channel or sickbeard.IRC_KEY != irc_key:
        try:
            sickbeard.botRunner.bot.jump_channel(irc_channel, irc_key)
        except ServerNotConnectedError:
            pass
            
    sickbeard.IRC_CHANNEL = irc_channel
    sickbeard.IRC_KEY = irc_key


def change_IRC_NICK(irc_nick):
            
    if sickbeard.IRC_NICK != irc_nick:
        try:
            sickbeard.botRunner.bot.nick(irc_nick)
        except ServerNotConnectedError:
            pass

    sickbeard.IRC_NICK = irc_nick
