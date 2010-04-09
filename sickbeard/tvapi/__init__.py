import Queue

from storm.locals import create_database, Store

from lib.tvdb_api import tvdb_api

storeQueue = Queue.Queue()
database = create_database("sqlite:stormtest.db")

def getStore():

    store = Store(database)
    
    # block on the put, then get as soon as we can
    storeQueue.put(store, True)
    return storeQueue.get()
    
def releaseStore():
    
    storeQueue.task_done()    


###################################################################################
## Everythnig below this is temporary until I make a permanent database and put the
## table structures into the main databases/ package. For now they're changing too
## often to bother.

# set it to false if you want to persist data from the last time for testing
if False:

    store = Store(database)
    
    for table in ("tvepisodedata", "tvshowdata", "tvepisode", "tvshow", "episodedatarel"):
        try:
            store.execute("DROP TABLE "+table)
        except Exception:
            pass
    
    store.execute("CREATE TABLE tvepisodedata ( \
                  edid INTEGER PRIMARY KEY, \
                  show_id NUMERIC, \
                  season NUMERIC, \
                  episode NUMERIC, \
                  name TEXT, \
                  description TEXT, \
                  aired TEXT, \
                  director TEXT, \
                  writer TEXT, \
                  rating NUMERIC, \
                  gueststars BLOB, \
                  thumb TEXT, \
                  displayseason NUMERIC, \
                  displayepisode NUMERIC, \
                  tvdb_id NUMERIC, \
                  imdb_id NUMERIC, \
                  _eid NUMERIC \
                  )")
    
    
    store.execute("CREATE TABLE tvshowdata ( \
                  name TEXT, \
                  plot TEXT, \
                  genres BLOB, \
                  network TEXT, \
                  duration NUMERIC, \
                  actors BLOB, \
                  firstaired TEXT, \
                  status TEXT, \
                  classification TEXT, \
                  country TEXT, \
                  rating NUMERIC, \
                  contentrating TEXT, \
                  tvdb_id INTEGER PRIMARY KEY, \
                  tvrage_id NUMERIC, \
                  tvrage_name TEXT, \
                  imdb_id NUMERIC \
                  )")
    
    store.execute("CREATE TABLE tvshow ( \
                  tvdb_id INTEGER PRIMARY KEY, \
                  _location TEXT, \
                  seasonfolders TEXT, \
                  paused NUMERIC, \
                  quality NUMERIC \
                  )")
    
    store.execute("CREATE TABLE tvepisode ( \
                  eid INTEGER PRIMARY KEY, \
                  location TEXT, \
                  _status NUMERIC, \
                  hasnfo NUMERIC, \
                  hastbn NUMERIC, \
                  _show_id NUMERIC \
                  )")
    
    store.execute("CREATE TABLE episodedatarel ( \
                  eid NUMERIC, \
                  show_id NUMERIC, \
                  season NUMERIC, \
                  episode NUMERIC, \
                  PRIMARY KEY (eid, show_id, season, episode) \
                  )")

    store.commit()
