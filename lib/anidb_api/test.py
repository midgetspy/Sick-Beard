
from aniDBAbstracter import Episode as aniDBEpisode
from anidb import AniDBInterface

filePath = "/Users/lad1337/Azureus/sabnzbd/tv/one/going after the big tressure first episode.avi"

anidb = AniDBInterface()

anidb.auth('lad1337', 'anidb.t0gepi175')
ep = aniDBEpisode(anidb,filePath=filePath,
     paramsF=["quality","anidb_file_name","crc32"],
     paramsA=["epno","english_name","other_name"])


ep.loadData()
try:
    print "Trying to lookup "+str(filePath)+" on anidb"
    #ep.loadData()
except Exception,e :
    print "exception msg: "+str(e)
    

if ep.anidb_file_name:
    print "Lookup successful, using anidb filename "+str(ep.anidb_file_name)
    