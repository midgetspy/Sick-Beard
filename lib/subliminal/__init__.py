# -*- coding: utf-8 -*-
__title__ = 'subliminal'
__version__ = '0.8.0-dev'
__author__ = 'Antoine Bertin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2013 Antoine Bertin'

import logging
from .api import list_subtitles, download_subtitles, download_best_subtitles, save_subtitles
#from .cache import MutexLock, region as cache_region
from .exceptions import Error, ProviderError
from .providers import Provider, ProviderPool, provider_manager
from .subtitle import Subtitle
from .video import VIDEO_EXTENSIONS, SUBTITLE_EXTENSIONS, Video, Episode, Movie, scan_videos, scan_video


logging.getLogger(__name__).addHandler(logging.NullHandler())
