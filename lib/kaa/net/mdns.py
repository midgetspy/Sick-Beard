# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# mdns.py - Simple Multicast DNS Interface
# -----------------------------------------------------------------------------
# $Id: mdns.py 4070 2009-05-25 15:32:31Z tack $
#
# This module provides a simple interface to multicast DNS (zeroconf) and
# service discovery. Right now it requires Avahi as mdns service. Other
# mdns implementations are not supported yet but should be added later to
# support other platforms like OSX.
#
# TODO: Update service txt record. There is a function UpdateServiceTxt and
# it looks like it does something, but the service browser does not have a
# signal to detect this.
#
# -----------------------------------------------------------------------------
# Copyright 2008-2009 Dirk Meyer
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

# python imports
import logging

# dbus and avahi support
import dbus
import avahi

# kaa imports
import kaa
from kaa.utils import property

# get logging object
log = logging.getLogger('mdns')

class Service(object):
    """
    A service object with all available mdns information
    """
    def __init__(self, interface, protocol, name, domain, host, address, port, local, txt):
        self.interface = interface
        self.protocol = protocol
        self.name = name
        self.domain = domain
        self.host = host
        self.address = address
        self.port = port
        self.local = local
        self.txt = txt

    def __repr__(self):
        return '<mdns.Service %s at %s:%s>' % (self.name, self.address, self.port)


class ServiceList(object):
    """
    An object handling all services of a given type.
    """
    def __init__(self):
        self.signals = kaa.Signals('added', 'removed')
        self._dict = {}

    def _add(self, interface, protocol, name, domain, host, address, port, local, txt):
        s = Service(interface, protocol, name, domain, host, address, port, local, txt)
        self._dict[(interface, protocol, name, domain)] = s
        self.signals['added'].emit(s)

    def _remove(self, interface, protocol, name, domain):
        value = self._dict.pop((interface, protocol, name, domain))
        self.signals['removed'].emit(value)

    @property
    def services(self):
        return self._dict.values()


class Avahi(object):
    """
    Simple multicast DNS service based on Avahi. This service requires avahi
    installed and running as service, dbus python and the gobject mainloop
    running. The mainloop can either run as kaa mainloop (gtk or twisted with
    a gtk based mainloop) or as thread using kaa.gobject_set_threaded().
    """
    def __init__(self):
        self._bus = None
        self._services = {}
        self._provided = {}
        self._nextid = 0
        self._sync_running = False
        self._sync_required = False

    def provide(self, name, type, port, txt):
        """
        Provide a service with the given name and type listening on the given
        port with additional information in the txt record. This function returns
        the id of the service to remove the service later.
        """
        self._nextid += 1
        self._provided[self._nextid] = [
            avahi.IF_UNSPEC,            # interface
            avahi.PROTO_UNSPEC,         # protocol
            0,                          # flags
            name, type,                 # name, service type
            "",                         # domain
            "",                         # host
            dbus.UInt16(port),          # port
            avahi.string_array_to_txt_array([ '%s=%s' % t for t in txt.items() ]),
        ]
        self._sync_required = True
        self._sync()
        return self._nextid

    def remove(self, id):
        """
        Remove a service.
        """
        if id in self._provided:
            self._provided.pop(id)
            self._sync_required = True
            self._sync()

    def get_type(self, service):
        """
        Get a ServiceList object for the given type.
        e.g. get_type('_ssh._tcp')
        """
        if not service in self._services:
            self._services[service] = ServiceList()
            self._service_add_browser(service)
        return self._services[service]

    def _dbus_connect(self):
        """
        Connect to dbus and avahi. This is an internal function that has to be
        called from a function running in the GOBJECT thread.
        """
        self._bus = dbus.SystemBus()
        self._avahi = dbus.Interface(
            self._bus.get_object( avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER ),
            avahi.DBUS_INTERFACE_SERVER )
        self._entrygroup = dbus.Interface(
            self._bus.get_object( avahi.DBUS_NAME, self._avahi.EntryGroupNew()),
            avahi.DBUS_INTERFACE_ENTRY_GROUP)

    @kaa.threaded(kaa.GOBJECT)
    def _sync(self):
        """
        Sync providing service list to avahi. This is an internal function that
        has to be called from a function running in the GOBJECT thread.
        """
        if self._bus is None:
            self._dbus_connect()
        # return if nothing to do
        if self._sync_running or not self._sync_required:
            return
        # dbus callbacks to block sync
        callbacks = dict(
            reply_handler=self._sync_finished,
            error_handler=self._sync_finished
        )
        self._sync_running = True
        self._sync_required = False
        if not self._provided:
            self._entrygroup.Reset(**callbacks)
            return
        self._entrygroup.Reset()
        for service in self._provided.values():
            self._entrygroup.AddService(*service)
        self._entrygroup.Commit(**callbacks)

    def _sync_finished(self, error=None):
        """
        Dbus event when sync is finished. This is an internal function that
        has to be called from a function running in the GOBJECT thread.
        """
        if error:
            # something went wrong
            log.error(error)
        self._sync_running = False
        self._sync()

    @kaa.threaded(kaa.GOBJECT)
    def _service_add_browser(self, service):
        """
        Add a service browser to avahi.
        """
        if self._bus is None:
            self._dbus_connect()
        # fixed values (everything)
        interface = avahi.IF_UNSPEC
        protocol = avahi.PROTO_INET
        domain = ''
        # Call method to create new browser, and get back an object path for it.
        obj = self._avahi.ServiceBrowserNew(
            interface, protocol, service, domain, dbus.UInt32(0))
        # Create browser interface for the new object
        browser = dbus.Interface(self._bus.get_object(avahi.DBUS_NAME, obj),
                                 avahi.DBUS_INTERFACE_SERVICE_BROWSER)
        browser.connect_to_signal('ItemNew', self._service_new)
        browser.connect_to_signal('ItemRemove', self._service_remove)

    @kaa.threaded(kaa.MAINTHREAD)
    def _service_remove(self, interface, protocol, name, type, domain, flags):
        """
        Callback from dbus when a service is removed.
        """
        self._services[type]._remove(
            int(interface), int(protocol), str(name), str(domain))

    def _service_new(self, interface, protocol, name, type, domain, flags):
        """
        Callback from dbus when a new service is available. This function is
        called inside the GOBJECT thread and uses dbus again.
        """
        self._avahi.ResolveService(
            interface, protocol, name, type, domain, avahi.PROTO_INET, dbus.UInt32(0),
            reply_handler=self._service_resolved, error_handler=self._error)

    @kaa.threaded(kaa.MAINTHREAD)
    def _service_resolved(self, interface, protocol, name, type, domain, host,
                          aprotocol, address, port, txt, flags):
        """
        Callback from dbus when a new service is available and resolved.
        """
        txtdict = {}
        for record in avahi.txt_array_to_string_array(txt):
            if record.find('=') > 0:
                k, v = record.split('=', 2)
                txtdict[k] = v
        local = False
        try:
            if flags & avahi.LOOKUP_RESULT_LOCAL:
                local = True
        except dbus.DBusException:
            pass
        self._services[type]._add(
            int(interface), int(protocol), str(name), str(domain),
            str(host), str(address), int(port), local, txtdict
        )

    @kaa.threaded(kaa.MAINTHREAD)
    def _error(self, err):
        log.error(str(err))


# create singleton object
mdns = kaa.utils.Singleton(Avahi)

# create functions to use from the outside
provide = mdns.provide
get_type = mdns.get_type
remove = mdns.remove
