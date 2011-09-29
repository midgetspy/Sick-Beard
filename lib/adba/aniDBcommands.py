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

from threading import Lock
from aniDBresponses import *
from aniDBerrors import *

class Command:
	queue={None:None}
	def __init__(self,command,**parameters):
		self.command=command
		self.parameters=parameters
		self.raw=self.flatten(command,parameters)

		self.mode=None
		self.callback=None
		self.waiter=Lock()
		self.waiter.acquire()
	
	def __repr__(self):
		return "Command(%s,%s) %s\n%s\n"%(repr(self.tag),repr(self.command),repr(self.parameters),self.raw_data())
	
	def authorize(self,mode,tag,session,callback):
		self.mode=mode
		self.callback=callback
		self.tag=tag
		self.session=session
		
		self.parameters['tag']=tag
		self.parameters['s']=session
	
	def handle(self,resp):
		self.resp=resp
		if self.mode==1:
			self.waiter.release()
		elif self.mode==2:
			self.callback(resp)
	
	def wait_response(self):
		self.waiter.acquire()
	
	def flatten(self,command,parameters):
		tmp=[]
		for key,value in parameters.iteritems():
			if value==None:
				continue
			tmp.append("%s=%s"%(self.escape(key),self.escape(value)))
		return ' '.join([command,'&'.join(tmp)])
	
	def escape(self,data):
		return str(data).replace('&','&amp;')
	
	def raw_data(self):
		self.raw=self.flatten(self.command,self.parameters)
		return self.raw
		
	def cached(self,interface,database):
		return None
	
	def cache(self,interface,database):
		pass
		
#first run
class AuthCommand(Command):
	def __init__(self,username,password,protover,client,clientver,nat=None,comp=None,enc=None,mtu=None):
		parameters={'user':username,'pass':password,'protover':protover,'client':client,'clientver':clientver,'nat':nat,'comp':comp,'enc':enc,'mtu':mtu}
		Command.__init__(self,'AUTH',**parameters)

class LogoutCommand(Command):
	def __init__(self):
		Command.__init__(self,'LOGOUT')

#third run (at the same time as second)
class PushCommand(Command):
	def __init__(self,notify,msg,buddy=None):
		parameters={'notify':notify,'msg':msg,'buddy':buddy}
		Command.__init__(self,'PUSH',**parameters)

class PushAckCommand(Command):
	def __init__(self,nid):
		parameters={'nid':nid}
		Command.__init__(self,'PUSHACK',**parameters)

class NotifyAddCommand(Command):
	def __init__(self,aid=None,gid=None,type=None,priority=None):
		if not (aid or gid) or (aid and gid):
			raise AniDBIncorrectParameterError,"You must provide aid OR gid for NOTIFICATIONADD command"
		parameters={'aid':aid,"gid":gid,"type":type,"priority":priority}
		Command.__init__(self,'NOTIFICATIONADD',**parameters)
		
class NotifyCommand(Command):
	def __init__(self,buddy=None):
		parameters={'buddy':buddy}
		Command.__init__(self,'NOTIFY',**parameters)

class NotifyListCommand(Command):
	def __init__(self):
		Command.__init__(self,'NOTIFYLIST')

class NotifyGetCommand(Command):
	def __init__(self,type,id):
		parameters={'type':type,'id':id}
		Command.__init__(self,'NOTIFYGET',**parameters)

class NotifyAckCommand(Command):
	def __init__(self,type,id):
		parameters={'type':type,'id':id}
		Command.__init__(self,'NOTIFYACK',**parameters)

class BuddyAddCommand(Command):
	def __init__(self,uid=None,uname=None):
		if not (uid or uname) or (uid and uname):
			raise AniDBIncorrectParameterError,"You must provide <u(id|name)> for BUDDYADD command"
		parameters={'uid':uid,'uname':uname.lower()}
		Command.__init__(self,'BUDDYADD',**parameters)

class BuddyDelCommand(Command):
	def __init__(self,uid):
		parameters={'uid':uid}
		Command.__init__(self,'BUDDYDEL',**parameters)

class BuddyAcceptCommand(Command):
	def __init__(self,uid):
		parameters={'uid':uid}
		Command.__init__(self,'BUDDYACCEPT',**parameters)

class BuddyDenyCommand(Command):
	def __init__(self,uid):
		parameters={'uid':uid}
		Command.__init__(self,'BUDDYDENY',**parameters)

