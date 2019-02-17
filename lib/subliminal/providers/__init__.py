# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import contextlib
import logging
import socket
import babelfish
from pkg_resources import iter_entry_points, EntryPoint
import requests
from ..video import Episode, Movie


logger = logging.getLogger(__name__)


class Provider(object):
    """Base class for providers

    If any configuration is possible for the provider, like credentials, it must take place during instantiation

    :param \*\*kwargs: configuration
    :raise: :class:`~subliminal.exceptions.ProviderConfigurationError` if there is a configuration error

    """
    #: Supported BabelFish languages
    languages = set()

    #: Supported video types
    video_types = (Episode, Movie)

    #: Required hash, if any
    required_hash = None

    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, type, value, traceback):  # @ReservedAssignment
        self.terminate()

    def initialize(self):
        """Initialize the provider

        Must be called when starting to work with the provider. This is the place for network initialization
        or login operations.

        .. note:
            This is called automatically if you use the :keyword:`with` statement


        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable

        """
        pass

    def terminate(self):
        """Terminate the provider

        Must be called when done with the provider. This is the place for network shutdown or logout operations.

        .. note:
            This is called automatically if you use the :keyword:`with` statement

        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable
        """
        pass

    @classmethod
    def check(cls, video):
        """Check if the `video` can be processed

        The video is considered invalid if not an instance of :attr:`video_types` or if the :attr:`required_hash` is
        not present in :attr:`~subliminal.video.Video`'s `hashes` attribute.

        :param video: the video to check
        :type video: :class:`~subliminal.video.Video`
        :return: `True` if the `video` and `languages` are valid, `False` otherwise
        :rtype: bool

        """
        if not isinstance(video, cls.video_types):
            return False
        if cls.required_hash is not None and cls.required_hash not in video.hashes:
            return False
        return True

    def query(self, languages, *args, **kwargs):
        """Query the provider for subtitles

        This method arguments match as much as possible the actual parameters for querying the provider

        :param languages: languages to search for
        :type languages: set of :class:`babelfish.Language`
        :param \*args: other required arguments
        :param \*\*kwargs: other optional arguments
        :return: the subtitles
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`
        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable
        :raise: :class:`~subliminal.exceptions.ProviderError` if something unexpected occured

        """
        raise NotImplementedError

    def list_subtitles(self, video, languages):
        """List subtitles for the `video` with the given `languages`

        This is a proxy for the :meth:`query` method. The parameters passed to the :meth:`query` method may
        vary depending on the amount of information available in the `video`

        :param video: video to list subtitles for
        :type video: :class:`~subliminal.video.Video`
        :param languages: languages to search for
        :type languages: set of :class:`babelfish.Language`
        :return: the subtitles
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`
        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable
        :raise: :class:`~subliminal.exceptions.ProviderError` if something unexpected occured

        """
        raise NotImplementedError

    def download_subtitle(self, subtitle):
        """Download the `subtitle` an fill its :attr:`~subliminal.subtitle.Subtitle.content` attribute with
        subtitle's text

        :param subtitle: subtitle to download
        :type subtitle: :class:`~subliminal.subtitle.Subtitle`
        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable
        :raise: :class:`~subliminal.exceptions.ProviderError` if something unexpected occured

        """
        raise NotImplementedError

    def __repr__(self):
        return '<%s [%r]>' % (self.__class__.__name__, self.video_types)


class ProviderManager(object):
    """Manager for providers behaving like a dict with lazy loading

    Loading is done in this order:

    * Entry point providers
    * Registered providers

    .. attribute:: entry_point

        The entry point where to look for providers

    """
    entry_point = 'subliminal.providers'

    def __init__(self):
        #: Registered providers with entry point syntax
        self.registered_providers = ['addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
                                     'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
                                     'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
                                     'thesubdb = subliminal.providers.thesubdb:TheSubDBProvider',
                                     'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider']

        #: Loaded providers
        self.providers = {}

    @property
    def available_providers(self):
        """Available providers"""
        available_providers = set(self.providers.keys())
        available_providers.update([ep.name for ep in iter_entry_points(self.entry_point)])
        available_providers.update([EntryPoint.parse(c).name for c in self.registered_providers])
        return available_providers

    def __getitem__(self, name):
        """Get a provider, lazy loading it if necessary"""
        if name in self.providers:
            return self.providers[name]
        for ep in iter_entry_points(self.entry_point):
            if ep.name == name:
                self.providers[ep.name] = ep.load()
                return self.providers[ep.name]
        for ep in (EntryPoint.parse(c) for c in self.registered_providers):
            if ep.name == name:
                self.providers[ep.name] = ep.load(require=False)
                return self.providers[ep.name]
        raise KeyError(name)

    def __setitem__(self, name, provider):
        """Load a provider"""
        self.providers[name] = provider

    def __delitem__(self, name):
        """Unload a provider"""
        del self.providers[name]

    def __iter__(self):
        """Iterator over loaded providers"""
        return iter(self.providers)

    def register(self, entry_point):
        """Register a provider

        :param string entry_point: provider to register (entry point syntax)
        :raise: ValueError if already registered

        """
        if entry_point in self.registered_providers:
            raise ValueError('Entry point \'%s\' already registered' % entry_point)
        entry_point_name = EntryPoint.parse(entry_point).name
        if entry_point_name in self.available_providers:
            raise ValueError('An entry point with name \'%s\' already registered' % entry_point_name)
        self.registered_providers.insert(0, entry_point)

    def unregister(self, entry_point):
        """Unregister a provider

        :param string entry_point: provider to unregister (entry point syntax)

        """
        self.registered_providers.remove(entry_point)

    def __contains__(self, name):
        return name in self.providers

