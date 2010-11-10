# Author: Nic Wolfe <nic@wolfeden.ca>
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

import sickbeard
from sickbeard import helpers, version
from sickbeard import logger

import os, os.path
import subprocess, re, datetime
import urllib, urllib2
import zipfile, tarfile

from urllib2 import URLError
from lib.pygithub import github

class CheckVersion():

    def __init__(self):
        self.install_type = self.find_install_type()

        if self.install_type == 'win':
            self.updater = WindowsUpdateManager()
        elif self.install_type == 'git':
            self.updater = GitUpdateManager()
        elif self.install_type == 'source':
            self.updater = SourceUpdateManager()
        else:
            self.updater = None

    def run(self):
        self.check_for_new_version()

    def find_install_type(self):

        # check if we're a windows build
        if version.SICKBEARD_VERSION.startswith('build '):
            install_type = 'win'
        elif os.path.isdir(os.path.join(sickbeard.PROG_DIR, '.git')):
            install_type = 'git'
        else:
            install_type = 'source'

        return install_type

    def check_for_new_version(self):

        if not sickbeard.VERSION_NOTIFY:
            logger.log(u"Version checking is disabled, not checking for the newest version")
            return

        logger.log(u"Checking if "+self.install_type+" needs an update")
        if not self.updater.need_update():
            logger.log(u"No update needed")
            return

        self.updater.set_newest_text()

    def update(self):

        if self.updater.need_update():
            return self.updater.update()

class UpdateManager():
    def get_update_url(self):
        return sickbeard.WEB_ROOT+"/home/update/?pid="+str(os.getpid())

class WindowsUpdateManager(UpdateManager):

    def __init__(self):
        self._cur_version = None
        self._newest_version = None

        self.gc_url = 'http://code.google.com/p/sickbeard/downloads/list'

    def _find_installed_version(self):
        return int(sickbeard.version.SICKBEARD_VERSION[6:])

    def _find_newest_version(self, whole_link=False):
        """
        Checks google code for the newest Windows binary build. Returns either the
        build number or the entire build URL depending on whole_link's value.

        whole_link: If True, returns the entire URL to the release. If False, it returns
                    only the build number. default: False
        """

        regex = "http://sickbeard.googlecode.com/files/SickBeard\-win32\-alpha\-build(\d+)(?:\.\d+)?\.zip"

        svnFile = urllib.urlopen(self.gc_url)

        for curLine in svnFile.readlines():
            match = re.search(regex, curLine)
            if match:
                if whole_link:
                    return match.group(0)
                else:
                    return int(match.group(1))

        return None

    def need_update(self):
        self._cur_version = self._find_installed_version()
        self._newest_version = self._find_newest_version()

        if self._newest_version > self._cur_version:
            return True

    def set_newest_text(self):
        new_str = 'There is a <a href="'+self.gc_url+'" target="_new">newer version available</a> (build '+str(self._newest_version)+')'
        new_str += " <a href=\""+self.get_update_url()+"\">Update Now</a>"
        sickbeard.NEWEST_VERSION_STRING = new_str

    def update(self):

        new_link = self._find_newest_version(True)

        if not new_link:
            logger.log(u"Unable to find a new version link on google code, not updating")
            return False

        # download the zip
        try:
            logger.log(u"Downloading update file from "+str(new_link))
            (filename, headers) = urllib.urlretrieve(new_link)

            # unzip it to sb-update
            sb_update_dir = os.path.join(sickbeard.PROG_DIR, 'sb-update')
            logger.log(u"Unzipping from "+str(filename)+" to "+sb_update_dir)
            update_zip = zipfile.ZipFile(filename, 'r')
            update_zip.extractall(sb_update_dir)
            update_zip.close()

        except Exception, e:
            logger.log(u"Error while trying to update: "+str(e).decode('utf-8'), logger.ERROR)
            return False

        # delete the zip
        logger.log(u"Deleting old update file from "+str(filename))
        os.remove(filename)

        return True