class BuddyListCommand(Command):
	def __init__(self,startat):
		parameters={'startat':startat}
		Command.__init__(self,'BUDDYLIST',**parameters)

class BuddyStateCommand(Command):
	def __init__(self,startat):
		parameters={'startat':startat}
		Command.__init__(self,'BUDDYSTATE',**parameters)

#first run
class AnimeCommand(Command):
	def __init__(self,aid=None,aname=None,amask=None):
		if not (aid or aname):
			raise AniDBIncorrectParameterError,"You must provide <a(id|name)> for ANIME command"
		parameters={'aid':aid,'aname':aname,'amask':amask}
		Command.__init__(self,'ANIME',**parameters)

class EpisodeCommand(Command):
	def __init__(self,eid=None,aid=None,aname=None,epno=None):
		if not (eid or ((aname or aid) and epno)) or (aname and aid) or (eid and (aname or aid or epno)):
			raise AniDBIncorrectParameterError,"You must provide <eid XOR a(id|name)+epno> for EPISODE command"
		parameters={'eid':eid,'aid':aid,'aname':aname,'epno':epno}
		Command.__init__(self,'EPISODE',**parameters)

class FileCommand(Command):
	def __init__(self,fid=None,size=None,ed2k=None,aid=None,aname=None,gid=None,gname=None,epno=None,fmask=None,amask=None):
		if not (fid or (size and ed2k) or ((aid or aname) and (gid or gname) and epno)) or (fid and (size or ed2k or aid or aname or gid or gname or epno)) or ((size and ed2k) and (fid or aid or aname or gid or gname or epno)) or (((aid or aname) and (gid or gname) and epno) and (fid or size or ed2k)) or (aid and aname) or (gid and gname):
			raise AniDBIncorrectParameterError,"You must provide <fid XOR size+ed2k XOR a(id|name)+g(id|name)+epno> for FILE command"
		parameters={'fid':fid,'size':size,'ed2k':ed2k,'aid':aid,'aname':aname,'gid':gid,'gname':gname,'epno':epno,'fmask':fmask,'amask':amask}
		Command.__init__(self,'FILE',**parameters)

class GroupCommand(Command):
	def __init__(self,gid=None,gname=None):
		if not (gid or gname) or (gid and gname):
			raise AniDBIncorrectParameterError,"You must provide <g(id|name)> for GROUP command"
		parameters={'gid':gid,'gname':gname}
		Command.__init__(self,'GROUP',**parameters)

class GroupstatusCommand(Command):
	def __init__(self,aid=None,status=None):
		if not aid:
			raise AniDBIncorrectParameterError,"You must provide aid for GROUPSTATUS command"
		parameters={'aid':aid,'status':status}
		Command.__init__(self,'GROUPSTATUS',**parameters)

class ProducerCommand(Command):
	def __init__(self,pid=None,pname=None):
		if not (pid or pname) or (pid and pname):
			raise AniDBIncorrectParameterError,"You must provide <p(id|name)> for PRODUCER command"
		parameters={'pid':pid,'pname':pname}
		Command.__init__(self,'PRODUCER',**parameters)
	
	def cached(self,intr,db):
		pid=self.parameters['pid']
		pname=self.parameters['pname']
		
		codes=('pid', 'name', 'shortname', 'othername', 'type', 'pic', 'url')
		names=','.join([code for code in codes if code!=''])
		ruleholder=(pid and 'pid=%s' or '(name=%s OR shortname=%s OR othername=%s)')
		rulevalues=(pid and [pid] or [pname,pname,pname])
		
		rows=db.select('ptb',names,ruleholder+" AND status&8",*rulevalues)
		
		if len(rows)>1:
			raise AniDBInternalError,"It shouldn't be possible for database to return more than 1 line for PRODUCER cache"
		elif not len(rows):
			return None
		else:
			resp=ProducerResponse(self,None,'245','CACHED PRODUCER',[list(rows[0])])
			resp.parse()
			return resp
		
	def cache(self,intr,db):
		if self.resp.rescode!='245' or self.cached(intr,db):
			return

		codes=('pid', 'name', 'shortname', 'othername', 'type', 'pic', 'url')
		if len(db.select('ptb','pid','pid=%s',self.resp.datalines[0]['pid'])):
			sets='status=status|15,'+','.join([code+'=%s' for code in codes if code!=''])
			values=[self.resp.datalines[0][code] for code in codes if code!='']+[self.resp.datalines[0]['pid']]

			db.update('ptb',sets,'pid=%s',*values)
		else:
			names='status,'+','.join([code for code in codes if code!=''])
			valueholders='0,'+','.join(['%s'for code in codes if code!=''])
			values=[self.resp.datalines[0][code] for code in codes if code!='']
		
			db.insert('ptb',names,valueholders,*values)

