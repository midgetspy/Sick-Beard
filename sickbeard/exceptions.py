# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickBeard.
#
# SickBeard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickBeard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with SickBeard.  If not, see <http://www.gnu.org/licenses/>.



class SickBeardException(Exception):
	"Generic SickBeard Exception - should never be thrown, only subclassed"

class ConfigErrorException(SickBeardException):
	"Error in the config file"

class LaterException(SickBeardException):
	"Something bad happened that I'll make a real exception for later"

class NoNFOException(SickBeardException):
	"No NFO was found!"

class FileNotFoundException(SickBeardException):
	"The specified file doesn't exist"

class MultipleDBEpisodesException(SickBeardException):
	"Found multiple episodes in the DB! Must fix DB first"

class MultipleDBShowsException(SickBeardException):
	"Found multiple shows in the DB! Must fix DB first"

class MultipleShowObjectsException(SickBeardException):
	"Found multiple objects for the same show! Something is very wrong"

class WrongShowException(SickBeardException):
	"The episode doesn't belong to the same show as its parent folder"

class ShowNotFoundException(SickBeardException):
	"The show wasn't found on theTVDB"
	
class EpisodeNotFoundException(SickBeardException):
	"The episode wasn't found on theTVDB"
	
class NewzbinAPIThrottled(SickBeardException):
	"Newzbin has throttled us, deal with it"

class TVRageException(SickBeardException):
	"TVRage API did something bad"
