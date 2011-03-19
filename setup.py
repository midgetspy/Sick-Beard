import re
import urllib, ConfigParser
from distutils.core import setup
import py2exe, sys, os, shutil, datetime, zipfile, subprocess, fnmatch
import googlecode_upload
from lib.pygithub import github

# mostly stolen from the SABnzbd package.py file
name = 'SickBeard'
version = '0.1'

release = name + '-' + version

Win32ConsoleName = 'SickBeard-console.exe'
Win32WindowName = 'SickBeard.exe'

def findLatestBuild():

    regex = "http\://sickbeard\.googlecode\.com/files/SickBeard\-win32\-alpha\-build(\d+)(?:\.\d+)?\.zip"
    
    svnFile = urllib.urlopen("http://code.google.com/p/sickbeard/downloads/list")
    
    for curLine in svnFile.readlines():
        match = re.search(regex, curLine)
        if match:
            groups = match.groups()
            return int(groups[0])

    return None

def recursive_find_data_files(root_dir, allowed_extensions=('*')):
    
    to_return = {}
    for (dirpath, dirnames, filenames) in os.walk(root_dir):
        if not filenames:
            continue
        
        for cur_filename in filenames:
            
            matches_pattern = False
            for cur_pattern in allowed_extensions:
                if fnmatch.fnmatch(cur_filename, '*.'+cur_pattern):
                    matches_pattern = True
            if not matches_pattern:
                continue
            
            cur_filepath = os.path.join(dirpath, cur_filename)
            to_return.setdefault(dirpath, []).append(cur_filepath)
            
    return sorted(to_return.items())


def find_all_libraries(root_dirs):
    
    libs = []
    
    for cur_root_dir in root_dirs:
        for (dirpath, dirnames, filenames) in os.walk(cur_root_dir):
            if '__init__.py' not in filenames:
                continue
            
            libs.append(dirpath.replace(os.sep, '.')) 
    
    return libs


def allFiles(dir):
    files = []
    for file in os.listdir(dir):
        fullFile = os.path.join(dir, file)
        if os.path.isdir(fullFile):
            files += allFiles(fullFile)
        else:
            files.append(fullFile) 

    return files

# save the original arguments and replace them with the py2exe args
oldArgs = []
if len(sys.argv) > 1:
    oldArgs = sys.argv[1:]
    del sys.argv[1:]

sys.argv.append('py2exe')

# clear the dist dir
if os.path.isdir('dist'):
    shutil.rmtree('dist')

# root source dir
compile_dir = os.path.dirname(os.path.normpath(os.path.abspath(sys.argv[0])))

if not 'nopull' in oldArgs:
    # pull new source from git
    print 'Updating source from git'
    p = subprocess.Popen('git pull origin master', shell=True, cwd=compile_dir)
    o,e = p.communicate()

# figure out what build this is going to be
latestBuild = findLatestBuild()
if 'test' in oldArgs:
    currentBuildNumber = str(latestBuild)+'a'
else:
    currentBuildNumber = latestBuild+1

# write the version file before we compile
versionFile = open("sickbeard/version.py", "w")
versionFile.write("SICKBEARD_VERSION = \"build "+str(currentBuildNumber)+"\"")
versionFile.close()

# set up the compilation options
data_files = recursive_find_data_files('data', ['gif', 'png', 'jpg', 'ico', 'js', 'css', 'tmpl'])

options = dict(
    name=name,
    version=release,
    author='Nic Wolfe',
    author_email='nic@wolfeden.ca',
    description=name + ' ' + release,
    scripts=['SickBeard.py'],
    packages=find_all_libraries(['sickbeard', 'lib']),
)

# set up py2exe to generate the console app
program = [ {'script': 'SickBeard.py' } ]
options['options'] = {'py2exe':
                        {
                         'bundle_files': 3,
                         'packages': ['Cheetah'],
                         'excludes': ['Tkconstants', 'Tkinter', 'tcl'],
                         'optimize': 2,
                         'compressed': 0
                        }
                     }
options['zipfile'] = 'lib/sickbeard.zip'
options['console'] = program
options['data_files'] = data_files

# compile sickbeard-console.exe
setup(**options)

# rename the exe to sickbeard-console.exe
try:
    if os.path.exists("dist/%s" % Win32ConsoleName):
        os.remove("dist/%s" % Win32ConsoleName)
    os.rename("dist/%s" % Win32WindowName, "dist/%s" % Win32ConsoleName)
except:
    print "Cannot create dist/%s" % Win32ConsoleName
    #sys.exit(1)

# we don't need this stuff when we make the 2nd exe
del options['console']
del options['data_files']
options['windows'] = program

