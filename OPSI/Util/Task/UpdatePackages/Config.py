# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Configuration.

Attention: socket.defaulttimeout may be changed per config file setting.
"""

import os
import os.path
import re
import socket

from .Exceptions import (ConfigurationError, MissingConfigurationValueError,
	RequiringBackendError)
from .Repository import ProductRepositoryInfo

from OPSI import __version__
from OPSI.Logger import Logger
from OPSI.Util.File import IniFile
from OPSI.Types import (
	forceBool, forceEmailAddress, forceFilename, forceHostAddress,
	forceHostId, forceInt, forceProductId, forceUnicode, forceUrl)

__all__ = ('DEFAULT_CONFIG', 'DEFAULT_USER_AGENT', 'ConfigurationParser')

DEFAULT_USER_AGENT = 'opsi-package-updater/%s' % __version__
DEFAULT_CONFIG = {
	"userAgent": DEFAULT_USER_AGENT,
	"packageDir": '/var/lib/opsi/products',
	"configFile": '/etc/opsi/opsi-package-updater.conf',
	"repositoryConfigDir": '/etc/opsi/package-updater.repos.d',
	"notification": False,
	"smtphost": u'localhost',
	"smtpport": 25,
	"smtpuser": None,
	"smtppassword": None,
	"subject": u'opsi-package-updater',
	"use_starttls": False,
	"sender": u'opsi@localhost',
	"receivers": [],
	"wolAction": False,
	"wolActionExcludeProductIds": [],
	"wolShutdownWanted": False,
	"wolStartGap": 0,
	"installationWindowStartTime": None,
	"installationWindowEndTime": None,
	"installationWindowExceptions": None,
	"repositories": [],
	"repositoryName": None,
	"forceRepositoryActivation": False,
	"installAllAvailable": False,
	"zsyncCommand": None,
	"processProductIds": None,
	"forceChecksumCalculation": False,
	"forceDownload": False,
	"proxy": None,
	"ignoreErrors" : False
}

logger = Logger()


def getRepoConfigs(repoDir):
	try:
		for entry in os.listdir(repoDir):
			filePath = os.path.join(repoDir, entry)
			if entry.endswith('.repo') and os.path.isfile(filePath):
				yield filePath
	except OSError as oserr:
		logger.warning("Problem listing {0}: {1}".format(repoDir, oserr))


def splitAndStrip(string, sep):
	for singleValue in string.split(sep):
		singleValue = singleValue.strip()
		if singleValue:
			yield singleValue


class ConfigurationParser:

	TIME_REGEX = re.compile(r'^\d{1,2}:\d{1,2}$')

	def __init__(self, configFile, backend=None, depotId=None, depotKey=None):
		self.configFile = configFile
		self.backend = backend
		self.depotId = depotId
		self.depotKey = depotKey

	def parse(self, configuration=None):
		"""
		Parse the configuration file.

		:param confiuration: Predefined configuration. Contents may be \
