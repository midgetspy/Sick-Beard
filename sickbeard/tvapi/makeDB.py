import sickbeard
###################################################################################
## Everythnig below this is temporary until I make a permanent database and put the
## table structures into the main databases/ package. For now they're changing too
## often to bother.

# set it to false if you want to persist data from the last time for testing

def makeDB():

    sickbeard.storeManager.safe_store("execute", "CREATE TABLE tvepisodedata ( \
                  tvdb_show_id NUMERIC, \
                  tvrage_show_id NUMERIC, \
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
                  _eid NUMERIC \
                  )")
    
    sickbeard.storeManager.safe_store("execute", "CREATE TABLE tvepisodedata_tvdb ( \
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
                  tvdb_id NUMERIC \
                  )")
    
    sickbeard.storeManager.safe_store("execute", "CREATE TABLE tvepisodedata_tvrage ( \
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
                  tvrage_id NUMERIC \
                  )")
    
    
    sickbeard.storeManager.safe_store("execute", "CREATE TABLE tvshowdata ( \
                  tvdb_id INTEGER PRIMARY KEY, \
                  tvrage_id NUMERIC, \
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
                  imdb_id NUMERIC \
                  )")
    
    sickbeard.storeManager.safe_store("execute", "CREATE TABLE tvshowdata_tvdb ( \
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
                  tvdb_id INTEGER PRIMARY KEY \
                  )")
    
    sickbeard.storeManager.safe_store("execute", "CREATE TABLE tvshowdata_tvrage ( \
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
                  tvrage_id NUMERIC \
                  )")
    
    sickbeard.storeManager.safe_store("execute", "CREATE TABLE tvshow ( \
                  tvdb_id INTEGER PRIMARY KEY, \
                  _location TEXT, \
                  seasonfolders TEXT, \
                  paused NUMERIC, \
                  quality NUMERIC \
                  )")
    
    sickbeard.storeManager.safe_store("execute", "CREATE TABLE tvepisode ( \
                  eid INTEGER PRIMARY KEY, \
                  location TEXT, \
                  _status NUMERIC, \
                  hasnfo NUMERIC, \
                  hastbn NUMERIC, \
                  _show_id NUMERIC \
                  )")
