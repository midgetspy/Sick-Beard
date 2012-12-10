import re
from bs4 import BeautifulSoup

import requests
from sqlalchemy import create_engine, MetaData, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sickbeard import logger
from datetime import date, timedelta

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


def updateSlugs():
	url = "http://cytec.us/tvdb/getList.php"
	r = requests.get(url)
	logger.log(u"Updating german airdate slugs", logger.DEBUG)
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
		logger.log(u"Entry {0} is in my Database".format(entry), logger.DEBUG)


def noSlug(tvdbid):
	is_in_error = session.query(Error).filter(Error.tvdbid == tvdbid).first()
	if not is_in_error:
		logger.log(u"Sorry i cant find any slugs for {0}, go to cytec.us/tvdb to add more shows".format(tvdbid), logger.ERROR)
		updateSlugs()
		session.merge(Error(tvdbid=tvdbid))
		session.commit()

def fsGetDates(tvdbid):
	my_request = session.query(Slugs).filter(Slugs.id == tvdbid).first()
	if not my_request:
		noSlug(tvdbid)
	
	if my_request.fernsehserien:
		url = "http://www.fernsehserien.de/{0}/episodenguide".format(my_request.fernsehserien)
		r = requests.get(url)
		if r.status_code == 200:
			soup = BeautifulSoup(r.text)
			eplist = soup.find_all("tr", {"class": "ep-hover"})
			for row in eplist:
				info = row.find_all("td")
				if info:
					rawseason = info[1]["data-href"]
					regex = ".*guide\/.*?(\d{1,3})/.*"
					season = re.match(regex, rawseason).group(1)
					episode = info[1].text
					name = info[3].text
					date = info[4].text
					serieselement = { "tvdbid": tvdbid, "name": name, "firstaired": date, "episode": episode, "season": season }
					updateEpisode(serieselement)
				else:
					logger.log(u"Something went wrong... unable to parse: {0}".format(row), logger.DEBUG)
		else:
			logger.log(u"Seems there was an error with the url {0}".format(url), logger.WARNING)

def sjGetDates(tvdbid):
	my_request = session.query(Slugs).filter(Slugs.id == tvdbid).first()
	if not my_request:
		noSlug(tvdbid)
	
	if my_request.serienjunkies:
		url = "http://www.serienjunkies.de/{0}/alle-serien-staffeln.html".format(my_request.serienjunkies)
		r = requests.get(url)
		if r.status_code == 200:
			soup = BeautifulSoup(r.text)
			eplist = soup.find("table", {"class": "eplist"})
			try:
				for row in eplist:
					info = row.find_all("td", {"class": re.compile("^e")})
					if info:
						season, episode = info[0].text.split("x")
						name = info[3].text
						date = info[4].text
						serieselement = { "tvdbid": tvdbid, "name": name, "firstaired": date, "episode": episode, "season": season }
						updateEpisode(serieselement)
					else:
						logger.log(u"Something went wrong... unable to parse: {0}".format(row), logger.WARNING)
			except:
				logger.log(u"Unable to parse Serienjunkies informations for {0}".format(tvdbid), logger.ERROR)
		else:
			logger.log(u"Seems there was an error with the url {0}".format(url), logger.WARNING)
	
def updateAirDates(tvdbid):
	now = date.today()
	t = timedelta(14)
	next = now + t
	result = session.query(Version).first()
	ins = Version(
		id = 1,
		nextupdate=next.toordinal()
	)
	if not result:
		session.merge(ins)
		logger.log(u"Next AirDates update: {0}".format(next), logger.ERROR)
	if result and result.nextupdate >= now.toordinal():
		logger.log(u"Next AirDates update: {0}".format(date.fromordinal(result.nextupdate)), logger.ERROR)
	if result and result.nextupdate <= now.toordinal():
		logger.log(u"Running AirDates update", logger.ERROR)
		session.merge(ins)
		updateSlugs()
		fsGetDates(tvdbid)
		sjGetDates(tvdbid)
	session.commit()


def getEpInfo(tvdbid, season, episode):

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
		updateSlugs()
		fsGetDates(tvdbid)
		sjGetDates(tvdbid)

	elif not result.firstaired:
		return None
		updateAirDates(tvdbid)
	else:
		return result.firstaired.split(".")
