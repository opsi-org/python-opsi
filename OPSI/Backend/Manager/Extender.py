# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2006-2018 uib GmbH <info@uib.de>

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
Backend Extender.

Reads the backend extensions and allows for them to be used like normal
methods in a backend context.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import inspect
import os
import types

from OPSI.Backend.Base import ExtendedBackend
from OPSI.Exceptions import BackendConfigurationError
from OPSI.Exceptions import *  # this is needed for dynamic extension loading
from OPSI.Logger import Logger
from OPSI.Object import *  # this is needed for dynamic extension loading
from OPSI.Types import *  # this is needed for dynamic extension loading

from .AccessControl import BackendAccessControl
from .Dispatcher import BackendDispatcher

__all__ = ('BackendExtender', )

logger = Logger()


class BackendExtender(ExtendedBackend):
    def __init__(self, backend, **kwargs):
        if not isinstance(backend, ExtendedBackend) and not isinstance(backend, BackendDispatcher):
            if not isinstance(backend, BackendAccessControl) or (not isinstance(backend._backend, ExtendedBackend) and not isinstance(backend._backend, BackendDispatcher)):
                raise TypeError("BackendExtender needs instance of ExtendedBackend or BackendDispatcher as backend, got %s" % backend.__class__.__name__)

        ExtendedBackend.__init__(self, backend, overwrite=kwargs.get('overwrite', True))

        self._extensionConfigDir = None
        self._extensionClass = None

        for (option, value) in kwargs.items():
            option = option.lower()
            if option == 'extensionconfigdir':
                self._extensionConfigDir = value
            elif option == 'extensionclass':
                self._extensionClass = value

        self.__createExtensions()

    def __createExtensions(self):
        if self._extensionClass:
            for methodName, functionRef in inspect.getmembers(self._extensionClass, inspect.ismethod):
                if methodName.startswith('_'):
                    continue
                logger.debug2(u"Extending {0} with instancemethod: {1!r}", self._backend.__class__.__name__, methodName)
                new_function = types.FunctionType(functionRef.func_code, functionRef.func_globals, functionRef.func_code.co_name)
                new_method = types.MethodType(new_function, self)
                setattr(self, methodName, new_method)

        if self._extensionConfigDir:
            if not os.path.exists(self._extensionConfigDir):
                logger.error(u"No extensions loaded: extension directory {0!r} does not exist".format(self._extensionConfigDir))
                return

            try:
                confFiles = (
                    os.path.join(self._extensionConfigDir, filename)
                    for filename in sorted(os.listdir(self._extensionConfigDir))
                    if filename.endswith('.conf')
                )

                for confFile in confFiles:
                    try:
                        logger.info(u"Reading config file '%s'" % confFile)
                        execfile(confFile)
                    except Exception as execError:
                        logger.logException(execError)
                        raise RuntimeError(u"Error reading file {0!r}: {1}".format(confFile, execError))

                    for key, val in locals().items():
                        if isinstance(val, types.FunctionType):   # TODO: find a better way
                            logger.debug2(u"Extending %s with instancemethod: '%s'" % (self._backend.__class__.__name__, key))
                            setattr(self, key, types.MethodType(val, self))
            except Exception as error:
                raise BackendConfigurationError(u"Failed to read extensions from '%s': %s" % (self._extensionConfigDir, error))
