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

from __future__ import absolute_import

import base64
import codecs
import inspect
import re
import time
from hashlib import md5
from twisted.conch.ssh import keys

from OPSI import __version__ as LIBRARY_VERSION
from OPSI.Logger import Logger
from OPSI.Object import *  # this is needed for dynamic loading
from OPSI.Types import (forceDict, forceFilename, forceList, forceUnicode,
    forceUnicodeList)
from OPSI.Util import compareVersions

__all__ = ('describeInterface', 'Backend')

OPSI_MODULES_FILE = u'/etc/opsi/modules'

logger = Logger()


def describeInterface(instance):
    """
    Describes what public methods are available and the signatures they use.

    These methods are represented as a dict with the following keys: \
    *name*, *params*, *args*, *varargs*, *keywords*, *defaults*.

    :returntype: [{},]
    """
    methods = {}
    for methodName, function in inspect.getmembers(instance, inspect.ismethod):
        if methodName.startswith('_'):
            # protected / private
            continue

        args, varargs, keywords, defaults = inspect.getargspec(function)
        params = [arg for arg in args if arg != 'self']

        if defaults is not None:
            offset = len(params) - len(defaults)
            for i in xrange(len(defaults)):
                index = offset + i
                params[index] = '*{0}'.format(params[index])

        for index, element in enumerate((varargs, keywords), start=1):
            if element:
                stars = '*' * index
                params.extend(['{0}{1}'.format(stars, arg) for arg in forceList(element)])

        logger.debug2(u"{0} interface method: name {1!r}, params {2}", instance.__class__.__name__, methodName, params)
        methods[methodName] = {
            'name': methodName,
            'params': params,
            'args': args,
            'varargs': varargs,
            'keywords': keywords,
            'defaults': defaults
        }

    return [methods[name] for name in sorted(methods.keys())]


