import sys, os.path
# Root path
base_path = os.path.dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.append(os.path.join(base_path, 'lib'))

from sqlalchemy import *
import requests


engine = create_engine('sqlite:///sickbeard.db', echo=False)
metadata = MetaData(engine)

tv_shows = Table('tv_shows', metadata,
    Column('show_id', Integer, primary_key=True),
    Column('show_name', String),
    Column('tvdb_id', String),
    )

metadata.create_all(engine)

conn = engine.connect()

myshows = tv_shows.select().order_by(tv_shows.c.show_id.desc()).execute()

missingshows = u""

for show in myshows:
    r = requests.get("http://cytec.us/tvdb/exists.php?tvdbid={0}".format(show.tvdb_id))
    if r.text.strip() != "1":
        missingshows = missingshows + u"{0}\t{1}\n".format(show.tvdb_id, show.show_name)

if missingshows:
    print "\nFolgende deiner tvdb ids sind noch nicht in der Datenbank:\n"
    print missingshows
    f = open('missingshows.txt', 'w')
    f.write("Folgende deiner tvdb ids sind noch nicht in der Datenbank:\n\n")
    f.write(missingshows)
    f.write("\nBitte hilf mit, gehe auf http://cytec.us/tvdb/ und trage deine TV-Shows ein.\n")
    f.close()
    print "\nBitte hilf mit, gehe auf http://cytec.us/tvdb/ und trage deine TV-Shows ein.\n"


else:
    print "\nKeine fehlenden Serien gefunden, wenn du dennoch helfen willst, gehe auf http://cytec.us/tvdb/\n"
    f = open('missingshows.txt', 'w')
    f.write("Keine fehlenden Serien gefunden, wenn du dennoch helfen willst, gehe auf http://cytec.us/tvdb/")
    f.close()
