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
Dispatching backend calls to multiple backends.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import importlib
import inspect
import os
import re
import types

from OPSI.Backend.Base import (
	Backend, ConfigDataBackend, ExtendedBackend, getArgAndCallString)
from OPSI.Exceptions import BackendConfigurationError
from OPSI.Logger import Logger
from OPSI.Types import forceList
from OPSI.Util.File.Opsi import BackendDispatchConfigFile

from .AccessControl import BackendAccessControl
from .Config import loadBackendConfig

__all__ = ('BackendDispatcher', )

logger = Logger()


class BackendDispatcher(Backend):
	def __init__(self, **kwargs):
		Backend.__init__(self, **kwargs)

		self._dispatchConfigFile = None
		self._dispatchConfig = []
		self._dispatchIgnoreModules = []
		self._backendConfigDir = None
		self._backends = {}
		self._options = {}
		self._context = self

		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'dispatchconfig':
				self._dispatchConfig = value
			elif option == 'dispatchconfigfile':
				self._dispatchConfigFile = value
			elif option == 'dispatchignoremodules' and value:
				self._dispatchIgnoreModules = forceList(value)
			elif option == 'backendconfigdir':
				self._backendConfigDir = value
			elif option == 'context':
				self._context = value

		if self._dispatchConfigFile:
			logger.info(u"Loading dispatch config file '%s'" % self._dispatchConfigFile)
			self.__loadDispatchConfig()

		if not self._dispatchConfig:
			raise BackendConfigurationError(u"Dispatcher not configured")

		self.__loadBackends()
		self._createInstanceMethods()

	def __repr__(self):
		additionalInformation = []
		try:
			if self._dispatchIgnoreModules:
				additionalInformation.append('dispatchIgnoreModules={0!r}'.format(self._dispatchIgnoreModules))

			if self._dispatchConfigFile:
				additionalInformation.append('dispatchConfigFile={0!r}'.format(self._dispatchConfigFile))
			elif self._dispatchConfig:
				additionalInformation.append('dispatchConfig={0!r}'.format(self._dispatchConfig))

			if self._context != self:
				additionalInformation.append('context={0!r}'.format(self._context))
		except AttributeError:
			# Can happen during initialisation
			pass

		return '<{0}({1})>'.format(self.__class__.__name__, ', '.join(additionalInformation))

	def __loadDispatchConfig(self):
		if not self._dispatchConfigFile:
			raise BackendConfigurationError(u"No dispatch config file defined")

		if not os.path.exists(self._dispatchConfigFile):
			raise BackendConfigurationError(u"Dispatch config file '%s' not found" % self._dispatchConfigFile)

		try:
			self._dispatchConfig = BackendDispatchConfigFile(self._dispatchConfigFile).parse()
			logger.debug(u"Read dispatch config from file {0!r}: {1!r}", self._dispatchConfigFile, self._dispatchConfig)
		except Exception as e:
			raise BackendConfigurationError(u"Failed to load dispatch config file '%s': %s" % (self._dispatchConfigFile, e))

	def __loadBackends(self):
		if not self._backendConfigDir:
			raise BackendConfigurationError(u"Backend config dir not given")

		if not os.path.exists(self._backendConfigDir):
			raise BackendConfigurationError(u"Backend config dir '%s' not found" % self._backendConfigDir)

		collectedBackends = set()
		for pattern, backends in self._dispatchConfig:
			for backend in backends:
				if not backend:
					raise BackendConfigurationError(u"Bad dispatcher config: {0!r} has empty target backend: {1!r}".format(pattern, backends))

				collectedBackends.add(backend)

		for backend in collectedBackends:
			self._backends[backend] = {}
			backendConfigFile = os.path.join(self._backendConfigDir, '%s.conf' % backend)
			logger.info(u"Loading backend config '%s'" % backendConfigFile)
			l = loadBackendConfig(backendConfigFile)
			if not l['module']:
				raise BackendConfigurationError(u"No module defined in backend config file '%s'" % backendConfigFile)
			if l['module'] in self._dispatchIgnoreModules:
				logger.notice(u"Ignoring module '%s', backend '%s'" % (l['module'], backend))
				del self._backends[backend]
				continue
			if not isinstance(l['config'], dict):
				raise BackendConfigurationError(u"Bad type for config var in backend config file '%s', has to be dict" % backendConfigFile)
			backendInstance = None
			l["config"]["context"] = self
			moduleName = 'OPSI.Backend.%s' % l['module']
			backendClassName = "%sBackend" % l['module']
			b = importlib.import_module(moduleName)
			self._backends[backend]["instance"] = getattr(b, backendClassName)(**l['config'])

	def _createInstanceMethods(self):
		logger.debug(u"BackendDispatcher is creating instance methods")
		for Class in (ConfigDataBackend, ):  # Also apply to ExtendedConfigDataBackend?
			for methodName, functionRef in inspect.getmembers(Class, inspect.ismethod):
				if methodName.startswith('_'):
					# Not a public method
					continue
				logger.debug2(u"Found public %s method '%s'" % (Class.__name__, methodName))

				if hasattr(self, methodName):
					logger.debug(u"{0}: skipping already present method {1}", self.__class__.__name__, methodName)
					continue

				methodBackends = []
				for regex, backends in self._dispatchConfig:
					if not re.search(regex, methodName):
						continue

					for backend in forceList(backends):
						if backend not in self._backends:
							logger.debug(u"Ignoring backend {0!r}: backend not available", backend)
							continue
						methodBackends.append(backend)
					logger.debug(u"{0!r} matches method {1!r}, dispatching to backends: {2}", regex, methodName, u', '.join(methodBackends))
					break

				if not methodBackends:
					continue

				argString, callString = getArgAndCallString(functionRef)

				exec(u'def %s(self, %s): return self._dispatchMethod(%s, "%s", %s)' % (methodName, argString, methodBackends, methodName, callString))
				setattr(self, methodName, types.MethodType(eval(methodName), self))

	def _dispatchMethod(self, methodBackends, methodName, **kwargs):
		logger.debug(u"Dispatching method {0!r} to backends: {1}", methodName, methodBackends)
		result = None

		for methodBackend in methodBackends:
			meth = getattr(self._backends[methodBackend]["instance"], methodName)
			res = meth(**kwargs)

			# TODO: handling of generators?
			if isinstance(result, list) and isinstance(res, list):
				result.extend(res)
			elif isinstance(result, dict) and isinstance(res, dict):
				result.update(res)
			elif isinstance(result, set) and isinstance(res, set):
				result = result.union(res)
			elif isinstance(result, tuple) and isinstance(res, tuple):
				result = result + res
			elif res is not None:
				result = res

		logger.debug2(u"Finished dispatching method {0!r}", methodName)
		return result

	def backend_setOptions(self, options):
		Backend.backend_setOptions(self, options)
		for be in self._backends.values():
			be['instance'].backend_setOptions(options)

	def backend_getOptions(self):
		options = Backend.backend_getOptions(self)
		for be in self._backends.values():
			options.update(be['instance'].backend_getOptions())
		return options

	def backend_exit(self):
		for be in self._backends.values():
			be['instance'].backend_exit()

	def dispatcher_getConfig(self):
		return self._dispatchConfig

	def dispatcher_getBackendNames(self):
		return self._backends.keys()


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
						with open(confFile) as confFileHandle:
							exec(confFileHandle.read())
					except Exception as execError:
						logger.logException(execError)
						raise RuntimeError(u"Error reading file {0!r}: {1}".format(confFile, execError))

					for key, val in locals().items():
						if isinstance(val, types.FunctionType):   # TODO: find a better way
							logger.debug2(u"Extending %s with instancemethod: '%s'" % (self._backend.__class__.__name__, key))
							setattr(self, key, types.MethodType(val, self))
			except Exception as error:
				raise BackendConfigurationError(u"Failed to read extensions from '%s': %s" % (self._extensionConfigDir, error))
