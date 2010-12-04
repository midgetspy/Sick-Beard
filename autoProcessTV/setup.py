from distutils.core import setup
import py2exe, sys, shutil

sys.argv.append('py2exe')

setup(
      options = {'py2exe': {'bundle_files': 1}},
#      windows = [{'console': "sabToSickbeard.py"}],
      zipfile = None,
      console = ['sabToSickbeard.py'],
)

shutil.copy('dist/sabToSickbeard.exe', '.')
