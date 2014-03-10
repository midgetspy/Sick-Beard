# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division
import datetime
import hashlib
import logging
import os
import struct
import babelfish
import enzyme
import guessit


logger = logging.getLogger(__name__)

#: Video extensions
VIDEO_EXTENSIONS = ('.3g2', '.3gp', '.3gp2', '.3gpp', '.60d', '.ajp', '.asf', '.asx', '.avchd', '.avi', '.bik',
                    '.bix', '.box', '.cam', '.dat', '.divx', '.dmf', '.dv', '.dvr-ms', '.evo', '.flc', '.fli',
                    '.flic', '.flv', '.flx', '.gvi', '.gvp', '.h264', '.m1v', '.m2p', '.m2ts', '.m2v', '.m4e',
                    '.m4v', '.mjp', '.mjpeg', '.mjpg', '.mkv', '.moov', '.mov', '.movhd', '.movie', '.movx', '.mp4',
                    '.mpe', '.mpeg', '.mpg', '.mpv', '.mpv2', '.mxf', '.nsv', '.nut', '.ogg', '.ogm', '.omf', '.ps',
                    '.qt', '.ram', '.rm', '.rmvb', '.swf', '.ts', '.vfw', '.vid', '.video', '.viv', '.vivo', '.vob',
                    '.vro', '.wm', '.wmv', '.wmx', '.wrap', '.wvx', '.wx', '.x264', '.xvid')

#: Subtitle extensions
SUBTITLE_EXTENSIONS = ('.srt', '.sub', '.smi', '.txt', '.ssa', '.ass', '.mpl')


class Video(object):
    """Base class for videos

    Represent a video, existing or not, with various properties that defines it.
    Each property has an associated score based on equations that are described in
    subclasses.

    :param string name: name or path of the video
    :param string format: format of the video (HDTV, WEB-DL, ...)
    :param string release_group: release group of the video
    :param string resolution: screen size of the video stream (480p, 720p, 1080p or 1080i)
    :param string video_codec: codec of the video stream
    :param string audio_codec: codec of the main audio stream
    :param int imdb_id: IMDb id of the video
    :param dict hashes: hashes of the video file by provider names
    :param int size: byte size of the video file
    :param set subtitle_languages: existing subtitle languages

    """
    scores = {}

    def __init__(self, name, format=None, release_group=None, resolution=None, video_codec=None, audio_codec=None,
                 imdb_id=None, hashes=None, size=None, subtitle_languages=None):
        self.name = name
        self.format = format
        self.release_group = release_group
        self.resolution = resolution
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.imdb_id = imdb_id
        self.hashes = hashes or {}
        self.size = size
        self.subtitle_languages = subtitle_languages or set()

    @classmethod
    def fromguess(cls, name, guess):
        if guess['type'] == 'episode':
            return Episode.fromguess(name, guess)
        if guess['type'] == 'movie':
            return Movie.fromguess(name, guess)
        raise ValueError('The guess must be an episode or a movie guess')

    @classmethod
    def fromname(cls, name):
        return cls.fromguess(os.path.split(name)[1], guessit.guess_file_info(name, 'autodetect'))

    def __repr__(self):
        return '<%s [%r]>' % (self.__class__.__name__, self.name)

    def __hash__(self):
        return hash(self.name)