# compile sickbeard.exe
setup(**options)

# compile sabToSickbeard.exe using the existing setup.py script
auto_process_dir = os.path.join(compile_dir, 'autoProcessTV')
p = subprocess.Popen([ sys.executable, os.path.join(auto_process_dir, 'setup.py') ], cwd=auto_process_dir, shell=True)
o,e = p.communicate()

# copy autoProcessTV files to the dist dir
auto_process_files = ['autoProcessTV/sabToSickBeard.py',
                      'autoProcessTV/hellaToSickBeard.py',
                      'autoProcessTV/autoProcessTV.py',
                      'autoProcessTV/autoProcessTV.cfg.sample',
                      'autoProcessTV/sabToSickBeard.exe']
 
os.makedirs('dist/autoProcessTV')
 
for curFile in auto_process_files:
    newFile = os.path.join('dist', curFile)
    print "Copying file from", curFile, "to", newFile
    shutil.copy(curFile, newFile)

# compile updater.exe
setup(
      options = {'py2exe': {'bundle_files': 1}},
      zipfile = None,
      console = ['updater.py'],
)

if 'test' in oldArgs:
    print "Ignoring changelog for test build"
else:
    # start building the CHANGELOG.txt
    print 'Creating changelog'
    gh = github.GitHub()
    
    # read the old changelog and find the last commit from that build
    lastCommit = ""
    try:
        cl = open("CHANGELOG.txt", "r")
        lastCommit = cl.readlines()[0].strip()
        cl.close()
    except:
        print "I guess there's no changelog"
    
    newestCommit = ""
    changeString = ""

    # cycle through all the git commits and save their commit messages
    for curCommit in gh.commits.forBranch('midgetspy', 'Sick-Beard'):
        if curCommit.id == lastCommit:
            break
    
        if newestCommit == "":
            newestCommit = curCommit.id
        
        changeString += curCommit.message + "\n\n"
    
    # if we didn't find any changes don't make a changelog file
    if newestCommit != "":
        newChangelog = open("CHANGELOG.txt", "w")
        newChangelog.write(newestCommit+"\n\n")
        newChangelog.write("Changelog for build "+str(currentBuildNumber)+"\n\n")
        newChangelog.write(changeString)
        newChangelog.close()
    else:
        print "No changes found, keeping old changelog"

# put the changelog in the compile dir
if os.path.exists("CHANGELOG.txt"):
    shutil.copy('CHANGELOG.txt', 'dist/')

# figure out what we're going to call the zip file
print 'Zipping files...'
zipFilename = 'SickBeard-win32-alpha-build'+str(currentBuildNumber)
if os.path.isfile(zipFilename + '.zip'):
    zipNum = 2
    while os.path.isfile(zipFilename + '.{0:0>2}.zip'.format(str(zipNum))):
        zipNum += 1
    zipFilename = zipFilename + '.{0:0>2}'.format(str(zipNum))

# get a list of files to add to the zip
zipFileList = allFiles('dist/')

# add all files to the zip
z = zipfile.ZipFile(zipFilename + '.zip', 'w', zipfile.ZIP_DEFLATED)
for file in zipFileList:
    z.write(file, file.replace('dist/', zipFilename + '/'))
z.close()

print "Created zip at", zipFilename

# leave version file as it is in source
print "Reverting version file to master"
versionFile = open("sickbeard/version.py", "w")
versionFile.write("SICKBEARD_VERSION = \"master\"")
versionFile.close()

# i store my google code username/pw in a config so i can have this file in public source control 
config = ConfigParser.ConfigParser()
configFilename = os.path.join(compile_dir, "gc.ini")
config.read(configFilename)

gc_username = config.get("GC", "username")
gc_password = config.get("GC", "password")

# upload to google code unless I tell it not to
if "noup" not in oldArgs and "test" not in oldArgs:
    print "Uploading zip to google code"
    googlecode_upload.upload(os.path.abspath(zipFilename+".zip"), "sickbeard", gc_username, gc_password, "Win32 alpha build "+str(currentBuildNumber)+" (unstable/development release)", ["Featured","Type-Executable","OpSys-Windows"])
 
if 'nopush' not in oldArgs and 'test' not in oldArgs:
    # tag commit as a new build and push changes to github
    print 'Tagging commit and pushing'
    p = subprocess.Popen('git tag -a "build-'+str(currentBuildNumber)+'" -m "Windows build '+zipFilename+'"', shell=True, cwd=compile_dir)
    o,e = p.communicate()
    p = subprocess.Popen('git push --tags origin windows_binaries', shell=True, cwd=compile_dir)
    o,e = p.communicate()
