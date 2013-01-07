import sys, os.path
# Root path
base_path = os.path.dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.append(os.path.join(base_path, 'lib'))

from sqlalchemy import *
import requests
from sickbeard import germandates


tvdbid = sys.argv[1]

germandates.fsGetDates(tvdbid, test=True)
germandates.sjGetDates(tvdbid, test=True)