class Backend:
    """
    Base backend.
    """

    matchCache = {}

    def __init__(self, **kwargs):
        """
        Constructor that only accepts keyword arguments.

        :param name: Name of the backend
        :param username: Username to use (if required)
        :param password: Password to use (if required)
        :param context: Context backend. Calling backend methods from \
other backend methods is done by using the context backend. \
This defaults to ``self``.
        """
        self._name = None
        self._username = None
        self._password = None
        self._context = self
        self._opsiVersion = LIBRARY_VERSION

        self._opsiModulesFile = OPSI_MODULES_FILE

        for (option, value) in kwargs.items():
            option = option.lower()
            if option == 'name':
                self._name = value
            elif option == 'username':
                self._username = value
            elif option == 'password':
                self._password = value
            elif option == 'context':
                self._context = value
                logger.info(u"Backend context was set to %s" % self._context)
            elif option == 'opsimodulesfile':
                self._opsiModulesFile = forceFilename(value)
        self._options = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.backend_exit()

    def _setContext(self, context):
        """Setting the context backend."""
        self._context = context

    def _getContext(self):
        """Getting the context backend."""
        return self._context

    def _objectHashMatches(self, objHash, **filter):
        """
        Checks if the opsi object hash matches the filter.

        :rtype: bool
        """
        for attribute, value in objHash.iteritems():
            if not filter.get(attribute):
                continue
            matched = False

            try:
                logger.debug(
                    u"Testing match of filter {0!r} of attribute {1!r} with "
                    u"value {2!r}", filter[attribute], attribute, value
                )
                filterValues = forceUnicodeList(filter[attribute])
                if forceUnicodeList(value) == filterValues or forceUnicode(value) in filterValues:
                    matched = True
                else:
                    for filterValue in filterValues:
                        if attribute == 'type':
                            match = False
                            Class = eval(filterValue)
                            for subClass in Class.subClasses:
                                if subClass == value:
                                    matched = True
                                    break

                            continue

                        if isinstance(value, list):
                            if filterValue in value:
                                matched = True
                                break

                            continue
                        elif value is None or isinstance(value, bool):
                            continue
                        elif isinstance(value, (float, long, int)) or re.search('^\s*([>=<]+)\s*([\d\.]+)', forceUnicode(filterValue)):
                            operator = '=='
                            v = forceUnicode(filterValue)
                            match = re.search('^\s*([>=<]+)\s*([\d\.]+)', filterValue)
                            if match:
                                operator = match.group(1)  # pylint: disable=maybe-no-member
                                v = match.group(2)  # pylint: disable=maybe-no-member

                            try:
                                matched = compareVersions(value, operator, v)
                                if matched:
                                    break
                            except Exception:
                                pass

                            continue

                        if '*' in filterValue and re.search('^%s$' % filterValue.replace('*', '.*'), value):
                            matched = True
                            break

                if matched:
                    logger.debug(
                        u"Value {0!r} matched filter {1!r}, attribute {2!r}",
                        value, filter[attribute], attribute
                    )
                else:
                    # No match, we can stop further checks.
                    return False
            except Exception as err:
                raise BackendError(
                    u"Testing match of filter {0!r} of attribute {1!r} with "
                    u"value {2!r} failed: {error}".format(
                        filter[attribute], attribute, value, error=err
                    )
                )

        return True

    def backend_setOptions(self, options):
        """
        Change the behaviour of the backend.

        :param options: The options to set. Unknown keywords will be ignored.
        :type options: dict
        """
        options = forceDict(options)
        for (key, value) in options.items():
            if key not in self._options:
                continue

            if type(value) != type(self._options[key]):
                logger.debug(u"Wrong type {0} for option {1}, expecting type {2}", type(value), key, type(self._options[key]))
                continue

            self._options[key] = value

    def backend_getOptions(self):
        """
        Get the current backend options.

        :rtype: dict
        """
        return self._options

    def backend_getInterface(self):
        """
        Returns what public methods are available and the signatures they use.

        These methods are represented as a dict with the following keys: \
        *name*, *params*, *args*, *varargs*, *keywords*, *defaults*.


        :returntype: [{},]
        """
        return describeInterface(self)

    def backend_info(self):
        """
        Get info about the used opsi version and the licensed modules.

        :rtype: dict
        """
        modules = {'valid': False}
        helpermodules = {}

        try:
            with codecs.open(self._opsiModulesFile, 'r', 'utf-8') as modulesFile:
                for line in modulesFile:
                    line = line.strip()
                    if '=' not in line:
                        logger.error(u"Found bad line '%s' in modules file '%s'" % (line, self._opsiModulesFile))
                        continue
                    (module, state) = line.split('=', 1)
                    module = module.strip().lower()
                    state = state.strip()
                    if module in ('signature', 'customer', 'expires'):
                        modules[module] = state
                        continue
                    state = state.lower()
                    if state not in ('yes', 'no'):
                        try:
                            helpermodules[module] = state
                            state = int(state)
                        except ValueError:
                            logger.error(u"Found bad line '%s' in modules file '%s'" % (line, self._opsiModulesFile))
                            continue
                    if isinstance(state, int):
                        modules[module] = (state > 0)
                    else:
                        modules[module] = (state == 'yes')

            if not modules.get('signature'):
                modules = {'valid': False}
                raise ValueError(u"Signature not found")
            if not modules.get('customer'):
                modules = {'valid': False}
                raise ValueError(u"Customer not found")
            if (modules.get('expires', '') != 'never') and (time.mktime(time.strptime(modules.get('expires', '2000-01-01'), "%Y-%m-%d")) - time.time() <= 0):
                modules = {'valid': False}
                raise ValueError(u"Signature expired")
            publicKey = keys.Key.fromString(data=base64.decodestring('AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP')).keyObject
            data = u''
            mks = modules.keys()
            mks.sort()
            for module in mks:
                if module in ('valid', 'signature'):
                    continue

                if module in helpermodules:
                    val = helpermodules[module]
                else:
                    val = modules[module]
                    if val is False:
                        val = 'no'
                    elif val is True:
                        val = 'yes'

                data += u'%s = %s\r\n' % (module.lower().strip(), val)
            modules['valid'] = bool(publicKey.verify(md5(data).digest(), [long(modules['signature'])]))
        except Exception as error:
            logger.info(u"Failed to read opsi modules file '%s': %s" % (self._opsiModulesFile, error))

        return {
            "opsiVersion": self._opsiVersion,
            "modules": modules,
            "realmodules": helpermodules
        }

    def backend_exit(self):
        """
        Exit the backend.

        This method should be used to close connections or clean up \
        used resources.
        """
        pass

    def __repr__(self):
        if self._name:
            return u'<{0}(name={1!r})>'.format(self.__class__.__name__, self._name)
        else:
            return u'<{0}()>'.format(self.__class__.__name__)
