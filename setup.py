import ConfigParser
from distutils.core import setup
import sys
import os
import shutil
import zipfile
import subprocess
import fnmatch
import googlecode_upload
import getopt

try:
    import py2exe
except ImportError:
    print
    sys.exit("ERROR you need py2exe to build a win binary http://www.py2exe.org/")

# only build off python 2.6+
if sys.version_info < (2, 6):
    sys.exit("Sorry, requires Python 2.6+")

if len(sys.argv) < 2:
    sys.exit("No build # specified, aborting")


def recursive_find_data_files(root_dir, allowed_extensions=('*')):
    to_return = {}
    for (dirpath, _dirnames, filenames) in os.walk(root_dir):
        if not filenames:
            continue

        for cur_filename in filenames:

            matches_pattern = False
            for cur_pattern in allowed_extensions:
                if fnmatch.fnmatch(cur_filename, '*.' + cur_pattern):
                    matches_pattern = True
            if not matches_pattern:
                continue

            cur_filepath = os.path.join(dirpath, cur_filename)
            to_return.setdefault(dirpath, []).append(cur_filepath)

    return sorted(to_return.items())


def find_all_libraries(root_dirs):
    libs = []
    for cur_root_dir in root_dirs:
        for (dirpath, _dirnames, filenames) in os.walk(cur_root_dir):
            if '__init__.py' not in filenames:
                continue

            libs.append(dirpath.replace(os.sep, '.'))

    return libs


def allFiles(directory):
    files = []
    for item in os.listdir(directory):
        path = os.path.join(directory, item)
        if os.path.isdir(path):
            files += allFiles(path)
        else:
            files.append(path)

    return files


