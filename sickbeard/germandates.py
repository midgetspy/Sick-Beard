import re
from bs4 import BeautifulSoup

import requests
from sqlalchemy import create_engine, MetaData, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sickbeard import logger
from datetime import datetime, timedelta
import time

##define a database and add stuff to it
#TODO: Rewrite with mappers!
#USE SCOPED SESSIONS ...

engine = create_engine('sqlite:///germandates.db', echo=False)
Base = declarative_base()



class Airdates(Base):
	__tablename__ = 'airdates'

	id = Column(Integer, primary_key=True)
	name = Column(String)
	firstaired = Column(String)
	tvdbid = Column(Integer)
	season = Column(Integer)
	episode = Column(Integer)

	def __init__(self, name, firstaired, tvdbid, season, episode):
		self.name = name
		self.firstaired = firstaired
		self.tvdbid = tvdbid
		self.season = season
		self.episode = episode

	def __repr__(self):
		return u"<Airdates('id:{0}, name:{1}, s{2}e{3}, aired:{4}>".format(self.tvdbid, self.name, self.season, self.episode, self.firstaired)

class Error(Base):
	__tablename__ = 'error'

	tvdbid = Column(Integer, ForeignKey("airdates.tvdbid"), primary_key=True)

	def __init__(self, tvdbid):
		self.tvdbid = tvdbid

	def __repr__(self):
		return u"<Error('tvdbid:{0}')>".format(self.tvdbid)


class Slugs(Base):
	__tablename__ = 'slugs'

	id = Column(Integer, primary_key=True)
	name = Column(String)
	serienjunkies = Column(String)
	fernsehserien = Column(String)


	def __init__(self, id, name, serienjunkies, fernsehserien):
		self.id = id
		self.name = name
		self.serienjunkies = serienjunkies
		self.fernsehserien = fernsehserien

	def __repr__(self):
		return u"<Slugs('id:{0}, name:{1}, fs:{2}, sj:{3}>".format(self.id, self.name, self.fernsehserien, self.serienjunkies)

class Version(Base):
	__tablename__ = 'version'

	id = Column(Integer, primary_key=True)
	nextupdate = Column(Integer)


	def __init__(self, id, nextupdate):
		self.id = id
		self.nextupdate = nextupdate

	def __repr__(self):
		return u"<Version('next_update:{0}>".format(self.nextupdate)


Base.metadata.create_all(engine)
Session = sessionmaker()
Session.configure(bind=engine)
session = scoped_session(Session)

def requestSlug(tvdbid=None, showname=None):
	if tvdbid:
		url = "http://tvdb.cytec.us/request.php"
		data = { "tvdbid": tvdbid, "name": showname }
		r = requests.post(url, data)
		if r.status_code == 200:
			logger.log(u"Requestet german airdates for Show ID: {0} ".format(tvdbid), logger.MESSAGE)

def updateSlugs(tvdbid, showname):
	url = u"http://tvdb.cytec.us/getList.php"
	r = requests.get(url)
	logger.log(u"Updating german airdate slugs", logger.DEBUG)
	#check if slug is in result if not request it

	if not str(tvdbid) in r.text:
		requestSlug(tvdbid=tvdbid, showname=showname)

	for entry in r.json["result"]:
	 	ins = Slugs(
	 		id = entry["id"],
	 		name = entry["name"],
	 		fernsehserien = entry["fernsehserien"],
	 		serienjunkies = entry["serienjunkies"]
	 		)
	 	session.merge(ins)
	 	is_in_error = session.query(Error).filter(Error.tvdbid == entry["id"]).first()
	 	if is_in_error:
	 		session.delete(is_in_error)
	session.commit()
	logger.log(u"german airdate slug update finished", logger.DEBUG)
	 		

def updateEpisode(serieselement):
	entry = (
		session.query(Airdates)
			.filter(Airdates.tvdbid == serieselement["tvdbid"])
			.filter(Airdates.season == serieselement["season"])
			.filter(Airdates.episode == serieselement["episode"])
			.first()
		)
	ins = Airdates(
		name = serieselement["name"],
		firstaired = serieselement["firstaired"],
		tvdbid = serieselement["tvdbid"],
		season = serieselement["season"],
		episode = serieselement["episode"]
	)
	if not entry:
		logger.log(u"Entry for {0} not in my Database... CREATE it".format(serieselement), logger.DEBUG)
		session.merge(ins)
		session.commit()
	elif entry and not entry.firstaired:
		logger.log(u"Entry for {0} without a Airdate... UPDATE it".format(serieselement), logger.DEBUG)
		session.merge(ins)
		session.commit()
	else:
		logger.log(u"Entry {0} is in my Database".format(serieselement), logger.DEBUG)


