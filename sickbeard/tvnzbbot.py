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



#! /usr/bin/env python
#
# Example program using ircbot.py.
#
# Joel Rosdahl <joel@rosdahl.net>

"""A simple example bot.

This is an example bot that uses the SingleServerIRCBot class from
ircbot.py.  The bot enters a channel and listens for commands in
private messages and channel traffic.  Commands in channel messages
are given by prefixing the text by the bot name followed by a colon.
It also responds to DCC CHAT invitations and echos data sent in such
sessions.

The known commands are:

    stats -- Prints some channel information.

    disconnect -- Disconnect the bot.  The bot will try to reconnect
                  after 60 seconds.

    die -- Let the bot cease to exist.

    dcc -- Let the bot invite you to a DCC CHAT connection.
"""

import re
import threading
import time
import urllib
import traceback

from lib.tvdb_api import tvdb_api, tvdb_exceptions, tvnamer

from classes import NZBSearchResult
from common import *
from logging import *

import sickbeard, search

from lib.irclib.ircbot import SingleServerIRCBot
from lib.irclib.irclib import nm_to_n, nm_to_h, irc_lower, ip_numstr_to_quad, ip_quad_to_numstr


class NZBBotRunner():
    
    def __init__(self):
        self.bot = NZBBot(sickbeard.IRC_CHANNEL + " " + sickbeard.IRC_KEY, sickbeard.IRC_NICK, sickbeard.IRC_SERVER)
        self.thread = None
        self.abort = False
        self.thread = None
        self.initThread()

    def initThread(self):
        if self.thread == None:
            self.thread = threading.Thread(None, self.runBot, "IRC")

    def runBot(self):

        logger.log("Starting IRC bot up in its own thread")

        try:

            # start things off by connecting to the server
            self.bot._connect()
    
            # then run forever until we get self.abort
            while True:
                
                self.bot.ircobj.process_once()
                
                if self.abort:
                    self.bot.disconnect("")
                    self.thread = None
                    self.abort = False
                    return
                
                time.sleep(0.2)

        except Exception as e:
            logger.log("IRC bot threw an exception: " + str(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)

class NZBBot(SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.server = server

    def on_nicknameinuse(self, c, e):
        newNick = c.get_nickname() + "_"
        logger.log("Name was taken, trying " + newNick)
        c.nick(newNick)

    def on_welcome(self, c, e):
        toJoin = self.channel.partition(" ")
        if toJoin[2] == "":
            logger.log("Joining channel " + self.channel)
            c.join(self.channel)
        else:
            logger.log("Joining channel " + toJoin[0] + " with key " + toJoin[2])
            c.join(toJoin[0], toJoin[2])

    def on_privmsg(self, c, e):
        logger.log("Received private msg: " + e.arguments()[0])
        #self.do_command(e, e.arguments()[0])

    def on_pubmsg(self, c, e):
        msg = stripSpecialChars(e.arguments()[0])
        
        match = re.match(re.compile("\[(\w+)\] (.*?) ::.*::.*::\s*(.*)"), msg)
        if match != None:
            source, name, url = match.group(1, 2, 3)
            logger.log("Got news that " + name + " is available at " + url + " on " + source)
            # check it out in a new thread so we don't mess up the bot by blocking
            threading.Thread(None, self.checkNZB, "CheckNZB", [source, name, url]).start()

    def on_dccmsg(self, c, e):
        c.privmsg("You said: " + e.arguments()[0])

    def on_dccchat(self, c, e):
        if len(e.arguments()) != 2:
            return
        args = e.arguments()[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    def start(self):
        logger.log("Creating IRC bot, connecting to " + self.server + " and joining " + self.channel)
        SingleServerIRCBot.start(self)

    def jump_server(self, newServer):
        self.server_list = [(newServer, 6667)]
        self.server = newServer
        SingleServerIRCBot.jump_server(self)

    def jump_channel(self, newChan, key=None):
        self.connection.part(self.channel.split(" ")[0])
        if key == None:
            self.channel = newChan
            self.connection.join(newChan)
        else:
            self.channel = newChan + " " + key
            self.connection.join(newChan, key)

    def nick(self, newNick):
        self._nickname = newNick
        self.connection.nick(newNick)

    def checkNZB(self, source, name, url):
        
        if source not in ("TVBINZ"):
            logger.log("Source " + source + " isn't supported, ignoring it")
            return
        
        logger.log("Parsing the name...", logger.DEBUG)
        result = tvnamer.processSingleName(name)
        logger.log("Result from parse: " + str(result), logger.DEBUG)

        if result != None:
            logger.log("Creating TVDB object", logger.DEBUG)
            t = tvdb_api.Tvdb(**sickbeard.TVDB_API_PARMS)
            logger.log("Object created: " + str(t), logger.DEBUG)
            
            try:
                logger.log("Getting show data from TVDB", logger.DEBUG)
                showObj = t[result["file_seriesname"]]
                logger.log("Show retrieval complete! " + str(showObj), logger.DEBUG)
            except tvdb_exceptions.tvdb_shownotfound:
                logger.log(name + " wasn't found on TVDB, skipping")
                return
                

            logger.log(name + " got detected as show " + showObj["seriesname"] + " (" + str(showObj["id"]) + ")")
            
            show = filter(lambda x: int(x.tvdbid) == int(showObj["id"]), sickbeard.showList)
            
            if show == []:
                logger.log("Show " + showObj["seriesname"] + " wasn't found in the show list")
                return
            
            if ".720p." in name:
                quality = HD
            else:
                quality = SD
            
            logger.log("Quality got detected as "+str(qualityStrings[quality]))
            
            season = int(result["seasno"])
            episode = int(result["epno"][0])
            
            ep = show[0].getEpisode(season, episode)
            
            if ep.status not in (SNATCHED, DOWNLOADED, SKIPPED) and quality == ep.quality:
                
                nzbObj = NZBSearchResult(ep)
                nzbObj.url = url + '&' + urllib.urlencode({'i': sickbeard.TVBINZ_UID, 'h': sickbeard.TVBINZ_HASH})
                nzbObj.extraInfo = [name]
                if source == "TVBINZ":
                    nzbObj.provider = TVBINZ
                else:
                    # don't support any other sources ATM
                    return
    
                search.snatchEpisode(nzbObj)


def stripSpecialChars(str):
    str = re.compile("\x03[0-9]{1,2}(,[0-9]{1,2})?").sub("", str)
    str = re.compile("[\x02\x1f\x16\x0f\x03]").sub("", str)
    return str
