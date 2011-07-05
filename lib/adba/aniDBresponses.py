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

from types import FunctionType
from aniDBmaper import AniDBMaper

class ResponseResolver:
	def __init__(self,data):
		restag,rescode,resstr,datalines=self.parse(data)
		
		self.restag=restag
		self.rescode=rescode
		self.resstr=resstr
		self.datalines=datalines

	def parse(self,data):
		resline=data.split('\n',1)[0]
		lines=data.split('\n')[1:-1]

		rescode,resstr=resline.split(' ',1)
		if rescode[0]=='T':
			restag=rescode
			rescode,resstr=resstr.split(' ',1)
		else:
			restag=None

		datalines=[]
		for line in lines:
			datalines.append(line.split('|'))
		
		
		return restag,rescode,resstr,datalines
	
	def resolve(self,cmd):
		return responses[self.rescode](cmd,self.restag,self.rescode,self.resstr,self.datalines)


class Response:
	def __init__(self,cmd,restag,rescode,resstr,rawlines):
		self.req=cmd
		self.restag=restag
		self.rescode=rescode
		self.resstr=resstr
		self.rawlines=rawlines
		self.maper = AniDBMaper()

	def __repr__(self):
		tmp="%s(%s,%s,%s) %s\n"%(self.__class__.__name__,repr(self.restag),repr(self.rescode),repr(self.resstr),repr(self.attrs))
		
		m=0
		for line in self.datalines:
			for k,v in line.iteritems():
				if len(k)>m:
					m=len(k)
		
		for line in self.datalines:
			tmp+="  Line:\n"
			for k,v in line.iteritems():
				tmp+="    %s:%s %s\n"%(k,(m-len(k))*' ',v)
		return tmp

	def parse(self):
		tmp=self.resstr.split(' ',len(self.codehead))
		self.attrs=dict(zip(self.codehead,tmp[:-1]))
		self.resstr=tmp[-1]
		
		self.datalines=[]
		for rawline in self.rawlines:
			normal=dict(zip(self.codetail,rawline))
			rawline=rawline[len(self.codetail):]
			rep=[]
			if len(self.coderep):
				while rawline:
					tmp=dict(zip(self.coderep,rawline))
					rawline=rawline[len(self.coderep):]
					rep.append(tmp)
			#normal['rep']=rep
			self.datalines.append(normal)
	
	def handle(self):
		if self.req:
			self.req.handle(self)

class LoginAcceptedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:
		sesskey	- session key
		address	- your address (ip:port) as seen by the server

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='LOGIN_ACCEPTED'
		self.codetail=()
		self.coderep=()

		nat=cmd.parameters['nat']
		nat=int(nat==None and nat or '0')
		if nat:
			self.codehead=('sesskey','address')
		else:
			self.codehead=('sesskey',)

class LoginAcceptedNewVerResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:
		sesskey	- session key
		address	- your address (ip:port) as seen by the server

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='LOGIN_ACCEPTED_NEW_VER'
		self.codetail=()
		self.coderep=()

		nat=cmd.parameters['nat']
		nat=int(nat==None and nat or '0')
		if nat:
			self.codehead=('sesskey','address')
		else:
			self.codehead=('sesskey',)

class LoggedOutResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='LOGGED_OUT'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class ResourceResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='RESOURCE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class StatsResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='STATS'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class TopResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='TOP'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class UptimeResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		uptime	- udpserver uptime in milliseconds

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='UPTIME'
		self.codehead=()
		self.codetail=('uptime',)
		self.coderep=()

class EncryptionEnabledResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:
		salt	- salt

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ENCRYPTION_ENABLED'
		self.codehead=('salt',)
		self.codetail=()
		self.coderep=()

class MylistEntryAddedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		entrycnt - number of entries added

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='MYLIST_ENTRY_ADDED'
		self.codehead=()
		self.codetail=('entrycnt',)
		self.coderep=()

class MylistEntryDeletedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		entrycnt - number of entries

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='MYLIST_ENTRY_DELETED'
		self.codehead=()
		self.codetail=('entrycnt',)
		self.coderep=()

class AddedFileResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ADDED_FILE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class AddedStreamResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ADDED_STREAM'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class EncodingChangedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ENCODING_CHANGED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class FileResponse(Response):
	
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		eid		episode id
		gid		group id
		lid		mylist id
		state		state
		size		size
		ed2k		ed2k
		md5		md5
		sha1		sha1
		crc32		crc32
		dublang		dub language
		sublang		sub language
		quality		quality
		source		source
		audiocodec	audio codec
		audiobitrate	audio bitrate
		videocodec	video codec
		videobitrate	video bitrate
		resolution	video resolution
		filetype	file type (extension)
		length		length in seconds
		description	description
		filename	anidb file name
		gname		group name
		gshortname	group short name
		epno		number of episode
		epname		ep english name
		epromaji	ep romaji name
		epkanji		ep kanji name
		totaleps	anime total episodes
		lastep		last episode nr (highest, not special)
		year		year
		type		type
		romaji		romaji name
		kanji		kanji name
		name		english name
		othername	other name
		shortnames	short name list
		synonyms	synonym list
		categories	category list
		relatedaids	related aid list
		producernames	producer name list
		producerids	producer id list
		
		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='FILE'
		self.codehead=()
		self.coderep=()
		
		fmask=cmd.parameters['fmask']
		amask=cmd.parameters['amask']
		
		codeListF = self.maper.getFileCodesF(fmask)
		codeListA = self.maper.getFileCodesA(amask)
		#print "File - codelistF: "+str(codeListF)
		#print "File - codelistA: "+str(codeListA)
		
		
		self.codetail=tuple(['fid']+codeListF+codeListA)

class MylistResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		lid	 - mylist id
		fid	 - file id
		eid	 - episode id
		aid	 - anime id
		gid	 - group id
		date	 - date when you added this to mylist
		state	 - the location of the file
		viewdate - date when you marked this watched
		storage	 - for example the title of the cd you have this on
		source	 - where you got the file (bittorrent,dc++,ed2k,...)
		other	 - other data regarding this file
		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='MYLIST'
		self.codehead=()
		self.codetail=('lid', 'fid', 'eid', 'aid', 'gid', 'date', 'state', 'viewdate', 'storage', 'source', 'other')
		self.coderep=()

class MylistStatsResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:
		
		data:
		animes		- animes
		eps		- eps
		files		- files
		filesizes	- size of files
		animesadded	- added animes
		epsadded	- added eps
		filesadded	- added files
		groupsadded	- added groups
		leechperc	- leech %
		lameperc	- lame %
		viewedofdb	- viewed % of db
		mylistofdb	- mylist % of db
		viewedofmylist	- viewed % of mylist
		viewedeps	- number of viewed eps
		votes		- votes
		reviews		- reviews
		
		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='MYLIST_STATS'
		self.codehead=()
		self.codetail=('animes', 'eps', 'files', 'filesizes', 'animesadded', 'epsadded', 'filesadded', 'groupsadded', 'leechperc', 'lameperc', 'viewedofdb', 'mylistofdb', 'viewedofmylist', 'viewedeps', 'votes', 'reviews')
		self.coderep=()

class AnimeResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ANIME'
		self.codehead=()
		self.coderep=()
		
		#TODO: impl random anime
		amask = cmd.parameters['amask']
		codeList = self.maper.getAnimeCodesA(amask)
		self.codetail=tuple(codeList)

class AnimeBestMatchResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ANIME_BEST_MATCH'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class RandomanimeResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='RANDOMANIME'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class EpisodeResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		eid	- episode id
		aid	- anime id
		length	- length
		rating	- rating
		votes	- votes
		epno	- number of episode
		name	- english name of episode
		romaji	- romaji name of episode
		kanji	- kanji name of episode

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='EPISODE'
		self.codehead=()
		self.codetail=('eid', 'aid', 'length', 'rating', 'votes', 'epno', 'name', 'romaji', 'kanji')
		self.coderep=()

class ProducerResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		pid	  - producer id
		name	  - name of producer
		shortname - short name
		othername - other name
		type	  - type
		pic	  - picture name
		url	  - home page url

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='PRODUCER'
		self.codehead=()
		self.codetail=('pid', 'name', 'shortname', 'othername', 'type', 'pic', 'url')
		self.coderep=()

class GroupResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		gid	   - group id
		rating	   - rating
		votes	   - votes
		animes	   - anime count
		files	   - file count
		name	   - name
		shortname  - short
		ircchannel - irc channel
		ircserver  - irc server
		url	   - url

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='GROUP'
		self.codehead=()
		self.codetail=('gid', 'rating', 'votes', 'animes', 'files', 'name', 'shortname', 'ircchannel', 'ircserver', 'url')
		self.coderep=()
		
class GroupstatusResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		gid	   - group id
		rating	   - rating
		votes	   - votes
		animes	   - anime count
		files	   - file count
		name	   - name
		shortname  - short
		ircchannel - irc channel
		ircserver  - irc server
		url	   - url

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='GROUPSTATUS'
		self.codehead=()
		self.codetail=('gid', 'name', 'state', ' last_episode_number', 'rating', 'votes', 'episode_range')
		self.coderep=()

class BuddyListResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:
		start	- mylist entry number of first buddy on this packet
		end	- mylist entry number of last buddy on this packet
		total	- total number of buddies on mylist

		data:
		uid	- uid
		name	- username
		state	- state

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='BUDDY_LIST'
		self.codehead=('start', 'end', 'total')
		self.codetail=('uid', 'username', 'state')
		self.coderep=()

class BuddyStateResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:
		start	- mylist entry number of first buddy on this packet
		end	- mylist entry number of last buddy on this packet
		total	- total number of buddies on mylist

		data:
		uid	- uid
		state	- online state

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='BUDDY_STATE'
		self.codehead=('start', 'end', 'total')
		self.codetail=('uid', 'state')
		self.coderep=()

class BuddyAddedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='BUDDY_ADDED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class BuddyDeletedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='BUDDY_DELETED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class BuddyAcceptedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='BUDDY_ACCEPTED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class BuddyDeniedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='BUDDY_DENIED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class VotedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		name	- aname/ename/gname

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='VOTED'
		self.codehead=()
		self.codetail=('name',)
		self.coderep=()

class VoteFoundResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		name	- aname/ename/gname
		value	- vote value

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='VOTE_FOUND'
		self.codehead=()
		self.codetail=('name', 'value')
		self.coderep=()

class VoteUpdatedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		name	- aname/ename/gname
		value	- vote value

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='VOTE_UPDATED'
		self.codehead=()
		self.codetail=('name', 'value')
		self.coderep=()

class VoteRevokedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		name	- aname/ename/gname
		value	- vote value

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='VOTE_REVOKED'
		self.codehead=()
		self.codetail=('name', 'value')
		self.coderep=()



class NotificationAddedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data: 
		nid - notofication id

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFICATION_ITEM_ADDED'
		self.codehead=()
		self.codetail=('nid')
		self.coderep=()

class NotificationUpdatedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data: 
		nid - notofication id

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFICATION_ITEM_UPDATED'
		self.codehead=()
		self.codetail=('nid')
		self.coderep=()

class NotificationEnabledResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFICATION_ENABLED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NotificationNotifyResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:
		nid	- notify packet id

		data:
		aid	- anime id
		date	- date
		count	- count
		name	- name of the anime

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFICATION_NOTIFY'
		self.codehead=('nid',)
		self.codetail=('aid', 'date', 'count', 'name')
		self.coderep=()

class NotificationMessageResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:
		nid	- notify packet id

		data:
		type	- type
		date	- date
		uid	- user id of the sender
		name	- name of the sender
		subject	- subject

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFICATION_MESSAGE'
		self.codehead=('nid',)
		self.codetail=('type', 'date', 'uid', 'name', 'subject')
		self.coderep=()

class NotificationBuddyResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:
		nid	- notify packet id

		data:
		uid	- buddy uid
		type	- event type

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFICATION_BUDDY'
		self.codehead=('notify_packet_id',)
		self.codetail=('uid', 'type')
		self.coderep=()

class NotificationShutdownResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:
		nid	- notify packet id

		data:
		time	- time offline
		comment	- comment

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFICATION_SHUTDOWN'
		self.codehead=('nid',)
		self.codetail=('time', 'comment')
		self.coderep=()

class PushackConfirmedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='PUSHACK_CONFIRMED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NotifyackSuccessfulMResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFYACK_SUCCESSFUL_M'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NotifyackSuccessfulNResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFYACK_SUCCESSFUL_N'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NotificationResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		notifies - pending notifies
		msgs	 - pending msgs
		buddys	 - number of online buddys
		
		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFICATION'
		self.codehead=()
		self.coderep=()

		buddy=cmd.parameters['buddy']
		buddy=int(buddy!=None and buddy or '0')
		if buddy:
			self.codetail=('notifies','msgs','buddys')
		else:
			self.codetail=('notifies','msgs')

class NotifylistResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		type	- type
		nid	- notify id

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFYLIST'
		self.codehead=()
		self.codetail=('type', 'nid')
		self.coderep=()

class NotifygetMessageResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		nid	- notify id
		uid	- from user id
		uname	- from username
		date	- date
		type	- type
		title	- title
		body	- body

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFYGET_MESSAGE'
		self.codehead=()
		self.codetail=('nid', 'uid', 'uname', 'date', 'type', 'title', 'body')
		self.coderep=()

class NotifygetNotifyResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		aid	- aid
		type	- type
		count	- count
		date	- date
		name	- anime name

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFYGET_NOTIFY'
		self.codehead=()
		self.codetail=('aid', 'type', 'count', 'date', 'name')
		self.coderep=()

class SendmsgSuccessfulResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='SENDMSG_SUCCESSFUL'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class UserResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		uid	- user id

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='USER'
		self.codehead=()
		self.codetail=('uid',)
		self.coderep=()

class PongResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='PONG'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class AuthpongResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='AUTHPONG'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchResourceResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_RESOURCE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class ApiPasswordNotDefinedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='API_PASSWORD_NOT_DEFINED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class FileAlreadyInMylistResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='FILE_ALREADY_IN_MYLIST'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class MylistEntryEditedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		entries	- number of entries edited

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='MYLIST_ENTRY_EDITED'
		self.codehead=()
		self.codetail=('entries',)
		self.coderep=()

class MultipleMylistEntriesResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		name	   - anime title
		eps	   - episodes
		unknowneps - eps with state unknown
		hddeps	   - eps with state on hdd
		cdeps	   - eps with state on cd
		deletedeps - eps with state deleted
		watchedeps - watched eps
		gshortname - group short name
		geps	   - eps for group

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='MULTIPLE_MYLIST_ENTRIES'
		self.codehead=()
		self.codetail=('name', 'eps', 'unknowneps', 'hddeps', 'cdeps', 'deletedeps', 'watchedeps')
		self.coderep=('gshortname', 'geps')

class SizeHashExistsResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='SIZE_HASH_EXISTS'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class InvalidDataResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='INVALID_DATA'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class StreamnoidUsedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='STREAMNOID_USED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchFileResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_FILE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchEntryResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_ENTRY'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class MultipleFilesFoundResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		fid	- file id

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='MULTIPLE_FILES_FOUND'
		self.codehead=()
		self.codetail=()
		self.coderep=('fid',)

class NoGroupsFoundResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO GROUPS FOUND'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchAnimeResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_ANIME'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchEpisodeResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_EPISODE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchProducerResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_PRODUCER'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchGroupResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_GROUP'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class BuddyAlreadyAddedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='BUDDY_ALREADY_ADDED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchBuddyResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_BUDDY'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class BuddyAlreadyAcceptedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='BUDDY_ALREADY_ACCEPTED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class BuddyAlreadyDeniedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='BUDDY_ALREADY_DENIED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchVoteResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_VOTE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class InvalidVoteTypeResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='INVALID_VOTE_TYPE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class InvalidVoteValueResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='INVALID_VOTE_VALUE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class PermvoteNotAllowedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		aname	- name of the anime

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='PERMVOTE_NOT_ALLOWED'
		self.codehead=()
		self.codetail=('aname',)
		self.coderep=()

class AlreadyPermvotedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		name	- aname/ename/gname

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ALREADY_PERMVOTED'
		self.codehead=()
		self.codetail=('name',)
		self.coderep=()

class NotificationDisabledResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOTIFICATION_DISABLED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchPacketPendingResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_PACKET_PENDING'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchEntryMResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_ENTRY_M'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchEntryNResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_ENTRY_N'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchMessageResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_MESSAGE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchNotifyResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_NOTIFY'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchUserResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_USER'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoChanges(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_CHANGES'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NotLoggedInResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NOT_LOGGED_IN'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchMylistFileResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_MYLIST_FILE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchMylistEntryResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_MYLIST_ENTRY'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class LoginFailedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='LOGIN_FAILED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class LoginFirstResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='LOGIN_FIRST'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class AccessDeniedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ACCESS_DENIED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class ClientVersionOutdatedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='CLIENT_VERSION_OUTDATED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class ClientBannedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='CLIENT_BANNED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class IllegalInputOrAccessDeniedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ILLEGAL_INPUT_OR_ACCESS_DENIED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class InvalidSessionResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='INVALID_SESSION'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class NoSuchEncryptionTypeResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='NO_SUCH_ENCRYPTION_TYPE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class EncodingNotSupportedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ENCODING_NOT_SUPPORTED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class BannedResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='BANNED'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class UnknownCommandResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='UNKNOWN_COMMAND'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class InternalServerErrorResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='INTERNAL_SERVER_ERROR'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class AnidbOutOfServiceResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='ANIDB_OUT_OF_SERVICE'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class ServerBusyResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='SERVER_BUSY'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class ApiViolationResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='API_VIOLATION'
		self.codehead=()
		self.codetail=()
		self.coderep=()