def buildWIN(buildParams):
    # constants
    Win32ConsoleName = 'SickBeard-console.exe'
    Win32WindowName = 'SickBeard.exe'

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

    currentBuildNumber = oldArgs[0]
    oldArgs = oldArgs[1:]

    if not buildParams['nopull']:
        # pull new source from git
        print 'Updating source from git'
        p = subprocess.Popen('git pull origin master', shell=True, cwd=compile_dir)
        o, e = p.communicate()

    # write the version file before we compile
    versionFile = open("sickbeard/version.py", "w")
    versionFile.write("SICKBEARD_VERSION = \"build " + str(currentBuildNumber) + "\"")
    versionFile.close()

    # set up the compilation options
    data_files = recursive_find_data_files('data', ['gif', 'png', 'jpg', 'ico', 'js', 'css', 'tmpl'])

    options = dict(
        name=buildParams['name'],
        author='Nic Wolfe',
        author_email='nic@wolfeden.ca',
        maintainer='%s-Team' % buildParams['name'],
        description=buildParams['packageName'],
        scripts=['SickBeard.py'],
        packages=find_all_libraries(['sickbeard', 'lib']),
    )

    # set up py2exe to generate the console app
    program = [ {'script': 'SickBeard.py',
                 'icon_resources': [(0, "data/images/ico/sickbeard.ico")],
                 'version': '0.0.0.0',
                 'company_name': '%s-Team' % buildParams['name'],
                 'name': buildParams['name'] + ' build' + str(currentBuildNumber),
                 'comments': buildParams['name'] + ' build' + str(currentBuildNumber),
                 'copyright': 'Copyright (C) 2009-2014 Nic Wolfe',
                 }]

    options['options'] = {'py2exe':
                            {'bundle_files': 3,
                             'packages': ['Cheetah'],
                             'excludes': ['Tkconstants', 'Tkinter', 'tcl', 'doctest', 'unittest'],
                             'optimize': 2,
                             'compressed': 0
                             }
                          }
    options['zipfile'] = 'lib/sickbeard.zip'
    options['console'] = program
    options['data_files'] = data_files

    if buildParams['test']:
        print
        print "########################################"
        print "NOT Building exe this was a TEST."
        print "########################################"
        return True

    # compile sickbeard-console.exe
    setup(**options)

    # rename the exe to sickbeard-console.exe
    try:
        if os.path.exists("dist/%s" % Win32ConsoleName):
            os.remove("dist/%s" % Win32ConsoleName)
        os.rename("dist/%s" % Win32WindowName, "dist/%s" % Win32ConsoleName)
    except:
        print "Cannot create dist/%s" % Win32ConsoleName

    # we don't need this stuff when we make the 2nd exe
    del options['console']
    del options['data_files']
    options['windows'] = program

    # compile sickbeard.exe
    setup(**options)

    # compile sabToSickbeard.exe using the existing setup.py script
    auto_process_dir = os.path.join(compile_dir, 'autoProcessTV')
    p = subprocess.Popen([ sys.executable, os.path.join(auto_process_dir, 'setup.py') ], cwd=auto_process_dir, shell=True)
    o, e = p.communicate()

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
          options={'py2exe': {'bundle_files': 1}},
          zipfile=None,
          console=['updater.py'],
    )

    # put the changelog in the compile dir
    if os.path.exists("CHANGELOG.txt"):
        shutil.copy('CHANGELOG.txt', 'dist/')

    # figure out what we're going to call the zip file
    print 'Zipping files...'
    zipFilename = 'SickBeard-win32-alpha-build' + str(currentBuildNumber)
    if os.path.isfile(zipFilename + '.zip'):
        zipNum = 2
        while os.path.isfile(zipFilename + '.{0:0>2}.zip'.format(str(zipNum))):
            zipNum += 1
        zipFilename = zipFilename + '.{0:0>2}'.format(str(zipNum))

    # get a list of files to add to the zip
    zipFileList = allFiles('dist/')

    # add all files to the zip
    z = zipfile.ZipFile(zipFilename + '.zip', 'w', zipfile.ZIP_DEFLATED)
    for entry in zipFileList:
        z.write(entry, entry.replace('dist/', zipFilename + '/'))
    z.close()

    print "Created zip at", zipFilename

    # leave version file as it is in source
    print "Reverting version file to master"
    versionFile = open("sickbeard/version.py", "w")
    versionFile.write("SICKBEARD_VERSION = \"master\"")
    versionFile.close()

    if not buildParams['noup']:
        # i store my google code username/pw in a config so i can have this file in public source control
        config = ConfigParser.ConfigParser()
        configFilename = os.path.join(compile_dir, "gc.ini")
        config.read(configFilename)

        gc_username = config.get("GC", "username")
        gc_password = config.get("GC", "password")

        print "Uploading zip to google code"
        googlecode_upload.upload(os.path.abspath(zipFilename + ".zip"), "sickbeard", gc_username, gc_password, "Win32 alpha build " + str(currentBuildNumber) + " (unstable/development release)", ["Featured", "Type-Executable", "OpSys-Windows"])

    if not buildParams['nopush'] and not buildParams['test']:
        # tag commit as a new build and push changes to github
        print 'Tagging commit and pushing'
        p = subprocess.Popen('git tag -a "build-' + str(currentBuildNumber) + '" -m "Windows build ' + zipFilename + '"', shell=True, cwd=compile_dir)
        o, e = p.communicate()
        p = subprocess.Popen('git push --tags origin windows_binaries', shell=True, cwd=compile_dir)
        o, e = p.communicate()


def main():
    buildParams = {}
    ######################
    # defaults
    buildParams['nopull'] = False
    buildParams['noup'] = True  # disabled due to no longer using GC
    buildParams['nopush'] = False
    buildParams['test'] = False

    try:
        opts, args = getopt.getopt(sys.argv[2:], "", [ 'nopull', 'noup', 'nopush', 'test' ])  # @UnusedVariable
    except getopt.GetoptError:
        print "Available options: --nopull, --noup, --nopush, --test, "
        exit(1)

    for o, a in opts:

        # Pull down latest changes from git before building
        if o in ('--nopull'):
            buildParams['nopull'] = True

        # Upload latest build to GoogleCode when completed
        if o in ('--noup'):
            buildParams['noup'] = True

        # Upload latest commit to branch when build completes
        if o in ('--nopush'):
            buildParams['nopush'] = True

        if o in ('--test'):
            buildParams['test'] = True

    # constants
    buildParams['name'] = "SickBeard"
    buildParams['majorVersion'] = "alpha"
    buildParams['targetOS'] = "win32"

    buildParams['packageName'] = "%s-%s-%s-%s" % (buildParams['name'], buildParams['targetOS'], buildParams['majorVersion'], 'build' + sys.argv[1])

    print
    print "########################################"
    print "Starting build " + buildParams['packageName'] + " ..."
    print "########################################"

    buildWIN(buildParams)

    print
    print "########################################"
    print "Finished build " + buildParams['packageName']
    print "########################################"

if __name__ == '__main__':
    main()