provider_manager = ProviderManager()


class ProviderPool(object):
    """A pool of providers with the same API as a single :class:`Provider`

    The :class:`ProviderPool` supports the ``with`` statement to :meth:`terminate` the providers

    :param providers: providers to use, if not all
    :type providers: list of string or None
    :param provider_configs: configuration for providers
    :type provider_configs: dict of provider name => provider constructor kwargs or None

    """
    def __init__(self, providers=None, provider_configs=None):
        self.provider_configs = provider_configs or {}
        self.providers = {p: provider_manager[p] for p in (providers or provider_manager.available_providers)}
        self.initialized_providers = {}
        self.discarded_providers = set()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):  # @ReservedAssignment
        self.terminate()

    def get_initialized_provider(self, name):
        """Get a :class:`Provider` by name, initializing it if necessary

        :param string name: name of the provider
        :return: the initialized provider
        :rtype: :class:`Provider`

        """
        if name in self.initialized_providers:
            return self.initialized_providers[name]
        provider = self.providers[name](**self.provider_configs.get(name, {}))
        provider.initialize()
        self.initialized_providers[name] = provider
        return provider

    def list_subtitles(self, video, languages):
        """List subtitles for `video` with the given `languages`

        :param video: video to list subtitles for
        :type video: :class:`~subliminal.video.Video`
        :param languages: languages of subtitles to search for
        :type languages: set of :class:`babelfish.Language`
        :return: found subtitles
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`

        """
        subtitles = []
        for provider_name, provider_class in self.providers.items():
            if not provider_class.check(video):
                logger.info('Skipping provider %r: not a valid video', provider_name)
                continue
            provider_languages = provider_class.languages & languages - video.subtitle_languages
            if not provider_languages:
                logger.info('Skipping provider %r: no language to search for', provider_name)
                continue
            if provider_name in self.discarded_providers:
                logger.debug('Skipping discarded provider %r', provider_name)
                continue
            try:
                provider = self.get_initialized_provider(provider_name)
                logger.info('Listing subtitles with provider %r and languages %r', provider_name, provider_languages)
                provider_subtitles = provider.list_subtitles(video, provider_languages)
                logger.info('Found %d subtitles', len(provider_subtitles))
                subtitles.extend(provider_subtitles)
            except (requests.exceptions.Timeout, socket.timeout):
                logger.warning('Provider %r timed out, discarding it', provider_name)
                self.discarded_providers.add(provider_name)
            except:
                logger.exception('Unexpected error in provider %r, discarding it', provider_name)
                self.discarded_providers.add(provider_name)
        return subtitles

    def download_subtitle(self, subtitle):
        """Download a subtitle

        :param subtitle: subtitle to download
        :type subtitle: :class:`~subliminal.subtitle.Subtitle`
        :return: ``True`` if the subtitle has been successfully downloaded, ``False`` otherwise
        :rtype: bool

        """
        if subtitle.provider_name in self.discarded_providers:
            logger.debug('Discarded provider %r', subtitle.provider_name)
            return False
        try:
            provider = self.get_initialized_provider(subtitle.provider_name)
            provider.download_subtitle(subtitle)
            if not subtitle.is_valid:
                logger.warning('Invalid subtitle')
                return False
            return True
        except (requests.exceptions.Timeout, socket.timeout):
            logger.warning('Provider %r timed out, discarding it', subtitle.provider_name)
            self.discarded_providers.add(subtitle.provider_name)
        except:
            logger.exception('Unexpected error in provider %r, discarding it', subtitle.provider_name)
            self.discarded_providers.add(subtitle.provider_name)
        return False

    def terminate(self):
        """Terminate all the initialized providers"""
        for (provider_name, provider) in self.initialized_providers.items():
            try:
                provider.terminate()
            except (requests.exceptions.Timeout, socket.timeout):
                logger.warning('Provider %r timed out, unable to terminate', provider_name)
            except:
                logger.exception('Unexpected error in provider %r', provider_name)