class Episode(Video):
    """Episode :class:`Video`

    Scores are defined by a set of equations, see :func:`~subliminal.score.get_episode_equations`

    :param string series: series of the episode
    :param int season: season number of the episode
    :param int episode: episode number of the episode
    :param string title: title of the episode
    :param int year: year of series
    :param int tvdb_id: TheTVDB id of the episode

    """
    scores = {'format': 3, 'video_codec': 2, 'tvdb_id': 48, 'title': 12, 'imdb_id': 60, 'audio_codec': 1, 'year': 24,
              'resolution': 2, 'season': 6, 'release_group': 6, 'series': 24, 'episode': 6, 'hash': 74}

    def __init__(self, name, series, season, episode, format=None, release_group=None, resolution=None, video_codec=None,
                 audio_codec=None, imdb_id=None, hashes=None, size=None, subtitle_languages=None, title=None,
                 year=None, tvdb_id=None):
        super(Episode, self).__init__(name, format, release_group, resolution, video_codec, audio_codec, imdb_id, hashes,
                                      size, subtitle_languages)
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.year = year
        self.tvdb_id = tvdb_id

    @classmethod
    def fromguess(cls, name, guess):
        if guess['type'] != 'episode':
            raise ValueError('The guess must be an episode guess')
        if 'series' not in guess or 'season' not in guess or 'episodeNumber' not in guess:
            raise ValueError('Insufficient data to process the guess')
        return cls(name, guess['series'], guess['season'], guess['episodeNumber'], format=guess.get('format'),
                   release_group=guess.get('releaseGroup'), resolution=guess.get('screenSize'),
                   video_codec=guess.get('videoCodec'), audio_codec=guess.get('audioCodec'),
                   title=guess.get('title'), year=guess.get('year'))

    @classmethod
    def fromname(cls, name):
        return cls.fromguess(os.path.split(name)[1], guessit.guess_episode_info(name))

    def __repr__(self):
        if self.year is None:
            return '<%s [%r, %dx%d]>' % (self.__class__.__name__, self.series, self.season, self.episode)
        return '<%s [%r, %d, %dx%d]>' % (self.__class__.__name__, self.series, self.year, self.season, self.episode)


class Movie(Video):
    """Movie :class:`Video`

    Scores are defined by a set of equations, see :func:`~subliminal.score.get_movie_equations`

    :param string title: title of the movie
    :param int year: year of the movie

    """
    scores = {'format': 3, 'video_codec': 2, 'title': 13, 'imdb_id': 34, 'audio_codec': 1, 'year': 7, 'resolution': 2,
              'release_group': 6, 'hash': 34}

    def __init__(self, name, title, format=None, release_group=None, resolution=None, video_codec=None, audio_codec=None,
                 imdb_id=None, hashes=None, size=None, subtitle_languages=None, year=None):
        super(Movie, self).__init__(name, format, release_group, resolution, video_codec, audio_codec, imdb_id, hashes,
                                    size, subtitle_languages)
        self.title = title
        self.year = year

    @classmethod
    def fromguess(cls, name, guess):
        if guess['type'] != 'movie':
            raise ValueError('The guess must be a movie guess')
        if 'title' not in guess:
            raise ValueError('Insufficient data to process the guess')
        return cls(name, guess['title'], format=guess.get('format'), release_group=guess.get('releaseGroup'),
                   resolution=guess.get('screenSize'), video_codec=guess.get('videoCodec'),
                   audio_codec=guess.get('audioCodec'),year=guess.get('year'))

    @classmethod
    def fromname(cls, name):
        return cls.fromguess(os.path.split(name)[1], guessit.guess_movie_info(name))

    def __repr__(self):
        if self.year is None:
            return '<%s [%r]>' % (self.__class__.__name__, self.title)
        return '<%s [%r, %d]>' % (self.__class__.__name__, self.title, self.year)


def scan_subtitle_languages(path):
    """Search for subtitles with alpha2 extension from a video `path` and return their language

    :param string path: path to the video
    :return: found subtitle languages
    :rtype: set

    """
    language_extensions = tuple('.' + c for c in babelfish.language_converters['alpha2'].codes)
    dirpath, filename = os.path.split(path)
    subtitles = set()
    for p in os.listdir(dirpath):
        if not isinstance(p, bytes) and p.startswith(os.path.splitext(filename)[0]) and p.endswith(SUBTITLE_EXTENSIONS):
            if os.path.splitext(p)[0].endswith(language_extensions):
                subtitles.add(babelfish.Language.fromalpha2(os.path.splitext(p)[0][-2:]))
            else:
                subtitles.add(babelfish.Language('und'))
    logger.debug('Found subtitles %r', subtitles)
    return subtitles