def noSlug(tvdbid, showname):
	is_in_error = session.query(Error).filter(Error.tvdbid == tvdbid).first()
	if not is_in_error:
		logger.log(u"Sorry i cant find any slugs for {0}, go to http://tvdb.cytec.us to request more shows".format(tvdbid), logger.ERROR)
		session.merge(Error(tvdbid=tvdbid))
		session.commit()
		updateSlugs(tvdbid, showname)
		

def fsGetDates(tvdbid, showname, test=False):
	my_request = session.query(Slugs).filter(Slugs.id == tvdbid).first()
	if not my_request:
		noSlug(tvdbid, showname)
	
	if my_request and my_request.fernsehserien:
		url = u"http://www.fernsehserien.de/{0}/episodenguide".format(my_request.fernsehserien)
		r = requests.get(url)
		logger.log(u"URL for {0} is {1}".format(tvdbid, url), logger.DEBUG)
		if r.status_code == 200:
			try:
				soup = BeautifulSoup(r.text)
				eplist = soup.find_all("tr", {"class": "ep-hover"})
				try:
					for row in eplist:
					#info = row.find_all("td")
						#rawseason = row.find("td", {"class":"episodenliste-episodennummer"})["data-href"]
						#regex = ".*guide\/.*?(\d{1,3})/.*"
						#season = re.match(regex, rawseason).group(1)
						season = row.find_all("td", {"class":"episodenliste-episodennummer"})[1].text.replace(".","")
						#episode = row.find("td", {"class":"episodenliste-episodennummer"}).text
						episode = row.find_all("td", {"class":"episodenliste-episodennummer"})[2].text
						name = row.find("td", {"class":"episodenliste-titel"}).text
						date = row.find("td", {"class":"episodenliste-ea"}).text
						if date == u"":
							date = None
						serieselement = { "tvdbid": tvdbid, "name": name, "firstaired": date, "episode": episode, "season": season }
						if test:
							print serieselement
						else:
							updateEpisode(serieselement)
				except:
					logger.log(u"Unable to parse rows from: {0}".format(url), logger.WARNING)
			except:
				logger.log(u"Seems there was an error with the HTML file from url: {0}".format(url), logger.WARNING)
		else:
			logger.log(u"URL {0} doesnt return 200...".format(url), logger.WARNING)

def sjGetDates(tvdbid, showname, test=False):
	my_request = session.query(Slugs).filter(Slugs.id == tvdbid).first()
	if not my_request:
		noSlug(tvdbid, showname)
	
	if my_request and my_request.serienjunkies:
		url = u"http://www.serienjunkies.de/{0}/alle-serien-staffeln.html".format(my_request.serienjunkies)
		r = requests.get(url)
		logger.log(u"URL for {0} is {1}".format(tvdbid, url), logger.DEBUG)
		if r.status_code == 200:
			soup = BeautifulSoup(r.text)
			eplist = soup.find("table", {"class": "eplist"})
			for row in eplist:
				info = row.find_all("td", {"class": re.compile("^e")})
				if info and len(info) >= 5:
					season, episode = info[0].text.split("x")
					name = info[3].text
					date = info[4].text
					serieselement = { "tvdbid": tvdbid, "name": name, "firstaired": date, "episode": episode, "season": season }
					if test:
						print serieselement
					else:
						updateEpisode(serieselement)
				else:
					logger.log(u"Something went wrong... unable to parse: {0}".format(row), logger.WARNING)

		else:
			logger.log(u"Seems there was an error with the url {0}".format(url), logger.WARNING)
	
def updateAirDates(tvdbid, showname):
	now = datetime.now()
	t = timedelta(minutes=60)
	next = now + t
	result = session.query(Version).first()
	ins = Version(
		id = 1,
		nextupdate=time.mktime(next.timetuple())
	)
	if not result:
		session.merge(ins)
		logger.log(u"Next AirDates update: {0}".format(next), logger.ERROR)
		updateSlugs(tvdbid, showname)
		fsGetDates(tvdbid, showname)
	# if result and result.nextupdate >= now.toordinal():
	# 	logger.log(u"Next AirDates update: {0}".format(date.fromordinal(result.nextupdate)), logger.ERROR)
	if result and result.nextupdate <= time.mktime(now.timetuple()):
		logger.log(u"Running AirDates update", logger.ERROR)
		session.merge(ins)
		updateSlugs(tvdbid, showname)
		fsGetDates(tvdbid, showname)
		#sjGetDates(tvdbid, showname)
	session.commit()


def getEpInfo(tvdbid, season, episode, showname):
	if season == 0:
		return "1.1.1".split(".")

	result = (
		session.query(Airdates)
			.filter(Airdates.tvdbid == tvdbid)
			.filter(Airdates.season == season)
			.filter(Airdates.episode == episode)
			.first()
		)

	if not result:
		updateAirDates(tvdbid, showname)
		#fsGetDates(tvdbid, showname)
		#sjGetDates(tvdbid, showname)

	elif not result.firstaired:
		updateAirDates(tvdbid, showname)
		session.remove()
		return None
	else:
		session.remove()
		return result.firstaired.split(".")
