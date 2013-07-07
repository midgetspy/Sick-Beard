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
from sickbeard import helpers
from sickbeard import version, ui
from sickbeard import logger
from sickbeard import scene_exceptions
from sickbeard.exceptions import ex
from sickbeard import encodingKludge as ek

import os
import platform
import shutil
import subprocess
import re

import urllib

import zipfile
import tarfile

import gh_api as github


class CheckVersion():
    """
    Version check class meant to run as a thread object with the SB scheduler.
    """

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

        # refresh scene exceptions too
        scene_exceptions.retrieve_exceptions()

    def find_install_type(self):
        """
        Determines how this copy of SB was installed.

        returns: type of installation. Possible values are:
            'win': any compiled windows build
            'git': running from source using git
            'source': running from source without git
        """

        # check if we're a windows build
        if sickbeard.version.SICKBEARD_VERSION.startswith('build '):
            install_type = 'win'
        elif os.path.isdir(ek.ek(os.path.join, sickbeard.PROG_DIR, u'.git')):
            install_type = 'git'
        else:
            install_type = 'source'

        return install_type

    def check_for_new_version(self, force=False):
        """
        Checks the internet for a newer version.

        returns: bool, True for new version or False for no new version.

        force: if true the VERSION_NOTIFY setting will be ignored and a check will be forced
        """

        if not sickbeard.VERSION_NOTIFY and not force:
            logger.log(u"Version checking is disabled, not checking for the newest version")
            return False

        logger.log(u"Checking if " + self.install_type + " needs an update")
        if not self.updater.need_update():
            sickbeard.NEWEST_VERSION_STRING = None
            logger.log(u"No update needed")

            if force:
                ui.notifications.message('No update needed')
            return False

        self.updater.set_newest_text()
        return True

    def update(self):
        if self.updater.need_update():
            return self.updater.update()


class UpdateManager():

    def get_github_repo_user(self):
        return 'midgetspy'

    def get_github_repo(self):
        return 'Sick-Beard'

    def get_update_url(self):
        return sickbeard.WEB_ROOT + "/home/update/?pid=" + str(sickbeard.PID)


