from sickbeard.tvclasses import TVEpisode
from sickbeard.tvapi import store
from sickbeard.tvapi.tvapi import getTVShow
from sickbeard.tvapi.tvapi_classes import TVEpisodeData

# use case: parsing a random scene name, generating temp objects for it, and throwing them away
#           for example, when parsing the RSS names and finding an episode we already have
# we take The.Office.US.S01E02E03.Blah.avi and found:
#
# series name: The Office US
# season: 1
# episodes: (2,3)
#
# we then look up the tvdb id (internet or local DB) and determine that the show is one we want
# tvdb_id: 73244

# the use case starts here
# use the tvdb id to make the show data
myShow = getTVShow(79488) # really I'd just look it up in sickbeard.showList

# in real life this line wouldn't be necessary since the metadata database would always have the latest required info
myShow.update()
store.add(myShow)
for x in myShow.data.seasons:
    print myShow.data[x]

print "1. %s (%r)" % (myShow.data.name, myShow.tvdb_id)

epObj = TVEpisode(myShow)

epObj.addEp(1,2)
print "2. %s" % ", ".join(["%dx%d - %s" % (x.season, x.episode, x.name) for x in epObj.episodes])
epObj.addEp(1,3)
print "3. %s" % ", ".join(["%dx%d - %s" % (x.season, x.episode, x.name) for x in epObj.episodes])
store.commit()
