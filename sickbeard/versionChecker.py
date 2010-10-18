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

import subprocess, re, sys, os, datetime
from lib.pygithub import github

class CheckVersion():
    
    def run(self):

        # check if we're a windows build
        if version.SICKBEARD_VERSION.startswith('build '):
            install_type = 'win'
        elif version.SICKBEARD_VERSION == 'master':
            install_type = 'source'
        else:
            logger.log("Unknown install type, not doing any version checking", logger.ERROR)

        # if we're running from source try to specify the version
        if install_type == 'source':
            (cur_commit_hash, cur_commit_date) = check_git_version()
            logger.log("Got git info as being: "+cur_commit_hash+" @ "+str(cur_commit_date), logger.DEBUG)

        if not sickbeard.VERSION_NOTIFY:
            logger.log("Version checking is disabled, not checking for the newest version")
            return

        if install_type == 'win':
        
            latestBuild = helpers.findLatestBuild()
            
            if latestBuild == None:
                return
            
            logger.log("Setting NEWEST_VERSION to "+str(latestBuild))
            
            sickbeard.NEWEST_VERSION = latestBuild

            if int(sickbeard.version.SICKBEARD_VERSION[6:]) < sickbeard.NEWEST_VERSION:
                set_newest_text('http://code.google.com/p/sickbeard/downloads/list', 'build '+str(latestBuild))
        
        else:
            
            check_git_for_update(cur_commit_hash, cur_commit_date)
    
def check_git_version():

    output = None
    
    try:
        p = subprocess.Popen('git show', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=os.getcwd())
        output, err = p.communicate()
    except OSError, e:
        logger.log("Unable to find git, can't tell what version you're running")
        return (None, None)
    
    commit_regex = '^commit ([a-f0-9]+)$'
    date_regex = '^Date:\s+(\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4}) [\-\+]\d{4}$'
    
    cur_commit_hash = None
    cur_commit_date = None
    
    for line in output.split('\n'):
        if cur_commit_hash and cur_commit_date:
            break
    
        match = re.match(commit_regex, line)
        if match:
            cur_commit_hash = match.group(1)
            continue
    
        match = re.match(date_regex, line)
        if match:
            cur_commit_date = datetime.datetime.strptime(match.group(1), '%a %b %d %H:%M:%S %Y')
            continue

    if not cur_commit_hash:
        logger.log("Unable to find a version number in the git output")
        return (None, None)

    version.SICKBEARD_VERSION = 'master'

    return (cur_commit_hash, cur_commit_date)
    

def check_git_for_update(commit_hash, commit_date=None):
    
    if not commit_hash:
        return
    
    num_commits_behind = 0

    gh = github.GitHub()
    
    for curCommit in gh.commits.forBranch('midgetspy', 'Sick-Beard'):
        if curCommit.id == commit_hash:
            break
    
        num_commits_behind += 1

    days_old = 0
    if commit_date:
        how_old = datetime.datetime.now() - commit_date
        days_old = how_old.days

    # if we're up to date then don't set this
    if num_commits_behind == 35:
        set_newest_text('http://github.com/midgetspy/Sick-Beard/commits/', "or else you're ahead of master")
        
    elif num_commits_behind:
        set_newest_text('http://github.com/midgetspy/Sick-Beard/commits/', str(num_commits_behind)+' commits and '+str(days_old)+' days ahead')

def set_newest_text(url, extra_text):
    sickbeard.NEWEST_VERSION_STRING = 'There is a <a href="'+url+'" target="_new">newer version available</a> ('+extra_text+')'