class GitUpdateManager(UpdateManager):

    def __init__(self):
        self._cur_commit_hash = None
        self._newest_commit_hash = None
        self._num_commits_behind = 0

        self.git_url = 'http://code.google.com/p/sickbeard/downloads/list'

    def _git_error(self):
        error_message = 'Unable to find your git executable - either delete your .git folder and run from source OR <a href="http://code.google.com/p/sickbeard/wiki/AdvancedSettings" target="_new">set git_path in your config.ini</a> to enable updates.'
        sickbeard.NEWEST_VERSION_STRING = error_message
        
        return None

    def _find_installed_version(self):
        """
        Attempts to find the currently installed version of Sick Beard.

        Uses git show to get commit version.

        Returns: a tuple containing the commit hash and a datetime object of the commit date.
                 Both will be None if we can't retrieve them.
        """

        output = None
        
        if sickbeard.GIT_PATH:
            git = '"'+sickbeard.GIT_PATH+'"'
        else:
            git = 'git'

        cmd = git+' rev-parse HEAD'

        try:
            logger.log(u"Executing "+cmd+"with your shell in "+sickbeard.PROG_DIR, logger.DEBUG)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=sickbeard.PROG_DIR)
            output, err = p.communicate()
        except OSError, e:
            logger.log(u"Unable to find git, can't tell what version you're running")
            return self._git_error()


        if 'not found' in output or "not recognized as an internal or external command" in output:
            logger.log(u"Unable to find git, can't tell what version you're running. Maybe specify the path to git in git_path in your config.ini?")
            return self._git_error()

        if 'fatal:' in output or err:
            logger.log(u"Git returned bad info, are you sure this is a git installation?", logger.ERROR)
            return self._git_error()

        logger.log(u"Git output: "+str(output), logger.DEBUG)
        cur_commit_hash = output.strip()

        if not re.match('^[a-z0-9]+$', cur_commit_hash):
            logger.log(u"Output doesn't look like a hash, not using it", logger.ERROR)
            return self._git_error()
            
        return True


    def _check_github_for_update(self):
        """
        Uses pygithub to ask github if there is a newer version that the provided
        commit hash. If there is a newer version it sets Sick Beard's version text.

        commit_hash: hash that we're checking against
        """

        self._num_commits_behind = 0
        self._newest_commit_hash = None

        gh = github.GitHub()

        # find newest commit
        for curCommit in gh.commits.forBranch('midgetspy', 'Sick-Beard', version.SICKBEARD_VERSION):
            if not self._newest_commit_hash:
                self._newest_commit_hash = curCommit.id
                if not self._cur_commit_hash:
                    break

            if curCommit.id == self._cur_commit_hash:
                break

            self._num_commits_behind += 1

        logger.log(u"newest: "+str(self._newest_commit_hash)+" and current: "+str(self._cur_commit_hash)+" and num_commits: "+str(self._num_commits_behind), logger.DEBUG)

    def set_newest_text(self):

        # if we're up to date then don't set this
        if self._num_commits_behind == 35:
            message = "or else you're ahead of master"

        elif self._num_commits_behind > 0:
            message = "you're "+str(self._num_commits_behind)+' commits behind'

        else:
            return

        if self._newest_commit_hash:
            url = 'http://github.com/midgetspy/Sick-Beard/compare/'+self._cur_commit_hash+'...'+self._newest_commit_hash
        else:
            url = 'http://github.com/midgetspy/Sick-Beard/commits/'

        new_str = 'There is a <a href="'+url+'" target="_new">newer version available</a> ('+message+')'
        new_str += " <a href=\""+self.get_update_url()+"\">Update Now</a>"

        sickbeard.NEWEST_VERSION_STRING = new_str

    def need_update(self):
        self._find_installed_version()
        self._check_github_for_update()

        logger.log(u"After checking, cur_commit = "+str(self._cur_commit_hash)+", newest_commit = "+str(self._newest_commit_hash)+", num_commits_behind = "+str(self._num_commits_behind), logger.DEBUG)

        if self._num_commits_behind > 0:
            return True

        return False

    def update(self):
        """
        Calls git pull origin <branch> in order to update Sick Beard. Returns a bool depending
        on the call's success.
        """

        output = None

        if sickbeard.GIT_PATH:
            git = '"'+sickbeard.GIT_PATH+'"'
        else:
            git = 'git'

        try:
            popen_str = git+' pull origin '+sickbeard.version.SICKBEARD_VERSION
            logger.log(u"Executing command: "+popen_str+" with your shell in "+sickbeard.PROG_DIR, logger.DEBUG)
            p = subprocess.Popen(popen_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=sickbeard.PROG_DIR)
            output, err = p.communicate()
        except OSError, e:
            logger.log(u'Error calling git pull: '+str(e).decode('utf-8'), logger.ERROR)
            return False

        pull_regex = '(\d+) files? changed, (\d+) insertions?\(\+\), (\d+) deletions?\(\-\)'

        (files, insertions, deletions) = (None, None, None)

        for line in output.split('\n'):

            if 'Already up-to-date.' in line:
                logger.log(u"No update available, not updating")
                logger.log(u"Output: "+str(output))
                return False
            elif line.endswith('Aborting.'):
                logger.log(u"Unable to update from git: "+line, logger.ERROR)
                logger.log(u"Output: "+str(output))
                return False

            match = re.search(pull_regex, line)
            if match:
                (files, insertions, deletions) = match.groups()
                break

        if None in (files, insertions, deletions):
            logger.log(u"Didn't find indication of success in output, assuming git pull failed", logger.ERROR)
            logger.log(u"Output: "+str(output))
            return False

        return True



