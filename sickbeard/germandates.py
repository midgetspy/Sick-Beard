import re
from bs4 import BeautifulSoup

import requests
from sqlalchemy import *
from sickbeard import logger
from datetime import date, timedelta

##define a database and add stuff to it
#TODO: Rewrite with mappers!

engine = create_engine('sqlite:///germandates.db', echo=False)
metadata = MetaData(engine)

airdates = Table('airdates', metadata,
	Column('id', Integer, primary_key=True),
	Column('name', String),
	Column('firstaired', String),
	Column('tvdbid', Integer),
	Column('season', Integer),
	Column('episode', Integer),
	)

error = Table('error', metadata,
	Column('tvdbid', Integer, ForeignKey('airdates.tvdbid'))
	)

slugs = Table('slugs', metadata,
	Column('id', Integer, primary_key=True, unique=True),
	Column('name', String),
	Column('serienjunkies', String),
	Column('fernsehserien', String),
	)

version = Table('version', metadata,
	Column('id', Integer, primary_key=True),
	Column('nextupdate', Integer),
	)

metadata.create_all(engine)

conn = engine.connect()



def updateSlugs():
	url = "http://cytec.us/tvdb/getList.php"
	r = requests.get(url)
	logger.log(u"Updating german airdate slugs", logger.DEBUG)
	for entry in r.json["result"]:
	 	if not slugs.select(slugs.c.id == entry["id"]).execute().fetchone():
	 		slugs.insert().execute(entry)
	 	if error.select(error.c.tvdbid == entry["id"]).execute().fetchone():
	 		conn.execute(error.delete().where(error.c.tvdbid == entry["id"]))


def updateEpisode(serieselement):
	entry = airdates.select(and_(
		airdates.c.tvdbid == serieselement["tvdbid"], 
		airdates.c.season == serieselement["season"], 
		airdates.c.episode == serieselement["episode"]
		)).execute().fetchone()

	if not entry:
		logger.log(u"Entry for {0} not in my Database... CREATE it".format(serieselement), logger.DEBUG)
		airdates.insert(serieselement).execute()
	elif entry and not entry.firstaired:
		logger.log(u"Entry for {0} without a Airdate... UPDATE it".format(serieselement), logger.DEBUG)
		airdates.update().where(and_(airdates.c.season == serieselement["season"], airdates.c.episode == serieselement["episode"],airdates.c.tvdbid == serieselement["tvdbid"])).values(serieselement).execute()
	else:
		logger.log(u"Entry {0} is in my Database".format(entry), logger.DEBUG)

def noSlug(tvdbid):
	inerror = error.select(error.c.tvdbid == tvdbid).execute().fetchone()
	if not inerror:
		logger.log(u"Sorry i cant find any slugs for {0}, go to cytec.us/tvdb to add more shows".format(tvdbid), logger.ERROR)
		updateSlugs()
		add_to_error = error.insert().values(tvdbid=tvdbid).execute()

def fsGetDates(tvdbid):
	myrequest = slugs.select(slugs.c.id == tvdbid).execute().fetchone()
	if not myrequest:
		noSlug(tvdbid)
	
	if myrequest.fernsehserien:
		url = "http://www.fernsehserien.de/{0}/episodenguide".format(myrequest.fernsehserien)
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
	myrequest = slugs.select(slugs.c.id == tvdbid).execute().fetchone()
	if not myrequest:
		noSlug(tvdbid)
	
	if myrequest.serienjunkies:
		url = "http://www.serienjunkies.de/{0}/alle-serien-staffeln.html".format(myrequest.serienjunkies)
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
	result = version.select().execute().fetchone()
	if not result:
		ins = {"id":1, "nextupdate":next.toordinal()}
		version.insert(ins).execute()
		logger.log(u"Next AirDates update: {0}".format(next), logger.ERROR)
	if result and result.nextupdate >= now.toordinal():
		logger.log(u"Next AirDates update: {0}".format(date.fromordinal(result.nextupdate)), logger.ERROR)
	if result and result.nextupdate <= now.toordinal():
		logger.log(u"Running AirDates update", logger.ERROR)
		version.update().where(version.c.id == 1).values(nextupdate=next.toordinal()).execute()
		updateSlugs()
		fsGetDates(tvdbid)
		sjGetDates(tvdbid)


def getEpInfo(tvdbid, season, episode):

	if season == 0:
		return "1.1.1".split(".")

	result = airdates.select(and_(
		airdates.c.tvdbid == tvdbid, 
		airdates.c.season == season, 
		airdates.c.episode == episode
		)).execute().fetchone()
	if not result:
		updateSlugs()
		fsGetDates(tvdbid)
		sjGetDates(tvdbid)

	elif not result.firstaired:
		return "1.1.1".split(".")
		updateAirDates(tvdbid)
	else:
		return result.firstaired.split(".")