class WindowsUpdateManager(UpdateManager):

    def __init__(self):
        self.github_repo_user = self.get_github_repo_user()
        self.github_repo = self.get_github_repo()
        self.branch = 'windows_binaries'

        self._cur_version = None
        self._cur_commit_hash = None
        self._newest_version = None

        self.gc_url = 'http://code.google.com/p/sickbeard/downloads/list'
        self.version_url = 'https://raw.github.com/' + self.github_repo_user + '/' + self.github_repo + '/' + self.branch + '/updates.txt'

    def _find_installed_version(self):
        try:
            version = sickbeard.version.SICKBEARD_VERSION
            return int(version[6:])
        except ValueError:
            logger.log(u"Unknown SickBeard Windows binary release: " + version, logger.ERROR)
            return None

    def _find_newest_version(self, whole_link=False):
        """
        Checks git for the newest Windows binary build. Returns either the
        build number or the entire build URL depending on whole_link's value.

        whole_link: If True, returns the entire URL to the release. If False, it returns
                    only the build number. default: False
        """

        regex = ".*SickBeard\-win32\-alpha\-build(\d+)(?:\.\d+)?\.zip"

        version_url_data = helpers.getURL(self.version_url)

        if version_url_data is None:
            return None
        else:
            for curLine in version_url_data.splitlines():
                logger.log(u"checking line " + curLine, logger.DEBUG)
                match = re.match(regex, curLine)
                if match:
                    logger.log(u"found a match", logger.DEBUG)
                    if whole_link:
                        return curLine.strip()
                    else:
                        return int(match.group(1))

        return None

    def need_update(self):
        self._cur_version = self._find_installed_version()
        self._newest_version = self._find_newest_version()

        logger.log(u"newest version: " + repr(self._newest_version), logger.DEBUG)

        if self._newest_version and self._newest_version > self._cur_version:
            return True

    def set_newest_text(self):

        sickbeard.NEWEST_VERSION_STRING = None

        if not self._cur_version:
            newest_text = "Unknown SickBeard Windows binary version. Not updating with original version."
        else:
            newest_text = 'There is a <a href="' + self.gc_url + '" onclick="window.open(this.href); return false;">newer version available</a> (build ' + str(self._newest_version) + ')'
            newest_text += "&mdash; <a href=\"" + self.get_update_url() + "\">Update Now</a>"

        sickbeard.NEWEST_VERSION_STRING = newest_text

    def update(self):

        zip_download_url = self._find_newest_version(True)
        logger.log(u"new_link: " + repr(zip_download_url), logger.DEBUG)

        if not zip_download_url:
            logger.log(u"Unable to find a new version link on google code, not updating")
            return False

        try:
            # prepare the update dir
            sb_update_dir = ek.ek(os.path.join, sickbeard.PROG_DIR, u'sb-update')

            if os.path.isdir(sb_update_dir):
                logger.log(u"Clearing out update folder " + sb_update_dir + " before extracting")
                shutil.rmtree(sb_update_dir)

            logger.log(u"Creating update folder " + sb_update_dir + " before extracting")
            os.makedirs(sb_update_dir)

            # retrieve file
            logger.log(u"Downloading update from " + zip_download_url)
            zip_download_path = os.path.join(sb_update_dir, u'sb-update.zip')
            urllib.urlretrieve(zip_download_url, zip_download_path)

            if not ek.ek(os.path.isfile, zip_download_path):
                logger.log(u"Unable to retrieve new version from " + zip_download_url + ", can't update", logger.ERROR)
                return False

            # extract to sb-update dir
            logger.log(u"Unzipping from " + str(zip_download_path) + " to " + sb_update_dir)
            update_zip = zipfile.ZipFile(zip_download_path, 'r')
            update_zip.extractall(sb_update_dir)
            update_zip.close()

            # delete the zip
            logger.log(u"Deleting zip file from " + str(zip_download_path))
            os.remove(zip_download_path)

            # find update dir name
            update_dir_contents = [x for x in os.listdir(sb_update_dir) if os.path.isdir(os.path.join(sb_update_dir, x))]

            if len(update_dir_contents) != 1:
                logger.log(u"Invalid update data, update failed. Maybe try deleting your sb-update folder?", logger.ERROR)
                return False

            content_dir = os.path.join(sb_update_dir, update_dir_contents[0])
            old_update_path = os.path.join(content_dir, u'updater.exe')
            new_update_path = os.path.join(sickbeard.PROG_DIR, u'updater.exe')
            logger.log(u"Copying new update.exe file from " + old_update_path + " to " + new_update_path)
            shutil.move(old_update_path, new_update_path)

        except Exception, e:
            logger.log(u"Error while trying to update: " + ex(e), logger.ERROR)
            return False

        return True


