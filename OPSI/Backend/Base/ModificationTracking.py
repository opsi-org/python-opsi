# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2013-2018 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Basic backend.

This holds the basic backend classes.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Logger import Logger
from OPSI.Util import (
    blowfishEncrypt, blowfishDecrypt, compareVersions,
    getfqdn, removeUnit, timestamp)


__all__ = (
    'ModificationTrackingBackend', 'BackendModificationListener'
)

logger = Logger()


class ModificationTrackingBackend(ExtendedBackend):

    def __init__(self, backend, overwrite=True):
        ExtendedBackend.__init__(self, backend, overwrite=overwrite)
        self._createInstanceMethods()
        self._backendChangeListeners = []

    def addBackendChangeListener(self, backendChangeListener):
        if backendChangeListener in self._backendChangeListeners:
            return
        self._backendChangeListeners.append(backendChangeListener)

    def removeBackendChangeListener(self, backendChangeListener):
        if backendChangeListener not in self._backendChangeListeners:
            return
        self._backendChangeListeners.remove(backendChangeListener)

    def _fireEvent(self, event, *args):
        for bcl in self._backendChangeListeners:
            try:
                meth = getattr(bcl, event)
                meth(self, *args)
            except Exception as e:
                logger.error(e)

    def _executeMethod(self, methodName, **kwargs):
        logger.debug(u"ModificationTrackingBackend {0}: executing {1!r} on backend {2}".format(self, methodName, self._backend))
        meth = getattr(self._backend, methodName)
        result = meth(**kwargs)
        action = None
        if '_' in methodName:
            action = methodName.split('_', 1)[1]

        if action in ('insertObject', 'updateObject', 'deleteObjects'):
            if action == 'insertObject':
                self._fireEvent('objectInserted', kwargs.values()[0])
            elif action == 'updateObject':
                self._fireEvent('objectUpdated', kwargs.values()[0])
            elif action == 'deleteObjects':
                self._fireEvent('objectsDeleted', kwargs.values()[0])
            self._fireEvent('backendModified')

        return result


class BackendModificationListener(object):
    def objectInserted(self, backend, obj):
        # Should return immediately!
        pass

    def objectUpdated(self, backend, obj):
        # Should return immediately!
        pass

    def objectsDeleted(self, backend, objs):
        # Should return immediately!
        pass

    def backendModified(self, backend):
        # Should return immediately!
        pass
