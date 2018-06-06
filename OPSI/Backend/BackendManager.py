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
BackendManager.

If you want to work with an opsi backend in i.e. a script a
BackendManager instance should be your first choice.
A BackendManager instance does the heavy lifting for you so you don't
need to set up you backends, ACL, multiplexing etc. yourself.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import inspect
import os
import re
import socket
import sys
import types

from OPSI.Backend.Base import (
	Backend, ExtendedBackend, ExtendedConfigDataBackend)
from OPSI.Backend.Depotserver import DepotserverBackend
from OPSI.Backend.HostControl import HostControlBackend
from OPSI.Backend.HostControlSafe import HostControlSafeBackend
from OPSI.Exceptions import *  # this is needed for dynamic extension loading
from OPSI.Logger import Logger
from OPSI.Object import *  # this is needed for dynamic extension loading
from OPSI.Types import *  # this is needed for dynamic extension loading
from OPSI.Util import objectToBeautifiedText, getfqdn  # used in extensions

from .Manager.AccessControl import BackendAccessControl
from .Manager.Dispatcher import BackendDispatcher

__all__ = (
	'BackendManager', 'BackendDispatcher', 'BackendExtender',
	'BackendAccessControl', 'backendManagerFactory'
)

logger = Logger()


class BackendManager(ExtendedBackend):
	"""
	The BackendManager manages the backend and glues together various parts.

	This includes extending the backends, dispatching calls to backends,
	limiting the access	through ACL.
	"""

	def __init__(self, **kwargs):
		"""
		Creating a BackendManager.

		If no configuration is given a default config for accessing the
		local backend as configured through the files in
		/etc/opsi/backendManager/ will be used.

		The constructor takes several parameters and these are all optional.

		:param username: A username for authentication.
		:type username: str
		:param password: The corresponding password.
		:type password: str
		:param backend: A backend to use.
		:param dispatchconfig: A pre-definded dispatch config to use.
		:param dispatchconfigfile: The configuration file for dispatching.
		:type dispatchconfigfile: str
		:param backendconfigdir: The location of backend configurations.
		:type backendconfigdir: str
		:param depotbackend: Allow depot actions?
		:type depotbackend: bool
		:param hostcontrolbackend: Allow controlling hosts?
		:type hostcontrolbackend: bool
		:param hostcontrolsafebackend: Allow controlling hosts (safe variant)?
		:type hostcontrolsafebackend: bool
		:param extensionconfigdir: The directory where backend extensions can be found.
		:type extensionconfigdir: str
		:param extend: Extend the backends?
		:type extend: bool
		:param acl: An access control list (ACL) configuration to use.
		:type acl: [[str, ]]
		:param aclfile: Load the ACL from this file.
		:type aclfile: str
		"""
		self._backend = None
		self._backendConfigDir = None
		self._options = {}
		self._overwrite = True
		self._context = self

		Backend.__init__(self, **kwargs)

		username = None
		password = None
		dispatch = False
		extend = False
		extensionConfigDir = None
		extensionClass = None
		accessControl = False
		depotBackend = False
		hostControlBackend = False
		hostControlSafeBackend = False
		startReactor = True
		loadBackend = None

		if not kwargs:
			kwargs = {
				"dispatchConfigFile": u'/etc/opsi/backendManager/dispatch.conf',
				"backendConfigDir": u'/etc/opsi/backends',
				"extensionConfigDir": u'/etc/opsi/backendManager/extend.d',
				"depotBackend": True,
				"hostControlBackend": True,
				"hostControlSafeBackend": True,
			}
			logger.debug("No config given, using {0!r}".format(kwargs))

		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'username':
				username = value
			elif option == 'password':
				password = value
			elif option == 'backend':
				if isinstance(value, (str, unicode)):
					loadBackend = value
				else:
					self._backend = value
				del kwargs[option]
			elif option == 'backendconfigdir':
				self._backendConfigDir = value
			elif option in ('dispatchconfig', 'dispatchconfigfile') and value:
				dispatch = True
			elif option == 'depotbackend':
				depotBackend = forceBool(value)
			elif option == 'hostcontrolbackend':
				hostControlBackend = forceBool(value)
			elif option == 'hostcontrolsafebackend':
				hostControlSafeBackend = forceBool(value)
			elif option == 'extensionconfigdir' and value:
				extensionConfigDir = value
				extend = True
			elif option == 'extensionclass':
				extensionClass = value
				extend = True
			elif option == 'extend':
				extend = forceBool(value)
			elif option in ('acl', 'aclfile') and value:
				accessControl = True
			elif option == 'startreactor' and value is False:
				startReactor = False

		if loadBackend:
			logger.info(u"* BackendManager is loading backend '%s'" % loadBackend)
			self._backend = self.__loadBackend(loadBackend)
			# self._backend is now a ConfigDataBackend

		if not dispatch and not self._backend:
			raise BackendConfigurationError(u"Neither backend nor dispatch config given")

		if dispatch:
			logger.info(u"* BackendManager is creating BackendDispatcher")
			self._backend = BackendDispatcher(context=self, **kwargs)
			# self._backend is now a BackendDispatcher which is a ConfigDataBackend

		if extend or depotBackend:
			logger.info(u"* BackendManager is creating ExtendedConfigDataBackend")
			# DepotserverBackend/BackendExtender need ExtendedConfigDataBackend backend
			self._backend = ExtendedConfigDataBackend(self._backend)
			# self._backend is now an ExtendedConfigDataBackend

		if depotBackend:
			logger.info(u"* BackendManager is creating DepotserverBackend")
			self._backend = DepotserverBackend(self._backend)

		if hostControlBackend:
			logger.info(u"* BackendManager is creating HostControlBackend")
			try:
				hostControlBackendConfig = self.__loadBackendConfig('hostcontrol')['config']
			except Exception as backendConfigLoadError:
				logger.error(
					"Failed to load configuration for HostControlBackend: {}",
					backendConfigLoadError
				)
				hostControlBackendConfig = {}
			self._backend = HostControlBackend(self._backend, **hostControlBackendConfig)

		if hostControlSafeBackend:
			logger.info(u"* BackendManager is creating HostControlSafeBackend")
			try:
				hostControlSafeBackendConfig = self.__loadBackendConfig('hostcontrol')['config']
			except Exception as backendConfigLoadError:
				logger.error(
					"Failed to load configuration for HostControlSafeBackend: {}",
					backendConfigLoadError
				)
				hostControlSafeBackendConfig = {}
			self._backend = HostControlSafeBackend(self._backend, **hostControlSafeBackendConfig)

		if accessControl:
			logger.info(u"* BackendManager is creating BackendAccessControl")
			self._backend = BackendAccessControl(backend=self._backend, **kwargs)

		if extensionConfigDir or extensionClass:
			logger.info(u"* BackendManager is creating BackendExtender")
			self._backend = BackendExtender(self._backend, **kwargs)

		self._createInstanceMethods()

	def __loadBackendConfig(self, name):
		if not self._backendConfigDir:
			raise BackendConfigurationError(u"Backend config dir not given")
		if not os.path.exists(self._backendConfigDir):
			raise BackendConfigurationError(u"Backend config dir '%s' not found" % self._backendConfigDir)
		if not re.search('^[a-zA-Z0-9-_]+$', name):
			raise ValueError(u"Bad backend config name '%s'" % name)
		name = name.lower()
		backendConfigFile = os.path.join(self._backendConfigDir, '%s.conf' % name)
		if not os.path.exists(backendConfigFile):
			raise BackendConfigurationError(u"Backend config file '%s' not found" % backendConfigFile)

		l = {'socket': socket, 'os': os, 'sys': sys, 'module': '', 'config': {}}
		execfile(backendConfigFile, l)
		return l

	def __loadBackend(self, name):
		config = self.__loadBackendConfig(name)
		backendConfigFile = os.path.join(self._backendConfigDir, '%s.conf' % name)
		if not config['module']:
			raise BackendConfigurationError(u"No module defined in backend config file '%s'" % backendConfigFile)
		if not isinstance(config['config'], dict):
			raise BackendConfigurationError(u"Bad type for config var in backend config file '%s', has to be dict" % backendConfigFile)
		config['config']['name'] = name
		exec(u'from %s import %sBackend' % (config['module'], config['module']))
		return eval(u'%sBackend(**config["config"])' % config['module'])


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