class GitUpdateManager(UpdateManager):

    def __init__(self):
        self._git_path = self._find_working_git()
        self.github_repo_user = self.get_github_repo_user()
        self.github_repo = self.get_github_repo()
        self.branch = self._find_git_branch()

        self._cur_commit_hash = None
        self._newest_commit_hash = None
        self._num_commits_behind = 0

    def _git_error(self):
        error_message = 'Unable to find your git executable - Shutdown SickBeard and EITHER <a href="http://code.google.com/p/sickbeard/wiki/AdvancedSettings" onclick="window.open(this.href); return false;">set git_path in your config.ini</a> OR delete your .git folder and run from source to enable updates.'
        sickbeard.NEWEST_VERSION_STRING = error_message

    def _find_working_git(self):
        test_cmd = 'version'

        if sickbeard.GIT_PATH:
            main_git = '"' + sickbeard.GIT_PATH + '"'
        else:
            main_git = 'git'

        logger.log(u"Checking if we can use git commands: " + main_git + ' ' + test_cmd, logger.DEBUG)
        output, err, exit_status = self._run_git(main_git, test_cmd)

        if exit_status == 0:
            logger.log(u"Using: " + main_git, logger.DEBUG)
            return main_git
        else:
            logger.log(u"Not using: " + main_git, logger.DEBUG)

        # trying alternatives

        alternative_git = []

        # osx people who start SB from launchd have a broken path, so try a hail-mary attempt for them
        if platform.system().lower() == 'darwin':
            alternative_git.append('/usr/local/git/bin/git')

        if platform.system().lower() == 'windows':
            if main_git != main_git.lower():
                alternative_git.append(main_git.lower())

        if alternative_git:
            logger.log(u"Trying known alternative git locations", logger.DEBUG)

            for cur_git in alternative_git:
                logger.log(u"Checking if we can use git commands: " + cur_git + ' ' + test_cmd, logger.DEBUG)
                output, err, exit_status = self._run_git(cur_git, test_cmd)

                if exit_status == 0:
                    logger.log(u"Using: " + cur_git, logger.DEBUG)
                    return cur_git
                else:
                    logger.log(u"Not using: " + cur_git, logger.DEBUG)

        # Still haven't found a working git
        error_message = 'Unable to find your git executable - Shutdown SickBeard and EITHER <a href="http://code.google.com/p/sickbeard/wiki/AdvancedSettings" onclick="window.open(this.href); return false;">set git_path in your config.ini</a> OR delete your .git folder and run from source to enable updates.'
        sickbeard.NEWEST_VERSION_STRING = error_message

        return None

    def _run_git(self, git_path, args):

        output = err = exit_status = None

        if not git_path:
            logger.log(u"No git specified, can't use git commands", logger.ERROR)
            exit_status = 1
            return (output, err, exit_status)

        cmd = git_path + ' ' + args

        try:
            logger.log(u"Executing " + cmd + " with your shell in " + sickbeard.PROG_DIR, logger.DEBUG)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=sickbeard.PROG_DIR)
            output, err = p.communicate()
            exit_status = p.returncode

            if output:
                output = output.strip()
            logger.log(u"git output: " + output, logger.DEBUG)

        except OSError:
            logger.log(u"Command " + cmd + " didn't work")
            exit_status = 1

        if exit_status == 0:
            logger.log(cmd + u" : returned successful", logger.DEBUG)
            exit_status = 0

        elif exit_status == 1:
            logger.log(cmd + u" returned : " + output, logger.ERROR)
            exit_status = 1

        elif exit_status == 128 or 'fatal:' in output or err:
            logger.log(cmd + u" returned : " + output, logger.ERROR)
            exit_status = 128

        else:
            logger.log(cmd + u" returned : " + output + u", treat as error for now", logger.ERROR)
            exit_status = 1

        return (output, err, exit_status)

    def _find_installed_version(self):
        """
        Attempts to find the currently installed version of Sick Beard.

        Uses git show to get commit version.

        Returns: True for success or False for failure
        """

        output, err, exit_status = self._run_git(self._git_path, 'rev-parse HEAD')  #@UnusedVariable

        if exit_status == 0 and output:
            cur_commit_hash = output.strip()
            if not re.match('^[a-z0-9]+$', cur_commit_hash):
                logger.log(u"Output doesn't look like a hash, not using it", logger.ERROR)
                return False
            self._cur_commit_hash = cur_commit_hash
            return True
        else:
            return False

    def _find_git_branch(self):
        branch_info, err, exit_status = self._run_git(self._git_path, 'symbolic-ref -q HEAD')
        if exit_status == 0 and branch_info:
            branch = branch_info.strip().replace('refs/heads/', '', 1)
            if branch:
                sickbeard.version.SICKBEARD_VERSION = branch
        return sickbeard.version.SICKBEARD_VERSION

    def _check_github_for_update(self):
        """
        Uses pygithub to ask github if there is a newer version that the provided
        commit hash. If there is a newer version it sets Sick Beard's version text.

        commit_hash: hash that we're checking against
        """

        self._num_commits_behind = 0
        self._newest_commit_hash = None

        gh = github.GitHub(self.github_repo_user, self.github_repo, self.branch)

        # find newest commit
        for curCommit in gh.commits():
            if not self._newest_commit_hash:
                self._newest_commit_hash = curCommit['sha']
                if not self._cur_commit_hash:
                    break

            if curCommit['sha'] == self._cur_commit_hash:
                break

            self._num_commits_behind += 1

        logger.log(u"newest: " + str(self._newest_commit_hash) + " and current: " + str(self._cur_commit_hash) + " and num_commits: " + str(self._num_commits_behind), logger.DEBUG)

    def set_newest_text(self):

        # if we're up to date then don't set this
        sickbeard.NEWEST_VERSION_STRING = None

        if self._num_commits_behind == 100:
            newest_text = "You are ahead of " + self.branch + ". Update not possible."

        elif self._num_commits_behind > 0:

            base_url = 'http://github.com/' + self.github_repo_user + '/' + self.github_repo
            if self._newest_commit_hash:
                url = base_url + '/compare/' + self._cur_commit_hash + '...' + self._newest_commit_hash
            else:
                url = base_url + '/commits/'

            newest_text = 'There is a <a href="' + url + '" onclick="window.open(this.href); return false;">newer version available</a> '
            newest_text += " (you're " + str(self._num_commits_behind) + " commit"
            if self._num_commits_behind > 1:
                newest_text += 's'
            newest_text += ' behind)' + "&mdash; <a href=\"" + self.get_update_url() + "\">Update Now</a>"

        else:
            return

        sickbeard.NEWEST_VERSION_STRING = newest_text

    def need_update(self):
        self._find_installed_version()

        if not self._cur_commit_hash:
            return True
        else:
            try:
                self._check_github_for_update()
            except Exception, e:
                logger.log(u"Unable to contact github, can't check for update: " + repr(e), logger.ERROR)
                return False

            logger.log(u"After checking, cur_commit = " + str(self._cur_commit_hash) + u", newest_commit = " + str(self._newest_commit_hash) + u", num_commits_behind = " + str(self._num_commits_behind), logger.DEBUG)

            if self._num_commits_behind > 0:
                return True

        return False

    def update(self):
        """
        Calls git pull origin <branch> in order to update Sick Beard. Returns a bool depending
        on the call's success.
        """

        output, err, exit_status = self._run_git(self._git_path, 'pull origin ' + self.branch)  #@UnusedVariable

        if exit_status == 0:
            return True
        else:
            return False

        return False


