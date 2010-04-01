#
# Copyright (c) 2008 Canonical
#
# Written by James Henstridge <jamesh@canonical.com>
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

"""Django middleware support for the Zope transaction manager.

Adding storm.django.middleware.ZopeTransactionMiddleware to
L{MIDDLEWARE_CLASSES} in the application's settings module will cause a
Zope transaction to be run for each request.
"""

__all__ = ['ZopeTransactionMiddleware']


from django.conf import settings

import transaction


class ZopeTransactionMiddleware(object):
    """Zope Transaction middleware for Django.

    If this is enabled, a Zope transaction will be run to cover each
    request.
    """
    def __init__(self):
        self.commit_safe_methods = getattr(
            settings, 'STORM_COMMIT_SAFE_METHODS', True)

    def process_request(self, request):
        """Begin a transaction on request start.."""
        from django.db import transaction as django_transaction
        django_transaction.enter_transaction_management()
        django_transaction.managed(True)
        transaction.begin()

    def process_exception(self, request, exception):
        """Abort the transaction on errors."""
        from django.db import transaction as django_transaction
        transaction.abort()
        django_transaction.set_clean()
        django_transaction.leave_transaction_management()

    def process_response(self, request, response):
        """Commit or abort the transaction after processing the response.

        On successful completion of the request, the transaction will
        be committed.

        As an exception to this, if the L{STORM_COMMIT_SAFE_METHODS}
        setting is False, and the request used either of the GET and
        HEAD methods, the transaction will be aborted.
        """
        from django.db import transaction as django_transaction
        # If process_exception() has been called, then we'll no longer
        # be in managed transaction mode.
        if django_transaction.is_managed():
            if self.commit_safe_methods or (
                request.method not in ['HEAD', 'GET']):
                transaction.commit()
            else:
                transaction.abort()
            django_transaction.set_clean()
            django_transaction.leave_transaction_management()
        return response