def backendManagerFactory(user, password, dispatchConfigFile, backendConfigDir,
				extensionConfigDir, aclFile, depotId, postpath, context, **kwargs):
	backendManager = None
	if len(postpath) == 2 and postpath[0] == 'backend':
		backendManager = BackendManager(
			backend=postpath[1],
			accessControlContext=context,
			backendConfigDir=backendConfigDir,
			aclFile=aclFile,
			username=user,
			password=password,
			**kwargs
		)
	elif len(postpath) == 2 and postpath[0] == 'extend':
		extendPath = postpath[1]
		if not re.search('^[a-zA-Z0-9\_\-]+$', extendPath):
			raise ValueError(u"Extension config path '%s' refused" % extendPath)
		backendManager = BackendManager(
			dispatchConfigFile=dispatchConfigFile,
			backendConfigDir=backendConfigDir,
			extensionConfigDir=os.path.join(extensionConfigDir, extendPath),
			aclFile=aclFile,
			accessControlContext=context,
			depotBackend=bool(depotId),
			hostControlBackend=True,
			hostControlSafeBackend=True,
			username=user,
			password=password,
			**kwargs
		)
	else:
		backendManager = BackendManager(
			dispatchConfigFile=dispatchConfigFile,
			backendConfigDir=backendConfigDir,
			extensionConfigDir=extensionConfigDir,
			aclFile=aclFile,
			accessControlContext=context,
			depotBackend=bool(depotId),
			hostControlBackend=True,
			hostControlSafeBackend=True,
			username=user,
			password=password,
			**kwargs
		)

	return backendManager