class VersionResponse(Response):
	def __init__(self,cmd,restag,rescode,resstr,datalines):
		"""
		attributes:

		data:
		version	- server version

		"""
		Response.__init__(self,cmd,restag,rescode,resstr,datalines)
		self.codestr='VERSION'
		self.codehead=()
		self.codetail=('version',)
		self.coderep=()


responses={
	'200':LoginAcceptedResponse,
	'201':LoginAcceptedNewVerResponse,
	'203':LoggedOutResponse,
	'205':ResourceResponse,
	'206':StatsResponse,
	'207':TopResponse,
	'208':UptimeResponse,
	'209':EncryptionEnabledResponse,
	'210':MylistEntryAddedResponse,
	'211':MylistEntryDeletedResponse,
	'214':AddedFileResponse,
	'215':AddedStreamResponse,
	'219':EncodingChangedResponse,
	'220':FileResponse,
	'221':MylistResponse,
	'222':MylistStatsResponse,
	'225':GroupstatusResponse,
	'230':AnimeResponse,
	'231':AnimeBestMatchResponse,
	'232':RandomanimeResponse,
	'240':EpisodeResponse,
	'245':ProducerResponse,
	'246':NotificationAddedResponse,
	'248':NotificationUpdatedResponse,
	'250':GroupResponse,
	'253':BuddyListResponse,
	'254':BuddyStateResponse,
	'255':BuddyAddedResponse,
	'256':BuddyDeletedResponse,
	'257':BuddyAcceptedResponse,
	'258':BuddyDeniedResponse,
	'260':VotedResponse,
	'261':VoteFoundResponse,
	'262':VoteUpdatedResponse,
	'263':VoteRevokedResponse,
	'270':NotificationEnabledResponse,
	'271':NotificationNotifyResponse,
	'272':NotificationMessageResponse,
	'273':NotificationBuddyResponse,
	'274':NotificationShutdownResponse,
	'280':PushackConfirmedResponse,
	'281':NotifyackSuccessfulMResponse,
	'282':NotifyackSuccessfulNResponse,
	'290':NotificationResponse,
	'291':NotifylistResponse,
	'292':NotifygetMessageResponse,
	'293':NotifygetNotifyResponse,
	'294':SendmsgSuccessfulResponse,
	'295':UserResponse,
	'300':PongResponse,
	'301':AuthpongResponse,
	'305':NoSuchResourceResponse,
	'309':ApiPasswordNotDefinedResponse,
	'310':FileAlreadyInMylistResponse,
	'311':MylistEntryEditedResponse,
	'312':MultipleMylistEntriesResponse,
	'314':SizeHashExistsResponse,
	'315':InvalidDataResponse,
	'316':StreamnoidUsedResponse,
	'320':NoSuchFileResponse,
	'321':NoSuchEntryResponse,
	'322':MultipleFilesFoundResponse,
	'325':NoGroupsFoundResponse,
	'330':NoSuchAnimeResponse,
	'340':NoSuchEpisodeResponse,
	'345':NoSuchProducerResponse,
	'350':NoSuchGroupResponse,
	'355':BuddyAlreadyAddedResponse,
	'356':NoSuchBuddyResponse,
	'357':BuddyAlreadyAcceptedResponse,
	'358':BuddyAlreadyDeniedResponse,
	'360':NoSuchVoteResponse,
	'361':InvalidVoteTypeResponse,
	'362':InvalidVoteValueResponse,
	'363':PermvoteNotAllowedResponse,
	'364':AlreadyPermvotedResponse,
	'370':NotificationDisabledResponse,
	'380':NoSuchPacketPendingResponse,
	'381':NoSuchEntryMResponse,
	'382':NoSuchEntryNResponse,
	'392':NoSuchMessageResponse,
	'393':NoSuchNotifyResponse,
	'394':NoSuchUserResponse,
	'399':NoChanges,
	'403':NotLoggedInResponse,
	'410':NoSuchMylistFileResponse,
	'411':NoSuchMylistEntryResponse,
	'500':LoginFailedResponse,
	'501':LoginFirstResponse,
	'502':AccessDeniedResponse,
	'503':ClientVersionOutdatedResponse,
	'504':ClientBannedResponse,
	'505':IllegalInputOrAccessDeniedResponse,
	'506':InvalidSessionResponse,
	'509':NoSuchEncryptionTypeResponse,
	'519':EncodingNotSupportedResponse,
	'555':BannedResponse,
	'598':UnknownCommandResponse,
	'600':InternalServerErrorResponse,
	'601':AnidbOutOfServiceResponse,
	'602':ServerBusyResponse,
	'666':ApiViolationResponse,
	'998':VersionResponse
}