class SourceUpdateManager(GitUpdateManager):

    def _find_installed_version(self):

        version_file = os.path.join(sickbeard.PROG_DIR, 'version.txt')

        if not os.path.isfile(version_file):
            self._cur_commit_hash = None
            return

        fp = open(version_file, 'r')
        self._cur_commit_hash = fp.read().strip(' \n\r')
        fp.close()

        if not self._cur_commit_hash:
            self._cur_commit_hash = None

    def need_update(self):

        parent_result = GitUpdateManager.need_update(self)

        if not self._cur_commit_hash:
            return True
        else:
            return parent_result


    def set_newest_text(self):
        if not self._cur_commit_hash:
            logger.log(u"Unknown current version, don't know if we should update or not", logger.DEBUG)

            new_str = "Unknown version: If you've never used the Sick Beard upgrade system then I don't know what version you have."
            new_str += " <a href=\""+self.get_update_url()+"\">Update Now</a>"

            sickbeard.NEWEST_VERSION_STRING = new_str

        else:
            GitUpdateManager.set_newest_text(self)

    def update(self):
        """
        Downloads the latest source tarball from github and installs it over the existing version.
        """

        tar_download_url = 'http://github.com/midgetspy/Sick-Beard/tarball/'+version.SICKBEARD_VERSION
        sb_update_dir = os.path.join(sickbeard.PROG_DIR, 'sb-update')
        version_path = os.path.join(sickbeard.PROG_DIR, 'version.txt')

        # retrieve file
        try:
            logger.log(u"Downloading update from "+tar_download_url)
            data = urllib2.urlopen(tar_download_url)
        except (IOError, URLError):
            logger.log(u"Unable to retrieve new version from "+tar_download_url+", can't update", logger.ERROR)
            return False

        download_name = data.geturl().split('/')[-1]

        tar_download_path = os.path.join(sickbeard.PROG_DIR, download_name)

        # save to disk
        f = open(tar_download_path, 'wb')
        f.write(data.read())
        f.close()

        # extract to temp folder
        logger.log(u"Extracting file "+tar_download_path)
        tar = tarfile.open(tar_download_path)
        tar.extractall(sb_update_dir)
        tar.close()

        # delete .tar.gz
        logger.log(u"Deleting file "+tar_download_path)
        os.remove(tar_download_path)

        # find update dir name
        update_dir_contents = [x for x in os.listdir(sb_update_dir) if os.path.isdir(os.path.join(sb_update_dir, x))]
        if len(update_dir_contents) != 1:
            logger.log(u"Invalid update data, update failed: "+str(update_dir_contents), logger.ERROR)
            return False
        content_dir = os.path.join(sb_update_dir, update_dir_contents[0])

        # walk temp folder and move files to main folder
        for dirname, dirnames, filenames in os.walk(content_dir):
            dirname = dirname[len(content_dir)+1:]
            for curfile in filenames:
                old_path = os.path.join(content_dir, dirname, curfile)
                new_path = os.path.join(sickbeard.PROG_DIR, dirname, curfile)

                if os.path.isfile(new_path):
                    os.remove(new_path)
                os.renames(old_path, new_path)

        # update version.txt with commit hash
        try:
            ver_file = open(version_path, 'w')
            ver_file.write(self._newest_commit_hash)
            ver_file.close()
        except IOError, e:
            logger.log(u"Unable to write version file, update not complete: "+str(e).decode('utf-8'), logger.ERROR)
            return False

        return True

