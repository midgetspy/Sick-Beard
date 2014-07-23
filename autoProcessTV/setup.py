from distutils.core import setup
import py2exe
import sys
import shutil

sys.argv.append('py2exe')

setup(
      options={'py2exe': {'bundle_files': 1}},
      zipfile=None,
      console=[{'script': 'sabToSickbeard.py',
                'icon_resources': [(0, "../data/images/ico/sickbeard.ico")],
                'version': '0.0.0.1',
                'company_name': 'SickBeard-Team',
                'name': 'sabToSickbeard',
                'comments': 'sabToSickbeard - SABnzbd post-processing script',
                'copyright': 'Copyright (C) 2009-2014 Nic Wolfe',
                }],
)

shutil.copy('dist/sabToSickbeard.exe', '.')