class SourceUpdateManager(UpdateManager):

    def __init__(self):
        self.github_repo_user = self.get_github_repo_user()
        self.github_repo = self.get_github_repo()
        self.branch = sickbeard.version.SICKBEARD_VERSION

        self._cur_commit_hash = None
        self._newest_commit_hash = None
        self._num_commits_behind = 0

    def _find_installed_version(self):

        version_file = ek.ek(os.path.join, sickbeard.PROG_DIR, u'version.txt')

        if not os.path.isfile(version_file):
            self._cur_commit_hash = None
            return

        fp = open(version_file, 'r')
        self._cur_commit_hash = fp.read().strip(' \n\r')
        fp.close()

        if not self._cur_commit_hash:
            self._cur_commit_hash = None

    def need_update(self):

        self._find_installed_version()

        try:
            self._check_github_for_update()
        except Exception, e:
            logger.log(u"Unable to contact github, can't check for update: " + repr(e), logger.ERROR)
            return False

        logger.log(u"After checking, cur_commit = " + str(self._cur_commit_hash) + u", newest_commit = " + str(self._newest_commit_hash) + u", num_commits_behind = " + str(self._num_commits_behind), logger.DEBUG)

        if not self._cur_commit_hash or self._num_commits_behind > 0:
            return True

        return False

    def _check_github_for_update(self):
        """
        Uses pygithub to ask github if there is a newer version that the provided
        commit hash. If there is a newer version it sets Sick Beard's version text.

        commit_hash: hash that we're checking against
        """

        self._num_commits_behind = 0
        self._newest_commit_hash = None

        gh = github.GitHub(self.github_repo_user, self.github_repo, self.branch)

        # find newest commit
        for curCommit in gh.commits():
            if not self._newest_commit_hash:
                self._newest_commit_hash = curCommit['sha']
                if not self._cur_commit_hash:
                    break

            if curCommit['sha'] == self._cur_commit_hash:
                break

            self._num_commits_behind += 1

        logger.log(u"newest: " + str(self._newest_commit_hash) + " and current: " + str(self._cur_commit_hash) + " and num_commits: " + str(self._num_commits_behind), logger.DEBUG)

    def set_newest_text(self):

        # if we're up to date then don't set this
        sickbeard.NEWEST_VERSION_STRING = None

        if not self._cur_commit_hash or self._num_commits_behind == 100:
            logger.log(u"Unknown current version, don't know if we should update or not", logger.DEBUG)

            newest_text = "Unknown version: If you've never used the Sick Beard upgrade system then I don't know what version you have."
            newest_text += "&mdash; <a href=\"" + self.get_update_url() + "\">Update Now</a>"

        elif self._num_commits_behind > 0:
                base_url = 'http://github.com/' + self.github_repo_user + '/' + self.github_repo
                if self._newest_commit_hash:
                    url = base_url + '/compare/' + self._cur_commit_hash + '...' + self._newest_commit_hash
                else:
                    url = base_url + '/commits/'

                newest_text = 'There is a <a href="' + url + '" onclick="window.open(this.href); return false;">newer version available</a>'
                newest_text += " (you're " + str(self._num_commits_behind) + " commit"
                if self._num_commits_behind > 1:
                    newest_text += "s"
                newest_text += " behind)" + "&mdash; <a href=\"" + self.get_update_url() + "\">Update Now</a>"
        else:
            return

        sickbeard.NEWEST_VERSION_STRING = newest_text

    def update(self):
        """
        Downloads the latest source tarball from github and installs it over the existing version.
        """
        base_url = 'https://github.com/' + self.github_repo_user + '/' + self.github_repo
        tar_download_url = base_url + '/tarball/' + self.branch
        version_path = ek.ek(os.path.join, sickbeard.PROG_DIR, u'version.txt')

        try:
            # prepare the update dir
            sb_update_dir = ek.ek(os.path.join, sickbeard.PROG_DIR, u'sb-update')

            if os.path.isdir(sb_update_dir):
                logger.log(u"Clearing out update folder " + sb_update_dir + " before extracting")
                shutil.rmtree(sb_update_dir)

            logger.log(u"Creating update folder " + sb_update_dir + " before extracting")
            os.makedirs(sb_update_dir)

            # retrieve file
            logger.log(u"Downloading update from " + repr(tar_download_url))
            tar_download_path = os.path.join(sb_update_dir, u'sb-update.tar')
            urllib.urlretrieve(tar_download_url, tar_download_path)

            if not ek.ek(os.path.isfile, tar_download_path):
                logger.log(u"Unable to retrieve new version from " + tar_download_url + ", can't update", logger.ERROR)
                return False

            # extract to sb-update dir
            logger.log(u"Extracting file " + tar_download_path)
            tar = tarfile.open(tar_download_path)
            tar.extractall(sb_update_dir)
            tar.close()

            # delete .tar.gz
            logger.log(u"Deleting file " + tar_download_path)
            os.remove(tar_download_path)

            # find update dir name
            update_dir_contents = [x for x in os.listdir(sb_update_dir) if os.path.isdir(os.path.join(sb_update_dir, x))]
            if len(update_dir_contents) != 1:
                logger.log(u"Invalid update data, update failed: " + str(update_dir_contents), logger.ERROR)
                return False
            content_dir = os.path.join(sb_update_dir, update_dir_contents[0])

            # walk temp folder and move files to main folder
            for dirname, dirnames, filenames in os.walk(content_dir):  #@UnusedVariable
                dirname = dirname[len(content_dir) + 1:]
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
            except (IOError, OSError), e:
                logger.log(u"Unable to write version file, update not complete: " + ex(e), logger.ERROR)
                return False

        except Exception, e:
            logger.log(u"Error while trying to update: " + ex(e), logger.ERROR)
            return False

        return True
