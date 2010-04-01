"""ZStorm integrates Storm with Zope 3.

@var global_zstorm: A global L{ZStorm} instance.  It used the
    L{IZStorm} utility registered in C{configure.zcml}.
"""

#
# Copyright (c) 2006-2009 Canonical
#
# Written by Gustavo Niemeyer <gustavo@niemeyer.net>
#
# This file is part of Storm Object Relational Mapper.
#
# Storm is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# Storm is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import threading
import weakref

from zope.interface import implements

import transaction
from transaction.interfaces import IDataManager, ISynchronizer
try:
    from transaction.interfaces import TransactionFailedError
except ImportError:
    from ZODB.POSException import TransactionFailedError

from storm.zope.interfaces import IZStorm, ZStormError
from storm.database import create_database
from storm.store import Store


class ZStorm(object):
    """A utility which integrates Storm with Zope.

    Typically, applications will register stores using ZCML similar
    to::

      <store name='main' uri='sqlite:' />

    Application code can then acquire the store by name using code
    similar to::

      from zope.component import getUtility
      from storm.zope.interfaces import IZStorm

      store = getUtility(IZStorm).get('main')
    """

    implements(IZStorm)

    transaction_manager = transaction.manager

    _databases = {}

    def __init__(self):
        self._local = threading.local()
        self._default_databases = {}
        self._default_uris = {}

    def _reset(self):
        for name, store in list(self.iterstores()):
            self.remove(store)
            store.close()
        self._local = threading.local()
        self._databases.clear()
        self._default_databases.clear()
        self._default_uris.clear()

    @property
    def _stores(self):
        try:
            return self._local.stores
        except AttributeError:
            stores = weakref.WeakValueDictionary()
            return self._local.__dict__.setdefault("stores", stores)

    @property
    def _named(self):
        try:
            return self._local.named
        except AttributeError:
            return self._local.__dict__.setdefault("named", {})

    @property
    def _name_index(self):
        try:
            return self._local.name_index
        except AttributeError:
            return self._local.__dict__.setdefault(
                "name_index", weakref.WeakKeyDictionary())

    def _get_database(self, uri):
        database = self._databases.get(uri)
        if database is None:
            return self._databases.setdefault(uri, create_database(uri))
        return database

    def set_default_uri(self, name, default_uri):
        """Set C{default_uri} as the default URI for stores called C{name}."""
        self._default_databases[name] = self._get_database(default_uri)
        self._default_uris[name] = default_uri

    def create(self, name, uri=None):
        """Create a new store called C{name}.

        @param uri: Optionally, the URI to use.
        @raises ZStormError: Raised if C{uri} is None and no default
            URI exists for C{name}.  Also raised if a store with
            C{name} already exists.
        """
        if uri is None:
            database = self._default_databases.get(name)
            if database is None:
                raise ZStormError("Store named '%s' not found" % name)
        else:
            database = self._get_database(uri)

        if name is not None and self._named.get(name) is not None:
            raise ZStormError("Store named '%s' already exists" % name)

        store = Store(database)
        store._register_for_txn = True
        store._event.hook(
            "register-transaction", register_store_with_transaction,
            self.transaction_manager)

        self._stores[id(store)] = store
        if name is not None:
            self._named[name] = store
        self._name_index[store] = name

        return store

    def get(self, name, default_uri=None):
        """Get the store called C{name}, creating it first if necessary.

        @param default_uri: Optionally, the URI to use to create a
           store called C{name} when one doesn't already exist.
        @raises ZStormError: Raised if C{uri} is None and no default
            URI exists for C{name}.
        """
        store = self._named.get(name)
        if not store:
            return self.create(name, default_uri)
        return store

    def remove(self, store):
        """Remove the given store from ZStorm.

        This removes any management of the store from ZStorm.

        Notice that if the store was used inside the current
        transaction, it's probably joined the transaction system as
        a resource already, and thus it will commit/rollback when
        the transaction system requests so.

        This method will unlink the *synchronizer* from the transaction
        system, so that once the current transaction is over it won't
        link back to it in future transactions.
        """
        del self._stores[id(store)]
        name = self._name_index[store]
        del self._name_index[store]
        if name in self._named:
            del self._named[name]

        # Make sure the store isn't hooked up to future transactions.
        store._register_for_txn = False
        store._event.unhook(
            "register-transaction", register_store_with_transaction,
            self.transaction_manager)

    def iterstores(self):
        """Iterate C{name, store} 2-tuples."""
        # items is explicitly used here, instead of iteritems, to
        # avoid the problem where a store is deallocated during
        # iteration causing RuntimeError: dictionary changed size
        # during iteration.
        for store, name in self._name_index.items():
            yield name, store

    def get_name(self, store):
        """Returns the name for C{store} or None if one isn't available."""
        return self._name_index.get(store)

    def get_default_uris(self):
        """
        Return a list of name, uri tuples that are named as the default
        databases for those names.
        """
        return self._default_uris.copy()


def register_store_with_transaction(store, transaction_manager):
    data_manager = StoreDataManager(store, transaction_manager)
    transaction_manager.get().join(data_manager)

    # Unhook the event handler.  It will be rehooked for the next transaction.
    return False


class StoreDataManager(object):
    """An L{IDataManager} implementation for C{ZStorm}."""

    implements(IDataManager)

    def __init__(self, store, transaction_manager):
        self._store = store
        self.transaction_manager = transaction_manager

    def abort(self, txn):
        try:
            self._store.rollback()
        finally:
            if self._store._register_for_txn:
                self._store._event.hook(
                    "register-transaction", register_store_with_transaction,
                    self.transaction_manager)

    def tpc_begin(self, txn):
        # Zope's transaction system will call tpc_begin() on all
        # managers before calling commit, so flushing here may help
        # in cases where there are two stores with changes, and one
        # of them will fail.  In such cases, flushing earlier will
        # ensure that both transactions will be rolled back, instead
        # of one committed and one rolled back.
        self._store.flush()

    def commit(self, txn):
        try:
            self._store.commit()
        finally:
            if self._store._register_for_txn:
                self._store._event.hook(
                    "register-transaction", register_store_with_transaction,
                    self.transaction_manager)

    def tpc_vote(self, txn):
        pass

    def tpc_finish(self, txn):
        pass

    def tpc_abort(self, txn):
        pass

    def sortKey(self):
        return "store_%d" % id(self)


global_zstorm = ZStorm()

try:
    from zope.testing.cleanup import addCleanUp
except ImportError:
    # We don't have zope.testing installed.
    pass
else:
    addCleanUp(global_zstorm._reset)
    del addCleanUp
