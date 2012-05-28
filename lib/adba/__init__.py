#!/usr/bin/env python
#
# This file is part of aDBa.
#
# aDBa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aDBa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with aDBa.  If not, see <http://www.gnu.org/licenses/>.
import threading
from time import time, sleep, strftime, localtime
from types import *

from aniDBlink import AniDBLink
from aniDBcommands import *
from aniDBerrors import *
from aniDBAbstracter import Anime, Episode

version = 100

class Connection(threading.Thread):
    def __init__(self, clientname='adba', server='api.anidb.info', port=9000, myport=9876, user=None, password=None, session=None, log=False, logPrivate=False, keepAlive=False):
        super(Connection, self).__init__()
        # setting the log function
        self.logPrivate = logPrivate
        if type(log) in (FunctionType, MethodType):# if we get a function or a method use that.
            self.log = log
            self.logPrivate = True # true means sensitive data will not be NOT be logged ... yeah i know oO
        elif log:# if it something else (like True) use the own print_log
            self.log = self.print_log
        else:# dont log at all
            self.log = self.print_log_dummy


        self.link = AniDBLink(server, port, myport, self.log, logPrivate=self.logPrivate)
        self.link.session = session

        self.clientname = clientname
        self.clientver = version

        # from original lib 
        self.mode = 1    #mode: 0=queue,1=unlock,2=callback

        # to lock other threads out
        self.lock = threading.RLock()

        # thread keep alive stuff
        self.keepAlive = keepAlive
        self.setDaemon(True)
        self.lastKeepAliveCheck = 0
        self.lastAuth = 0
        self._username = password
        self._password = user

        self._iamALIVE = False

        self.counter = 0
        self.counterAge = 0

    def print_log(self, data):
        print(strftime("%Y-%m-%d %H:%M:%S", localtime(time())) + ": " + str(data))

    def print_log_dummy(self, data):
        pass

    def stop(self):
        self.logout(cutConnection=True)


    def cut(self):
        self.link.stop()

    def handle_response(self, response):
        if response.rescode in ('501', '506') and response.req.command != 'AUTH':
            self.log("seams like the last command got a not authed error back tring to reconnect now")
            if self._reAuthenticate():
                response.req.resp = None
                response = self.handle(response.req, response.req.callback)


    def handle(self, command, callback):

        self.lock.acquire()
        if self.counterAge < (time() - 120): # the last request was older then 2 min reset delay and counter
            self.counter = 0
            self.link.delay = 2
        else: # something happend in the last 120 seconds
            if self.counter < 5:
                self.link.delay = 2 # short term "A Client MUST NOT send more than 0.5 packets per second (that's one packet every two seconds, not two packets a second!)"
            elif self.counter >= 5:
                self.link.delay = 6 # long term "A Client MUST NOT send more than one packet every four seconds over an extended amount of time."

        if command.command not in ('AUTH', 'PING', 'ENCRYPT'):
            self.counterAge = time()
            self.counter += 1
            if self.keepAlive:
                self.authed()

        def callback_wrapper(resp):
            self.handle_response(resp)
            if callback:
                callback(resp)

        self.log("handling(" + str(self.counter) + "-" + str(self.link.delay) + ") command " + str(command.command))

        #make live request
        command.authorize(self.mode, self.link.new_tag(), self.link.session, callback_wrapper)
        self.link.request(command)

        #handle mode 1 (wait for response)
        if self.mode == 1:
            command.wait_response()
            try:
                command.resp
            except:
                self.lock.release()
                if self.link.banned:
                    raise AniDBBannedError("User is banned")
                else:
                    raise AniDBCommandTimeoutError("Command has timed out")

            self.handle_response(command.resp)
            self.lock.release()
            return command.resp
        else:
            self.lock.release()

    def authed(self, reAuthenticate=False):
        self.lock.acquire()
        authed = (self.link.session != None)
        if not authed and (reAuthenticate or self.keepAlive):
            self._reAuthenticate()
            authed = (self.link.session != None)
        self.lock.release()
        return authed

    def _reAuthenticate(self):
        if self._username and self._password:
            self.log("auto re authenticating !")
            resp = self.auth(self._username, self._password)
            if resp.rescode not in ('500'):
                return True
        else:
            return False

    def _keep_alive(self):
        self.lastKeepAliveCheck = time()
        self.log("auto check !")
        # check every 30 minutes if the session is still valid
        # if not reauthenticate 
        if self.lastAuth and time() - self.lastAuth > 1800:
            self.log("auto uptime !")
            self.uptime() # this will update the self.link.session and will refresh the session if it is still alive

            if self.authed(): # if we are authed we set the time
                self.lastAuth = time()
            else: # if we aren't authed and we have the user and pw then reauthenticate
                self._reAuthenticate()

        # issue a ping every 20 minutes after the last package
        # this ensures the connection will be kept alive
        if self.link.lastpacket and time() - self.link.lastpacket > 1200:
            self.log("auto ping !")
            self.ping()


    def run(self):
        while self.keepAlive:
            self._keep_alive()
            sleep(120)


    def auth(self, username, password, nat=None, mtu=None, callback=None):
        """
        Login to AniDB UDP API
        
        parameters:
        username - your anidb username
        password - your anidb password
        nat     - if this is 1, response will have "address" in attributes with your "ip:port" (default:0)
        mtu     - maximum transmission unit (max packet size) (default: 1400)
        
        """
        self.log("ok1")
        if self.keepAlive:
            self.log("ok2")
            self._username = username
            self._password = password
            if self.is_alive() == False:
                self.log("You wanted to keep this thing alive!")
                if self._iamALIVE == False:
                    self.log("Starting thread now...")
                    self.start()
                    self._iamALIVE = True
                else:
                    self.log("not starting thread seams like it is already running. this must be a _reAuthenticate")


        self.lastAuth = time()
        return self.handle(AuthCommand(username, password, 3, self.clientname, self.clientver, nat, 1, 'utf8', mtu), callback)

    def logout(self, cutConnection=False, callback=None):
        """
        Log out from AniDB UDP API
        
        """
        result = self.handle(LogoutCommand(), callback)
        if(cutConnection):
            self.cut()
        return result

    def push(self, notify, msg, buddy=None, callback=None):
        """
        Subscribe/unsubscribe to/from notifications

        parameters:
        notify    - Notifications about files added?
        msg    - Notifications about message added?
        buddy    - Notifications about buddy events?

        structure of parameters:
        notify msg [buddy]
        
        """
        return self.handle(PushCommand(notify, msg, buddy), callback)

    def pushack(self, nid, callback=None):
        """
        Acknowledge notification (do this when you get 271-274)

        parameters:
        nid    - Notification packet id

        structure of parameters:
        nid
        
        """
        return self.handle(PushAckCommand(nid), callback)

    def notifyadd(self, aid=None, gid=None, type=None, priority=None, callback=None):
        """
        Add a notification
        
        parameters:
        aid    - Anime id
        gid - Group id
        type - Type of notification: type=>  0=all, 1=new, 2=group, 3=complete
        priority - low = 0, medium = 1, high = 2 (unconfirmed)
        
        structure of parameters:
        [aid={int}|gid={int}]&type={int}&priority={int}
        
        """

        return self.handle(NotifyAddCommand(aid, gid, type, priority), callback)


    def notify(self, buddy=None, callback=None):
        """
        Get number of pending notifications and messages

        parameters:
        buddy    - Also display number of online buddies

        structure of parameters:
        [buddy]
        
        """
        return self.handle(NotifyCommand(buddy), callback)

    def notifylist(self, callback=None):
        """
        List all pending notifications/messages
        
        """
        return self.handle(NotifyListCommand(), callback)

    def notifyget(self, type, id, callback=None):
        """
        Get notification/message

        parameters:
        type    - (M=message, N=notification)
        id    - message/notification id

        structure of parameters:
        type id
        
        """
        return self.handle(NotifyGetCommand(type, id), callback)

    def notifyack(self, type, id, callback=None):
        """
        Mark message read or clear a notification

        parameters:
        type    - (M=message, N=notification)
        id    - message/notification id

        structure of parameters:
        type id
        
        """
        return self.handle(NotifyAckCommand(type, id), callback)

    def buddyadd(self, uid=None, uname=None, callback=None):
        """
        Add a user to your buddy list

        parameters:
        uid    - user id
        uname    - name of the user

        structure of parameters:
        (uid|uname)
        
        """
        return self.handle(BuddyAddCommand(uid, uname), callback)

    def buddydel(self, uid, callback=None):
        """
        Remove a user from your buddy list

        parameters:
        uid    - user id

        structure of parameters:
        uid
        
        """
        return self.handle(BuddyDelCommand(uid), callback)

    def buddyaccept(self, uid, callback=None):
        """
        Accept user as buddy

        parameters:
        uid    - user id

        structure of parameters:
        uid
        
        """
        return self.handle(BuddyAcceptCommand(uid), callback)

    def buddydeny(self, uid, callback=None):
        """
        Deny user as buddy

        parameters:
        uid    - user id

        structure of parameters:
        uid
        
        """
        return self.handle(BuddyDenyCommand(uid), callback)

    def buddylist(self, startat, callback=None):
        """
        Retrieve your buddy list

        parameters:
        startat    - number of buddy to start listing from

        structure of parameters:
        startat
        
        """
        return self.handle(BuddyListCommand(startat), callback)

    def buddystate(self, startat, callback=None):
        """
        Retrieve buddy states

        parameters:
        startat    - number of buddy to start listing from

        structure of parameters:
        startat
        
        """
        return self.handle(BuddyStateCommand(startat), callback)

    def anime(self, aid=None, aname=None, amask= -1, callback=None):
        """
        Get information about an anime

        parameters:
        aid    - anime id
        aname    - name of the anime
        amask    - a bitfield describing what information you want about the anime
        
        structure of parameters:
        (aid|aname) [amask]
        
        structure of amask:
        
        """
        return self.handle(AnimeCommand(aid, aname, amask), callback)

    def episode(self, eid=None, aid=None, aname=None, epno=None, callback=None):
        """
        Get information about an episode

        parameters:
        eid    - episode id
        aid    - anime id
        aname    - name of the anime
        epno    - number of the episode

        structure of parameters:
        eid
        (aid|aname) epno
        
        """
        return self.handle(EpisodeCommand(eid, aid, aname, epno), callback)

    def file(self, fid=None, size=None, ed2k=None, aid=None, aname=None, gid=None, gname=None, epno=None, fmask= -1, amask=0, callback=None):
        """
        Get information about a file

        parameters:
        fid    - file id
        size    - size of the file
        ed2k    - ed2k-hash of the file
        aid    - anime id
        aname    - name of the anime
        gid    - group id
        gname    - name of the group
        epno    - number of the episode
        fmask    - a bitfield describing what information you want about the file
        amask    - a bitfield describing what information you want about the anime

        structure of parameters:
        fid [fmask] [amask]
        size ed2k [fmask] [amask]
        (aid|aname) (gid|gname) epno [fmask] [amask]

        structure of fmask:
        bit    key        description
        0    -        -
        1    aid        aid
        2    eid        eid
        3    gid        gid
        4    lid        lid
        5    -        -
        6    -        -
        7    -        -
        8    state        state
        9    size        size
        10    ed2k        ed2k
        11    md5        md5
        12    sha1        sha1
        13    crc32        crc32
        14    -        -
        15    -        -
        16    dublang        dub language
        17    sublang        sub language
        18    quality        quality
        19    source        source
        20    audiocodec    audio codec
        21    audiobitrate    audio bitrate
        22    videocodec        video codec
        23    videobitrate    video bitrate
        24    resolution    video resolution
        25    filetype    file type (extension)
        26    length        length in seconds
        27    description    description
        28    -        -
        29    -        -
        30    filename    anidb file name
        31    -        -
        
        structure of amask:
        bit    key        description
        0    gname        group name
        1    gshortname    group short name
        2    -        -
        3    -        -
        4    -        -
        5    -        -
        6    -        -
        7    -        -
        8    epno        epno
        9    epname        ep english name
        10    epromaji    ep romaji name
        11    epkanji        ep kanji name
        12    -        -
        13    -        -
        14    -        -
        15    -        -
        16    totaleps    anime total episodes
        17    lastep        last episode nr (highest, not special)
        18    year        year
        19    type        type
        20    romaji        romaji name
        21    kanji        kanji name
        22    name        english name
        23    othername    other name
        24    shortnames    short name list
        25    synonyms    synonym list
        26    categories    category list
        27    relatedaids    related aid list
        28    producernames    producer name list
        29    producerids    producer id list
        30    -        -
        31    -        -
        
        """
        return self.handle(FileCommand(fid, size, ed2k, aid, aname, gid, gname, epno, fmask, amask), callback)

    def group(self, gid=None, gname=None, callback=None):
        """
        Get information about a group

        parameters:
        gid    - group id
        gname    - name of the group

        structure of parameters:
        (gid|gname)
        
        """
        return self.handle(GroupCommand(gid, gname), callback)

    def groupstatus(self, aid=None, state=None, callback=None):
        """
        Returns a list of group names and ranges of episodes released by the group for a given anime.
        parameters:
        aid    - anime id
        state - If state is not supplied, groups with a completion state of 'ongoing', 'finished', or 'complete' are returned
            state values:
                1 -> ongoing
                2 -> stalled
                3 -> complete
                4 -> dropped
                5 -> finished
                6 -> specials only
        """
        return self.handle(GroupstatusCommand(aid, state), callback)

    def producer(self, pid=None, pname=None, callback=None):
        """
        Get information about a producer

        parameters:
        pid    - producer id
        pname    - name of the producer

        structure of parameters:
        (pid|pname)
        
        """

        return self.handle(ProducerCommand(pid, pname), callback)

    def mylist(self, lid=None, fid=None, size=None, ed2k=None, aid=None, aname=None, gid=None, gname=None, epno=None, callback=None):
        """
        Get information about your mylist

        parameters:
        lid    - mylist id
        fid    - file id
        size    - size of the file
        ed2k    - ed2k-hash of the file
        aid    - anime id
        aname    - name of the anime
        gid    - group id
        gname    - name of the group
        epno    - number of the episode

        structure of parameters:
        lid
        fid
        size ed2k
        (aid|aname) (gid|gname) epno
        
        """
        return self.handle(MyListCommand(lid, fid, size, ed2k, aid, aname, gid, gname, epno), callback)

    def mylistadd(self, lid=None, fid=None, size=None, ed2k=None, aid=None, aname=None, gid=None, gname=None, epno=None, edit=None, state=None, viewed=None, source=None, storage=None, other=None, callback=None):
        """
        Add/Edit information to/in your mylist

        parameters:
        lid    - mylist id
        fid    - file id
        size    - size of the file
        ed2k    - ed2k-hash of the file
        aid    - anime id
        aname    - name of the anime
        gid    - group id
        gname    - name of the group
        epno    - number of the episode
        edit    - whether to add to mylist or edit an existing entry (0=add,1=edit)
        state    - the location of the file
        viewed    - whether you have watched the file (0=unwatched,1=watched)
        source    - where you got the file (bittorrent,dc++,ed2k,...)
        storage    - for example the title of the cd you have this on
        other    - other data regarding this file

        structure of parameters:
        lid edit=1 [state viewed source storage other]
        fid [state viewed source storage other] [edit]
        size ed2k [state viewed source storage other] [edit]
        (aid|aname) (gid|gname) epno [state viewed source storage other]
        (aid|aname) edit=1 [(gid|gname) epno] [state viewed source storage other]

        structure of state:
        value    meaning
        0    unknown    - state is unknown or the user doesn't want to provide this information
        1    on hdd    - the file is stored on hdd
        2    on cd    - the file is stored on cd
        3    deleted    - the file has been deleted or is not available for other reasons (i.e. reencoded)
        
        structure of epno:
        value    meaning
        x    target episode x
        0    target all episodes
        -x    target all episodes upto x
        
        """
        return self.handle(MyListAddCommand(lid, fid, size, ed2k, aid, aname, gid, gname, epno, edit, state, viewed, source, storage, other), callback)

    def mylistdel(self, lid=None, fid=None, aid=None, aname=None, gid=None, gname=None, epno=None, callback=None):
        """
        Delete information from your mylist

        parameters:
        lid    - mylist id
        fid    - file id
        size    - size of the file
        ed2k    - ed2k-hash of the file
        aid    - anime id
        aname    - name of the anime
        gid    - group id
        gname    - name of the group
        epno    - number of the episode

        structure of parameters:
        lid
        fid
        (aid|aname) (gid|gname) epno

        """
        return self.handle(MyListCommand(lid, fid, aid, aname, gid, gname, epno), callback)

    def myliststats(self, callback=None):
        """
        Get summary information of your mylist
        
        """
        return self.handle(MyListStatsCommand(), callback)

    def vote(self, type, id=None, name=None, value=None, epno=None, callback=None):
        """
        Rate an anime/episode/group

        parameters:
        type    - type of the vote
        id    - anime/group id
        name    - name of the anime/group
        value    - the vote
        epno    - number of the episode

        structure of parameters:
        type (id|name) [value] [epno]

        structure of type:
        value    meaning
        1    rate an anime (episode if you also specify epno)
        2    rate an anime temporarily (you haven't watched it all)
        3    rate a group

        structure of value:
        value     meaning
        -x     revoke vote
        0     get old vote
        100-1000 give vote
        
        """
        return self.handle(VoteCommand(type, id, name, value, epno), callback)

    def randomanime(self, type, callback=None):
        """
        Get information of random anime
        
        parameters:
        type    - where to take the random anime

        structure of parameters:
        type

        structure of type:
        value   meaning
        0    db
        1    watched
        2    unwatched
        3    mylist
        
        """
        return self.handle(RandomAnimeCommand(type), callback)

    def ping(self, callback=None):
        """
        Test connectivity to AniDB UDP API
        
        """
        return self.handle(PingCommand(), callback)

    def encrypt(self, user, apipassword, type=None, callback=None):
        """
        Encrypt all future traffic

        parameters:
        user        - your username
        apipassword - your api password
        type        - type of encoding (1=128bit AES)

        structure of parameters:
        user [type]
        
        """
        return self.handle(EncryptCommand(user, apipassword, type), callback)

    def encoding(self, name, callback=None):
        """
        Change encoding used in messages

        parameters:
        name    - name of the encoding

        structure of parameters:
        name

        comments:
        DO NOT USE THIS!
        utf8 is the only encoding which will support all the text in anidb responses
        the responses have japanese, russian, french and probably other alphabets as well
        even if you can't display utf-8 locally, don't change the server-client -connections encoding
        rather, make python convert the encoding when you DISPLAY the text
        it's better that way, let it go as utf8 to databases etc. because then you've the real data stored
        
        """
        raise AniDBStupidUserError, "pylibanidb sets the encoding to utf8 as default and it's stupid to use any other encoding. you WILL lose some data if you use other encodings, and now you've been warned. you will need to modify the code yourself if you want to do something as stupid as changing the encoding"
        return self.handle(EncodingCommand(name), callback)

    def sendmsg(self, to, title, body, callback=None):
        """
        Send message

        parameters:
        to    - name of the user you want as the recipient
        title    - title of the message
        body    - the message

        structure of parameters:
        to title body
        
        """
        return self.handle(SendMsgCommand(to, title, body), callback)

    def user(self, user, callback=None):
        """
        Retrieve user id

        parameters:
        user    - username of the user

        structure of parameters:
        user
        
        """
        return self.handle(UserCommand(user), callback)

    def uptime(self, callback=None):
        """
        Retrieve server uptime
        
        """
        return self.handle(UptimeCommand(), callback)

    def version(self, callback=None):
        """
        Retrieve server version
        
        """
        return self.handle(VersionCommand(), callback)
