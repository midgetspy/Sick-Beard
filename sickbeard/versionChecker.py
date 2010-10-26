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

import subprocess, re, sys, os, datetime, urllib
from lib.pygithub import github

class CheckVersion():
    
    def run(self):

        cur_install_type = install_type()

        # if we're running from source try to specify the version
        if cur_install_type == 'source':
            (cur_commit_hash, cur_commit_date) = check_git_version()
            logger.log("Got git info as being: "+str(cur_commit_hash)+" @ "+str(cur_commit_date), logger.DEBUG)

        if not sickbeard.VERSION_NOTIFY:
            logger.log("Version checking is disabled, not checking for the newest version")
            return

        if cur_install_type == 'win':
        
            latestBuild = find_latest_build()
            
            if not latestBuild:
                return
            
            logger.log("Setting NEWEST_VERSION to "+str(latestBuild))
            
            sickbeard.NEWEST_VERSION = latestBuild

            if int(sickbeard.version.SICKBEARD_VERSION[6:]) < sickbeard.NEWEST_VERSION:
                set_newest_text('http://code.google.com/p/sickbeard/downloads/list', 'build '+str(latestBuild), find_latest_build(True))
        
        else:
            
            check_git_for_update(cur_commit_hash, cur_commit_date)

def install_type():

    # check if we're a windows build
    if version.SICKBEARD_VERSION.startswith('build '):
        install_type = 'win'
    else:
        install_type = 'source'

    return install_type

    
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
    newest_commit_hash = ''

    gh = github.GitHub()
    
    for curCommit in gh.commits.forBranch('midgetspy', 'Sick-Beard'):
        if not newest_commit_hash:
            newest_commit_hash = curCommit.id
        
        if curCommit.id == commit_hash:
            break
    
        num_commits_behind += 1

    days_old = 0
    if commit_date:
        how_old = datetime.datetime.now() - commit_date
        days_old = how_old.days

    # if we're up to date then don't set this
    if num_commits_behind == 35:
        message = "or else you're ahead of master"
        
    elif num_commits_behind > 0:
        message = "you're "+str(num_commits_behind)+' commits'
        if days_old:
            message += ' and '+str(days_old)+' days'
        message += ' behind'

    else:
        return

    if newest_commit_hash:
        url = 'http://github.com/midgetspy/Sick-Beard/compare/'+commit_hash+'...'+newest_commit_hash
    else:
        url = 'http://github.com/midgetspy/Sick-Beard/commits/'
    
    set_newest_text(url, message, sickbeard.WEB_ROOT+"/home/update")

def set_newest_text(url, extra_text, update_url):
    sickbeard.NEWEST_VERSION_STRING = 'There is a <a href="'+url+'" target="_new">newer version available</a> ('+extra_text+')'
    sickbeard.NEWEST_VERSION_STRING += " <a href=\""+update_url+"/home/update\">Update Now</a>"

def find_latest_build(whole_link=False):

    regex = "http://sickbeard.googlecode.com/files/SickBeard\-win32\-alpha\-build(\d+)\.zip"
    
    svnFile = urllib.urlopen("http://code.google.com/p/sickbeard/downloads/list")
    
    for curLine in svnFile.readlines():
        match = re.search(regex, curLine)
        if match:
            groups = match.groups()
            if whole_link:
                return match.group(0)
            else:
                return int(match.group(1))

    return None


def update_with_git():

    output = None
    
    try:
        p = subprocess.Popen('git pull origin '+sickbeard.version.SICKBEARD_VERSION, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=os.getcwd())
        output, err = p.communicate()
    except OSError, e:
        #logger.log("Unable to find git, can't tell what version you're running")
        logger.log('Error calling git pull: '+str(e), logger.ERROR)
        return False
    
    pull_regex = '(\d+) files? changed, (\d+) insertions?\(\+\), (\d+) deletions?\(\-\)'
    
    (files, insertions, deletions) = (None, None, None)
    
    for line in output.split('\n'):
    
        if 'Already up-to-date.' in line:
            logger.log("No update available, not updating")
            return False
        elif line.endswith('Aborting.'):
            logger.log("Unable to update from git: "+line, logger.ERROR)
            return False
    
        match = re.search(pull_regex, line)
        if match:
            (files, insertions, deletions) = match.groups()
            break

    if None in (files, insertions, deletions):
        logger.log("Didn't find indication of success in output, assuming git pull failed", logger.ERROR)
        return False
    
    return True

def update_from_google_code():
    
    new_link = find_latest_build(True)
    
    if not new_link:
        logger.log("Unable to find a new version link on google code, not updating")

    # unzip it
    
    # write a bat file
    
    # shut down