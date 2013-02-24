# Author: Rembrand van Lakwijk <rem@lakwijk.com>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import subprocess

import sickbeard

from sickbeard import logger
from sickbeard import common
from sickbeard.exceptions import ex
from sickbeard.encodingKludge import fixStupidEncodings



class CmdNotifier:

	def notify_snatch(self, ep_name):
		pass

	def notify_download(self, ep_name):
		pass

	def update_library(self, ep, cmd=None, test=False):
		if not sickbeard.CMDNOTIFY_I_KNOW_WHAT_I_AM_DOING:
			logger.log(u"Cmdnotify not enabled, I_KNOW_WHAT_I_AM_DOING is False, skipping", logger.DEBUG)
			return False
		if not sickbeard.USE_CMDNOTIFY and not test:
			logger.log(u"Cmdnotify not enabled, skipping", logger.DEBUG)
			return False
		if not sickbeard.CMDNOTIFY_UPDATE_CMD and not test:
			logger.log(u"Cmdnotify command empty, skipping", logger.DEBUG)
			return False
		if not ep and not test:
			logger.log(u"Cmdnotify received update request for complete library, skipping", logger.DEBUG)
			return False
			

		cmd = str(cmd if cmd else sickbeard.CMDNOTIFY_UPDATE_CMD).strip()

		path = ep.fullPath() if not test else '/path/to/series/Some Show/Some.Ep.S01.E02.mkv'
		name = ep.prettyName() if not test else 'Some Show S01E02'

		eshow = ep.show.name if not test else 'Some Show'
		eseason = str(ep.season if not test else 1)
		eep = str(ep.episode if not test else 2)
		etitle = str(ep.name if not test else 'Some Ep')

		args = [cmd, path, name, eshow, eseason, eep, etitle]

		logger.log(u"Starting command notify hook: %s" % ' '.join(['"%s"' % s for s in args]))
		proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out = proc.communicate()
		status = proc.returncode
		if status != 0:
			logger.log(u"%s exited with non-zero status code %d" % (' '.join(['"%s"' % s for s in args]), status), logger.WARNING)
			logger.log(u"Stdout: \n%s\nStderr\n%s\n" % out, logger.WARNING)
			return False
		else:
			return True

	def test_notify(self, cmd):
		return self.update_library(None, cmd=cmd, test=True)



notifier = CmdNotifier