def scan_video(path, subtitles=True, embedded_subtitles=True):
    """Scan a video and its subtitle languages from a video `path`

    :param string path: absolute path to the video
    :param bool subtitles: scan for subtitles with the same name
    :param bool embedded_subtitles: scan for embedded subtitles
    :return: the scanned video
    :rtype: :class:`Video`
    :raise: ValueError if cannot guess enough information from the path

    """
    dirpath, filename = os.path.split(path)
    logger.info('Scanning video %r in %r', filename, dirpath)
    video = Video.fromguess(path, guessit.guess_file_info(path, 'autodetect'))
    video.size = os.path.getsize(path)
    if video.size > 10485760:
        logger.debug('Size is %d', video.size)
        video.hashes['opensubtitles'] = hash_opensubtitles(path)
        video.hashes['thesubdb'] = hash_thesubdb(path)
        logger.debug('Computed hashes %r', video.hashes)
    else:
        logger.warning('Size is lower than 10MB: hashes not computed')
    if subtitles:
        video.subtitle_languages |= scan_subtitle_languages(path)
    # enzyme
    try:
        if filename.endswith('.mkv'):
            with open(path, 'rb') as f:
                mkv = enzyme.MKV(f)
            if mkv.video_tracks:
                video_track = mkv.video_tracks[0]
                # resolution
                if video_track.height in (480, 720, 1080):
                    if video_track.interlaced:
                        video.resolution = '%di' % video_track.height
                        logger.debug('Found resolution %s with enzyme', video.resolution)
                    else:
                        video.resolution = '%dp' % video_track.height
                        logger.debug('Found resolution %s with enzyme', video.resolution)
                # video codec
                if video_track.codec_id == 'V_MPEG4/ISO/AVC':
                    video.video_codec = 'h264'
                    logger.debug('Found video_codec %s with enzyme', video.video_codec)
                elif video_track.codec_id == 'V_MPEG4/ISO/SP':
                    video.video_codec = 'DivX'
                    logger.debug('Found video_codec %s with enzyme', video.video_codec)
                elif video_track.codec_id == 'V_MPEG4/ISO/ASP':
                    video.video_codec = 'XviD'
                    logger.debug('Found video_codec %s with enzyme', video.video_codec)
            else:
                logger.warning('MKV has no video track')
            if mkv.audio_tracks:
                audio_track = mkv.audio_tracks[0]
                # audio codec
                if audio_track.codec_id == 'A_AC3':
                    video.audio_codec = 'AC3'
                    logger.debug('Found audio_codec %s with enzyme', video.audio_codec)
                elif audio_track.codec_id == 'A_DTS':
                    video.audio_codec = 'DTS'
                    logger.debug('Found audio_codec %s with enzyme', video.audio_codec)
                elif audio_track.codec_id == 'A_AAC':
                    video.audio_codec = 'AAC'
                    logger.debug('Found audio_codec %s with enzyme', video.audio_codec)
            else:
                logger.warning('MKV has no audio track')
            if mkv.subtitle_tracks:
                # embedded subtitles
                if embedded_subtitles:
                    embedded_subtitle_languages = set()
                    for st in mkv.subtitle_tracks:
                        if st.language:
                            try:
                                embedded_subtitle_languages.add(babelfish.Language.fromalpha3b(st.language))
                            except babelfish.Error:
                                logger.error('Embedded subtitle track language %r is not a valid language', st.language)
                                embedded_subtitle_languages.add(babelfish.Language('und'))
                        elif st.name:
                            try:
                                embedded_subtitle_languages.add(babelfish.Language.fromname(st.name))
                            except babelfish.Error:
                                logger.debug('Embedded subtitle track name %r is not a valid language', st.name)
                                embedded_subtitle_languages.add(babelfish.Language('und'))
                        else:
                            embedded_subtitle_languages.add(babelfish.Language('und'))
                    logger.debug('Found embedded subtitle %r with enzyme', embedded_subtitle_languages)
                    video.subtitle_languages |= embedded_subtitle_languages
            else:
                logger.debug('MKV has no subtitle track')
    except enzyme.Error:
        logger.exception('Parsing video metadata with enzyme failed')
    return video


