import itertools


class Cache(object):
    """Prevents recently used objects from being deallocated.

    This prevents recently used objects from being deallocated by Python
    even if the user isn't holding any strong references to it.  It does
    that by holding strong references to the objects referenced by the
    last C{N} C{obj_info}s added to it (where C{N} is the cache size).
    """

    def __init__(self, size=1000):
        self._size = size
        self._cache = {} # {obj_info: obj, ...}
        self._order = [] # [obj_info, ...]

    def clear(self):
        """Clear the entire cache at once."""
        self._cache.clear()
        del self._order[:]

    def add(self, obj_info):
        """Add C{obj_info} as the most recent entry in the cache.

        If the C{obj_info} is already in the cache, it remains in the
        cache and has its order changed to become the most recent entry
        (IOW, will be the last to leave).
        """
        if self._size != 0:
            if obj_info in self._cache:
                self._order.remove(obj_info)
            else:
                self._cache[obj_info] = obj_info.get_obj()
            self._order.insert(0, obj_info)
            if len(self._cache) > self._size:
                del self._cache[self._order.pop()]

    def remove(self, obj_info):
        """Remove C{obj_info} from the cache, if present.

        @return: True if C{obj_info} was cached, False otherwise.
        """
        if obj_info in self._cache:
            self._order.remove(obj_info)
            del self._cache[obj_info]
            return True
        return False

    def set_size(self, size):
        """Set the maximum number of objects that may be held in this cache.

        If the size is reduced, older C{obj_info}s may be dropped from
        the cache to respect the new size.
        """
        if size == 0:
            self.clear()
        else:
            # Remove all entries above the new size.
            while len(self._cache) > size:
                del self._cache[self._order.pop()]
        self._size = size

    def get_cached(self):
        """Return an ordered list of the currently cached C{obj_info}s.

        The most recently added objects come first in the list.
        """
        return list(self._order)


class GenerationalCache(object):
    """Generational replacement for Storm's LRU cache.

    This cache approximates LRU without keeping exact track.  Instead,
    it keeps a primary dict of "recently used" objects plus a similar,
    secondary dict of objects used in a previous timeframe.

    When the "most recently used" dict reaches its size limit, it is
    demoted to secondary dict and a fresh primary dict is set up.  The
    previous secondary dict is evicted in its entirety.

    Use this to replace the LRU cache for sizes where LRU tracking
    overhead becomes too large (e.g. 100,000 objects) or the
    `StupidCache` when it eats up too much memory.
    """

    def __init__(self, size=1000):
        """Create a generational cache with the given size limit.

        The size limit applies not to the overall cache, but to the
        primary one only.  When this reaches the size limit, the real
        number of cached objects will be somewhere between size and
        2*size depending on how much overlap there is between the
        primary and secondary caches.
        """
        self._size = size
        self._new_cache = {}
        self._old_cache = {}

    def clear(self):
        """See `storm.store.Cache.clear`.

        Clears both the primary and the secondary caches.
        """
        self._new_cache.clear()
        self._old_cache.clear()

    def _bump_generation(self):
        """Start a new generation of the cache.

        The primary generation becomes the secondary one, and the old
        secondary generation is evicted.

        Kids at home: do not try this for yourself.  We are trained
        professionals working with specially-bred generations.  This
        would not be an appropriate way of treating older generations
        of actual people.
        """
        self._old_cache, self._new_cache = self._new_cache, self._old_cache
        self._new_cache.clear()

    def add(self, obj_info):
        """See `storm.store.Cache.add`."""
        if self._size != 0 and obj_info not in self._new_cache:
            if len(self._new_cache) >= self._size:
                self._bump_generation()
            self._new_cache[obj_info] = obj_info.get_obj()

    def remove(self, obj_info):
        """See `storm.store.Cache.remove`."""
        in_new_cache = self._new_cache.pop(obj_info, None) is not None
        in_old_cache = self._old_cache.pop(obj_info, None) is not None
        return in_new_cache or in_old_cache

    def set_size(self, size):
        """See `storm.store.Cache.set_size`.

        After calling this, the cache may still contain more than `size`
        objects, but no more than twice that number.
        """
        self._size = size
        cache = itertools.islice(itertools.chain(self._new_cache.iteritems(),
                                                 self._old_cache.iteritems()),
                                 0, size)
        self._new_cache = dict(cache)
        self._old_cache.clear()

    def get_cached(self):
        """See `storm.store.Cache.get_cached`.

        The result is a loosely-ordered list.  Any object in the primary
        generation comes before any object that is only in the secondary
        generation, but objects within a generation are not ordered and
        there is no indication of the boundary between the two.

        Objects that are in both the primary and the secondary
        generation are listed only as part of the primary generation.
        """
        cached = self._new_cache.copy()
        cached.update(self._old_cache)
        return list(cached)