overriden based on values in configuration file.
		:rtype: dict
		"""
		logger.info(u"Reading config file '%s'", self.configFile)
		if not os.path.isfile(self.configFile):
			raise OSError(u"Configuration file {!r} not found".format(self.configFile))

		config = DEFAULT_CONFIG.copy()
		if configuration:
			config.update(configuration)

		config['repositories'] = []

		try:
			iniFile = IniFile(filename=self.configFile, raw=True)
			configIni = iniFile.parse()
			for section in configIni.sections():
				if section.lower() == 'general':
					for (option, value) in configIni.items(section):
						if option.lower() == 'packagedir':
							config["packageDir"] = forceFilename(value.strip())
						elif option.lower() == 'logfile':
							value = forceFilename(value.strip())
							logger.setLogFile(value)
						elif option.lower() == 'loglevel':
							logger.setFileLevel(forceInt(value.strip()))
						elif option.lower() == 'timeout':
							# TODO: find a better way!
							socket.setdefaulttimeout(float(value.strip()))
						elif option.lower() == 'tempdir':
							config["tempdir"] = value.strip()
						elif option.lower() == 'repositoryconfigdir':
							config["repositoryConfigDir"] = value.strip()
						elif option.lower() == 'proxy' and value.strip():
							config["proxy"] = forceUrl(value.strip())
						elif option.lower() == 'ignoreerrors' and value.strip():
							config["ignoreErrors"] = forceBool(value.strip())

				elif section.lower() == 'notification':
					for (option, value) in configIni.items(section):
						if option.lower() == 'active':
							config["notification"] = forceBool(value)
						elif option.lower() == 'smtphost':
							config["smtphost"] = forceHostAddress(value.strip())
						elif option.lower() == 'smtpport':
							config["smtpport"] = forceInt(value.strip())
						elif option.lower() == 'smtpuser':
							config["smtpuser"] = forceUnicode(value.strip())
						elif option.lower() == 'smtppassword':
							config["smtppassword"] = forceUnicode(value.strip())
						elif option.lower() == 'subject':
							config["subject"] = forceUnicode(value.strip())
						elif option.lower() == 'use_starttls':
							config["use_starttls"] = forceBool(value.strip())
						elif option.lower() == 'sender':
							config["sender"] = forceEmailAddress(value.strip())
						elif option.lower() == 'receivers':
							config["receivers"] = [
								forceEmailAddress(receiver)
								for receiver in splitAndStrip(value, u",")
							]

				elif section.lower() == 'wol':
					for (option, value) in configIni.items(section):
						if option.lower() == 'active':
							config["wolAction"] = forceBool(value.strip())
						elif option.lower() == 'excludeproductids':
							config['wolActionExcludeProductIds'] = [
								forceProductId(productId)
								for productId in splitAndStrip(value, u',')
							]
						elif option.lower() == 'shutdownwanted':
							config["wolShutdownWanted"] = forceBool(value.strip())
						elif option.lower() == 'startgap':
							config["wolStartGap"] = forceInt(value.strip())
							if config["wolStartGap"] < 0:
								config["wolStartGap"] = 0

				elif section.lower() == 'installation':
					for (option, value) in configIni.items(section):
						if option.lower() == 'windowstart':
							if not value.strip():
								continue
							if not self.TIME_REGEX.search(value.strip()):
								raise ValueError(u"Start time '%s' not in needed format 'HH:MM'" % value.strip())
							config["installationWindowStartTime"] = value.strip()
						elif option.lower() == 'windowend':
							if not value.strip():
								continue
							if not self.TIME_REGEX.search(value.strip()):
								raise ValueError(u"End time '%s' not in needed format 'HH:MM'" % value.strip())
							config["installationWindowEndTime"] = value.strip()
						elif option.lower() == 'exceptproductids':
							config['installationWindowExceptions'] = [
								forceProductId(productId)
								for productId in splitAndStrip(value, ',')
							]
				elif section.lower().startswith('repository'):
					try:
						repository = self._getRepository(configIni, section, config['forceRepositoryActivation'], config['repositoryName'], config['installAllAvailable'], config['proxy'])
						config['repositories'].append(repository)
					except MissingConfigurationValueError as mcverr:
						logger.debug(u"Configuration for %s incomplete: %s", section, mcverr)
					except ConfigurationError as cerr:
						logger.error(u"Configuration problem in %s: %s", section, cerr)
					except Exception as err:
						logger.error(u"Can't load repository from %s: %s", section, err)
				else:
					logger.error(u"Unhandled section '%s'", section)
		except Exception as exclude:
			raise RuntimeError(u"Failed to read config file '%s': %s" % (self.configFile, exclude))

		for configFile in getRepoConfigs(config['repositoryConfigDir']):
			iniFile = IniFile(filename=configFile, raw=True)

			try:
				repoConfig = iniFile.parse()
				for section in repoConfig.sections():
					if not section.lower().startswith('repository'):
						continue

					try:
						repository = self._getRepository(repoConfig, section, config['forceRepositoryActivation'], config['repositoryName'], config['installAllAvailable'], proxy=config['proxy'])
						config['repositories'].append(repository)
					except MissingConfigurationValueError as mcverr:
						logger.debug(u"Configuration for %s in %s incomplete: %s", section, configFile, mcverr)
					except ConfigurationError as cerr:
						logger.error(u"Configuration problem in %s in %s: %s", section, configFile, cerr)
					except Exception as err:
						logger.error(u"Can't load repository from %s in %s: %s", section, configFile, err)
			except Exception as error:
				logger.error("Unable to load repositories from %s: %s", configFile, error)

		return config

	def _getRepository(self, config, section, forceRepositoryActivation=False, repositoryName=None, installAllAvailable=False, proxy=None):
		active = False
		verifyCert = False
		baseUrl = None
		opsiDepotId = None
		for (option, value) in config.items(section):
			option = option.lower()
			value = value.strip()
			if option == 'active':
				active = forceBool(value)
			elif option == 'baseurl':
				if value:
					baseUrl = forceUrl(value)
			elif option == 'opsidepotid':
				if value:
					opsiDepotId = forceHostId(value)
			elif option == 'proxy':
				if value:
					proxy = forceUrl(value)
			elif option == 'verifycert':
				verifyCert = forceBool(value)


		repoName = section.replace('repository_', '', 1)

		if forceRepositoryActivation:
			if repoName == repositoryName:
				logger.debug("Activation for repository %s forced.", repoName)
				active = True
			else:
				active = False

		repository = None
		if opsiDepotId:
			if not self.backend:
				raise RequiringBackendError("Repository section '{0}' supplied an depot ID but we have no backend to check.".format(section))

			depots = self.backend.host_getObjects(type='OpsiDepotserver', id=opsiDepotId)
			if not depots:
				raise ConfigurationError(u"Depot '%s' not found in backend" % opsiDepotId)
			if not depots[0].repositoryRemoteUrl:
				raise ConfigurationError(u"Repository remote url for depot '%s' not found in backend" % opsiDepotId)

			repository = ProductRepositoryInfo(
				name=repoName,
				baseUrl=depots[0].repositoryRemoteUrl,
				dirs=['/'],
				username=self.depotId,
				password=self.depotKey,
				opsiDepotId=opsiDepotId,
				active=active,
				verifyCert=verifyCert
			)

		elif baseUrl:
			if proxy:
				logger.info(u"Repository %s is using proxy %s", repoName, proxy)

			repository = ProductRepositoryInfo(
				name=repoName,
				baseUrl=baseUrl,
				proxy=proxy,
				active=active,
				verifyCert=verifyCert
			)
		else:
			raise MissingConfigurationValueError(u"Repository section '{0}': neither baseUrl nor opsiDepotId set".format(section))

		for (option, value) in config.items(section):
			if option.lower() == 'username':
				repository.username = forceUnicode(value.strip())
			elif option.lower() == 'password':
				repository.password = forceUnicode(value.strip())
				if repository.password:
					logger.addConfidentialString(repository.password)
			elif option.lower() == 'authcertfile':
				repository.authcertfile = forceFilename(value.strip())
			elif option.lower() == 'authkeyfile':
				repository.authkeyfile = forceFilename(value.strip())
			elif option.lower() == 'autoinstall':
				repository.autoInstall = forceBool(value.strip())
			elif option.lower() == 'autoupdate':
				repository.autoUpdate = forceBool(value.strip())
			elif option.lower() == 'autosetup':
				repository.autoSetup = forceBool(value.strip())
			elif option.lower() == 'onlydownload':
				repository.onlyDownload = forceBool(value.strip())
			elif option.lower() == 'inheritproductproperties':
				if not opsiDepotId:
					logger.warning(u"InheritProductProperties not possible with normal http ressource.")
					repository.inheritProductProperties = False
				else:
					repository.inheritProductProperties = forceBool(value.strip())
			elif option.lower() == 'dirs':
				repository.dirs = [
					forceFilename(directory)
					for directory in splitAndStrip(value, ',')
				]
			elif option.lower() == 'excludes':
				repository.excludes = [
					re.compile(exclude)
					for exclude in splitAndStrip(value, ',')
				]
			elif option.lower() == 'includeproductids':
				repository.includes = [
					re.compile(include)
					for include in splitAndStrip(value, ',')
				]
			elif option.lower() == 'autosetupexcludes':
				repository.autoSetupExcludes = [
					re.compile(exclude)
					for exclude in splitAndStrip(value, ',')
				]
			elif option.lower() == 'description':
				repository.description = forceUnicode(value)

		if installAllAvailable:
			repository.autoInstall = True
			repository.autoUpdate = True
			repository.excludes = []

		return repository