def scan_videos(paths, subtitles=True, embedded_subtitles=True, age=None):
    """Scan `paths` for videos and their subtitle languages

    :params paths: absolute paths to scan for videos
    :type paths: list of string
    :param bool subtitles: scan for subtitles with the same name
    :param bool embedded_subtitles: scan for embedded subtitles
    :param age: age of the video, if any
    :type age: datetime.timedelta or None
    :return: the scanned videos
    :rtype: list of :class:`Video`

    """
    videos = []
    # scan files
    for filepath in [p for p in paths if os.path.isfile(p)]:
        if age is not None:
            try:
                video_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
            except ValueError:
                logger.exception('Error while getting video age, skipping it')
                continue
            if video_age > age:
                logger.info('Skipping video %r: older than %r', filepath, age)
                continue
        try:
            videos.append(scan_video(filepath, subtitles, embedded_subtitles))
        except ValueError as e:
            logger.error('Skipping video: %s', e)
            continue
    # scan directories
    for path in [p for p in paths if os.path.isdir(p)]:
        logger.info('Scanning directory %r', path)
        for dirpath, dirnames, filenames in os.walk(path):
            # skip badly encoded directories
            if isinstance(dirpath, bytes):
                logger.error('Skipping badly encoded directory %r', dirpath.decode('utf-8', errors='replace'))
                continue
            # skip badly encoded and hidden sub directories
            for dirname in list(dirnames):
                if isinstance(dirname, bytes):
                    logger.error('Skipping badly encoded dirname %r in %r', dirname.decode('utf-8', errors='replace'),
                                 dirpath)
                    dirnames.remove(dirname)
                elif dirname.startswith('.'):
                    logger.debug('Skipping hidden dirname %r in %r', dirname, dirpath)
                    dirnames.remove(dirname)
            # scan for videos
            for filename in filenames:
                # skip badly encoded files
                if isinstance(filename, bytes):
                    logger.error('Skipping badly encoded filename %r in %r', filename.decode('utf-8', errors='replace'),
                                 dirpath)
                    continue
                # filter videos
                if not filename.endswith(VIDEO_EXTENSIONS):
                    continue
                # skip hidden files
                if filename.startswith('.'):
                    logger.debug('Skipping hidden filename %r in %r', filename, dirpath)
                    continue
                filepath = os.path.join(dirpath, filename)
                # skip links
                if os.path.islink(filepath):
                    logger.debug('Skipping link %r in %r', filename, dirpath)
                    continue
                if age is not None:
                    try:
                        video_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
                    except ValueError:
                        logger.exception('Error while getting video age, skipping it')
                        continue
                    if video_age > age:
                        logger.info('Skipping video %r: older than %r', filepath, age)
                        continue
                try:
                    video = scan_video(filepath, subtitles, embedded_subtitles)
                except ValueError as e:
                    logger.error('Skipping video: %s', e)
                    continue
                videos.append(video)
    return videos


def hash_opensubtitles(video_path):
    """Compute a hash using OpenSubtitles' algorithm

    :param string video_path: path of the video
    :return: the hash
    :rtype: string

    """
    bytesize = struct.calcsize(b'<q')
    with open(video_path, 'rb') as f:
        filesize = os.path.getsize(video_path)
        filehash = filesize
        if filesize < 65536 * 2:
            return None
        for _ in range(65536 // bytesize):
            filebuffer = f.read(bytesize)
            (l_value,) = struct.unpack(b'<q', filebuffer)
            filehash += l_value
            filehash = filehash & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number
        f.seek(max(0, filesize - 65536), 0)
        for _ in range(65536 // bytesize):
            filebuffer = f.read(bytesize)
            (l_value,) = struct.unpack(b'<q', filebuffer)
            filehash += l_value
            filehash = filehash & 0xFFFFFFFFFFFFFFFF
    returnedhash = '%016x' % filehash
    return returnedhash


def hash_thesubdb(video_path):
    """Compute a hash using TheSubDB's algorithm

    :param string video_path: path of the video
    :return: the hash
    :rtype: string

    """
    readsize = 64 * 1024
    if os.path.getsize(video_path) < readsize:
        return None
    with open(video_path, 'rb') as f:
        data = f.read(readsize)
        f.seek(-readsize, os.SEEK_END)
        data += f.read(readsize)
    return hashlib.md5(data).hexdigest()