class MyListCommand(Command):
	def __init__(self,lid=None,fid=None,size=None,ed2k=None,aid=None,aname=None,gid=None,gname=None,epno=None):
		if not (lid or fid or (size and ed2k) or (aid or aname)) or (lid and (fid or size or ed2k or aid or aname or gid or gname or epno)) or (fid and (lid or size or ed2k or aid or aname or gid or gname or epno)) or ((size and ed2k) and (lid or fid or aid or aname or gid or gname or epno)) or ((aid or aname) and (lid or fid or size or ed2k)) or (aid and aname) or (gid and gname):
			raise AniDBIncorrectParameterError,"You must provide <lid XOR fid XOR size+ed2k XOR a(id|name)+g(id|name)+epno> for MYLIST command"
		parameters={'lid':lid,'fid':fid,'size':size,'ed2k':ed2k,'aid':aid,'aname':aname,'gid':gid,'gname':gname,'epno':epno}
		Command.__init__(self,'MYLIST',**parameters)

	def cached(self,intr,db):
		lid=self.parameters['lid']
		fid=self.parameters['fid']
		size=self.parameters['size']
		ed2k=self.parameters['ed2k']
		aid=self.parameters['aid']
		aname=self.parameters['aname']
		gid=self.parameters['gid']
		gname=self.parameters['gname']
		epno=self.parameters['epno']

		names=','.join([code for code in MylistResponse(None,None,None,None,[]).codetail if code!=''])
		
		if lid:
			ruleholder="lid=%s"
			rulevalues=[lid]
		elif fid or size or ed2k:
			resp=intr.file(fid=fid,size=size,ed2k=ed2k)
			if resp.rescode!='220':
				resp=NoSuchMylistResponse(self,None,'321','NO SUCH ENTRY (FILE NOT FOUND)',[])
				resp.parse()
				return resp
			fid=resp.datalines[0]['fid']
			
			ruleholder="fid=%s"
			rulevalues=[fid]
		else:
			resp=intr.anime(aid=aid,aname=aname)
			if resp.rescode!='230':
				resp=NoSuchFileResponse(self,None,'321','NO SUCH ENTRY (ANIME NOT FOUND)',[])
				resp.parse()
				return resp
			aid=resp.datalines[0]['aid']

			resp=intr.group(gid=gid,gname=gname)
			if resp.rescode!='250':
				resp=NoSuchFileResponse(self,None,'321','NO SUCH ENTRY (GROUP NOT FOUND)',[])
				resp.parse()
				return resp
			gid=resp.datalines[0]['gid']

			resp=intr.episode(aid=aid,epno=epno)
			if resp.rescode!='240':
				resp=NoSuchFileResponse(self,None,'321','NO SUCH ENTRY (EPISODE NOT FOUND)',[])
				resp.parse()
				return resp
			eid=resp.datalines[0]['eid']

			ruleholder="aid=%s AND eid=%s AND gid=%s"
			rulevalues=[aid,eid,gid]

		rows=db.select('ltb',names,ruleholder+" AND status&8",*rulevalues)

		if len(rows)>1:
			#resp=MultipleFilesFoundResponse(self,None,'322','CACHED MULTIPLE FILES FOUND',/*get fids from rows, not gonna do this as you haven't got a real cache out of these..*/)
			return None
		elif not len(rows):
			return None
		else:
			resp=MylistResponse(self,None,'221','CACHED MYLIST',[list(rows[0])])
			resp.parse()
			return resp
	
	def cache(self,intr,db):
		if self.resp.rescode!='221' or self.cached(intr,db):
			return

		codes=MylistResponse(None,None,None,None,[]).codetail
		if len(db.select('ltb','lid','lid=%s',self.resp.datalines[0]['lid'])):
			sets='status=status|15,'+','.join([code+'=%s' for code in codes if code!=''])
			values=[self.resp.datalines[0][code] for code in codes if code!='']+[self.resp.datalines[0]['lid']]

			db.update('ltb',sets,'lid=%s',*values)
		else:
			names='status,'+','.join([code for code in codes if code!=''])
			valueholders='15,'+','.join(['%s' for code in codes if code!=''])
			values=[self.resp.datalines[0][code] for code in codes if code!='']

			db.insert('ltb',names,valueholders,*values)

