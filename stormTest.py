from sickbeard.tvclasses import TVEpisode
from sickbeard.tvapi import store
from sickbeard.tvapi import tvapi
from sickbeard.tvapi.tvapi_classes import TVEpisodeData

myShow = tvapi.createTVShow(73244) # simulates adding a new show
store.commit()

for x in myShow.show_data.seasons:
    print myShow.show_data[x]

print "1. %s (%r)" % (myShow.show_data.name, myShow.tvdb_id)

epObj = myShow.getEp(1, 4)
print "2. %s" % ", ".join(["%dx%d - %s" % (x.season, x.episode, x.name) for x in epObj.episodes_data])

epObj = myShow.getEp(1, 2)
print "3. %s" % ", ".join(["%dx%d - %s" % (x.season, x.episode, x.name) for x in epObj.episodes_data])
epObj.addEp(1,3)
print "4. %s" % ", ".join(["%dx%d - %s" % (x.season, x.episode, x.name) for x in epObj.episodes_data])
store.commit()

for x in myShow.nextEpisodes():
    print x.season, x.episode, x.aired

print "5. status: 22 ==", epObj.status
epObj.status = 55
print "6. status: 55 ==", epObj.status

epObj = myShow.getEp(6, 21)
print "8. status: 11 ==", epObj.status
epObj.status = 66
print "9. status: 66 ==", epObj.status
store.commit()