class MyListAddCommand(Command):
	def __init__(self,lid=None,fid=None,size=None,ed2k=None,aid=None,aname=None,gid=None,gname=None,epno=None,edit=None,state=None,viewed=None,source=None,storage=None,other=None):
		if not (lid or fid or (size and ed2k) or ((aid or aname) and (gid or gname))) or (lid and (fid or size or ed2k or aid or aname or gid or gname or epno)) or (fid and (lid or size or ed2k or aid or aname or gid or gname or epno)) or ((size and ed2k) and (lid or fid or aid or aname or gid or gname or epno)) or (((aid or aname) and (gid or gname)) and (lid or fid or size or ed2k)) or (aid and aname) or (gid and gname) or (lid and not edit):
			raise AniDBIncorrectParameterError,"You must provide <lid XOR fid XOR size+ed2k XOR a(id|name)+g(id|name)+epno> for MYLISTADD command"
		parameters={'lid':lid,'fid':fid,'size':size,'ed2k':ed2k,'aid':aid,'aname':aname,'gid':gid,'gname':gname,'epno':epno,'edit':edit,'state':state,'viewed':viewed,'source':source,'storage':storage,'other':other}
		Command.__init__(self,'MYLISTADD',**parameters)

class MyListDelCommand(Command):
	def __init__(self,lid=None,fid=None,aid=None,aname=None,gid=None,gname=None,epno=None):
		if not (lid or fid or ((aid or aname) and (gid or gname) and epno)) or (lid and (fid or aid or aname or gid or gname or epno)) or (fid and (lid or aid or aname or gid or gname or epno)) or (((aid or aname) and (gid or gname) and epno) and (lid or fid)) or (aid and aname) or (gid and gname):
			raise AniDBIncorrectParameterError,"You must provide <lid+edit=1 XOR fid XOR a(id|name)+g(id|name)+epno> for MYLISTDEL command"
		parameters={'lid':lid,'fid':fid,'aid':aid,'aname':aname,'gid':gid,'gname':gname,'epno':epno}
		Command.__init__(self,'MYLISTDEL',**parameters)

class MyListStatsCommand(Command):
	def __init__(self):
		Command.__init__(self,'MYLISTSTATS')

class VoteCommand(Command):
	def __init__(self,type,id=None,name=None,value=None,epno=None):
		if not (id or name) or (id and name):
			raise AniDBIncorrectParameterError,"You must provide <(id|name)> for VOTE command"
		parameters={'type':type,'id':id,'name':name,'value':value,'epno':epno}
		Command.__init__(self,'VOTE',**parameters)

class RandomAnimeCommand(Command):
	def __init__(self,type):
		parameters={'type':type}
		Command.__init__(self,'RANDOMANIME',**parameters)

class PingCommand(Command):
	def __init__(self):
		Command.__init__(self,'PING')

#second run
class EncryptCommand(Command):
	def __init__(self,user,apipassword,type):
		self.apipassword=apipassword
		parameters={'user':user.lower(),'type':type}
		Command.__init__(self,'ENCRYPT',**parameters)

class EncodingCommand(Command):
	def __init__(self,name):
		parameters={'name':type}
		Command.__init__(self,'ENCODING',**parameters)

class SendMsgCommand(Command):
	def __init__(self,to,title,body):
		if len(title)>50 or len(body)>900:
			raise AniDBIncorrectParameterError,"Title must not be longer than 50 chars and body must not be longer than 900 chars for SENDMSG command"
		parameters={'to':to.lower(),'title':title,'body':body}
		Command.__init__(self,'SENDMSG',**parameters)

class UserCommand(Command):
	def __init__(self,user):
		parameters={'user':user}
		Command.__init__(self,'USER',**parameters)

class UptimeCommand(Command):
	def __init__(self):
		Command.__init__(self,'UPTIME')

class VersionCommand(Command):
	def __init__(self):
		Command.__init__(self,'VERSION')

