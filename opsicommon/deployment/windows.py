# -*- coding: utf-8 -*-

# This tool is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
# Copyright (C) 2007-2019 uib GmbH <info@uib.de>

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
:copyright: uib GmbH <info@uib.de>
:license: GNU Affero General Public License version 3
"""

import time
import socket
import shutil
import re
import os
import logging

from OPSI.Util.File import IniFile
from OPSI.Util import randomString
from OPSI.Types import forceHostId, forceIPAddress, forceUnicode, forceUnicodeLower
from OPSI.System import copy, execute, getFQDN, umount, which

from ..logging import logger
from .common import DeployThread, SkipClientException, SKIP_MARKER


def winexe(cmd, host, username, password):
	cmd = forceUnicode(cmd)
	host = forceUnicode(host)
	username = forceUnicode(username)
	password = forceUnicode(password)

	match = re.search(r'^([^\\\\]+)\\\\+([^\\\\]+)$', username)
	if match:
		username = match.group(1) + r'\\' + match.group(2)

	try:
		executable = which('winexe')
	except Exception as err:  # pylint: disable=broad-except
		logger.critical(
			"Unable to find 'winexe'. Please install 'opsi-windows-support' "
			"through your operating systems package manager!"
		)
		raise RuntimeError("Missing 'winexe'") from err

	try:
		logger.info('Winexe Version: %s', ''.join(execute(f'{executable} -V')))
	except Exception as err:  # pylint: disable=broad-except
		logger.warning("Failed to get version: %s", err)

	credentials=username + '%' + password.replace("'", "'\"'\"'")
	if logger.isEnabledFor(logging.DEBUG):
		return execute(f"{executable} -d 9 -U '{credentials}' //{host} '{cmd}'")
	return execute(f"{executable} -U '{credentials}' //{host} '{cmd}'")

class WindowsDeployThread(DeployThread):
	def __init__(  # pylint: disable=too-many-arguments,too-many-locals
		self, host, backend, username, password, shutdown, reboot, startService,
		deploymentMethod="hostname", stopOnPingFailure=True,
		skipExistingClient=False, mountWithSmbclient=True,
		keepClientOnFailure=False, additionalClientSettings=None,
		depot=None, group=None
	):
		DeployThread.__init__(
			self, host, backend, username, password, shutdown,
			reboot, startService, deploymentMethod, stopOnPingFailure,
			skipExistingClient, mountWithSmbclient, keepClientOnFailure,
			additionalClientSettings, depot, group
		)

	def run(self):
		if self.mountWithSmbclient:
			self._installWithSmbclient()
		else:
			self._installWithServersideMount()

	def _installWithSmbclient(self):  # pylint: disable=too-many-branches,too-many-statements
		logger.debug('Installing using client-side mount.')
		host = forceUnicodeLower(self.host)
		hostId = ''
		hostObj = None
		try:
			hostId = self._getHostId(host)
			self._checkIfClientShouldBeSkipped(hostId)

			logger.notice("Starting deployment to host %s", hostId)
			hostObj = self._prepareDeploymentToHost(hostId)
			self._testWinexeConnection()

			logger.notice("Patching config.ini")
			configIniName = f'{randomString(10)}_config.ini'
			copy(os.path.join('files', 'opsi', 'cfg', 'config.ini'), f'/tmp/{configIniName}')
			configFile = IniFile(f'/tmp/{configIniName}')
			config = configFile.parse()
			if not config.has_section('shareinfo'):
				config.add_section('shareinfo')
			config.set('shareinfo', 'pckey', hostObj.opsiHostKey)
			if not config.has_section('general'):
				config.add_section('general')
			config.set('general', 'dnsdomain', '.'.join(hostObj.id.split('.')[1:]))
			configFile.generate(config)

			try:
				logger.notice("Copying installation files")
				credentials=self.username + '%' + self.password.replace("'", "'\"'\"'")
				debug_param = " -d 9" if logger.isEnabledFor(logging.DEBUG) else ""
				cmd = (
					f"{which('smbclient')} -m SMB3{debug_param} //{self.networkAddress}/c$ -U '{credentials}'"
					" -c 'prompt; recurse; md tmp; cd tmp; md opsi-client-agent_inst;"
					" cd opsi-client-agent_inst; mput files; mput utils; cd files\\opsi\\cfg;"
					f" lcd /tmp; put {configIniName} config.ini; exit;'"
				)
				execute(cmd)

				logger.notice("Installing opsi-client-agent")
				cmd = (
					r"c:\\tmp\\opsi-client-agent_inst\\files\\opsi\\opsi-script\\opsi-script.exe"
					r" /batch c:\\tmp\\opsi-client-agent_inst\\files\\opsi\\setup.opsiscript"
					r" c:\\tmp\\opsi-client-agent.log /PARAMETER REMOTEDEPLOY"
				)
				for trynum in (1, 2):
					try:
						winexe(cmd, self.networkAddress, self.username, self.password)
						break
					except Exception as err:  # pylint: disable=broad-except
						if trynum == 2:
							raise Exception(f"Failed to install opsi-client-agent: {err}") from err
						logger.info("Winexe failure %s, retrying", err)
						time.sleep(2)
			finally:
				os.remove(f'/tmp/{configIniName}')

				try:
					cmd = (
						r'cmd.exe /C "del /s /q c:\\tmp\\opsi-client-agent_inst'
						r' && rmdir /s /q c:\\tmp\\opsi-client-agent_inst"'
					)
					winexe(cmd, self.networkAddress, self.username, self.password)
				except Exception as err:  # pylint: disable=broad-except
					logger.error(err)

			logger.notice("opsi-client-agent successfully installed on %s", hostId)
			self.success = True
			self._setOpsiClientAgentToInstalled(hostId)
			self._finaliseInstallation()
		except SkipClientException:
			logger.notice("Skipping host %s", hostId)
			self.success = SKIP_MARKER
			return
		except Exception as err:  # pylint: disable=broad-except
			logger.error("Deployment to %s failed: %s", self.host, err)
			self.success = False
			if self._clientCreatedByScript and hostObj and not self.keepClientOnFailure:
				self._removeHostFromBackend(hostObj)

	def _getHostId(self, host):  # pylint: disable=too-many-branches
		ip = None
		if self.deploymentMethod == 'ip':
			ip = forceIPAddress(host)
			try:
				(hostname, _, _) = socket.gethostbyaddr(ip)
				host = hostname
			except socket.herror as error:
				logger.debug("Lookup for %s failed: %s", ip, error)

				try:
					output = winexe('cmd.exe /C "echo %COMPUTERNAME%"', ip, self.username, self.password)
					for line in output:
						if line.strip():
							if 'unknown parameter' in line.lower():
								continue

							host = line.strip()
							break
				except Exception as err:
					logger.debug("Name lookup via winexe failed: %s", err)
					raise Exception(f"Can't find name for IP {ip}: {err}") from err

			logger.debug("Lookup of IP returned hostname %s", host)

		host = host.replace('_', '-')

		if host.count('.') < 2:
			hostBefore = host
			try:
				host = socket.getfqdn(socket.gethostbyname(host))

				try:
					if ip == forceIPAddress(host):  # Lookup did not succeed
						# Falling back to hopefully valid hostname
						host = hostBefore
				except ValueError:
					pass  # no IP - great!
				except NameError:
					pass  # no deployment via IP
			except socket.gaierror as error:
				logger.debug("Lookup of %s failed.", host)

		logger.debug("Host is now: %s", host)
		if host.count('.') < 2:
			hostId = forceHostId(f'{host}.{".".join(getFQDN().split(".")[1:])}')
		else:
			hostId = forceHostId(host)

		logger.info("Got hostId %s", hostId)
		return hostId

	def _testWinexeConnection(self):
		logger.notice("Testing winexe")
		cmd = r'cmd.exe /C "del /s /q c:\\tmp\\opsi-client-agent_inst && rmdir /s /q c:\\tmp\\opsi-client-agent_inst || echo not found"'
		for trynum in (1, 2):
			try:
				winexe(cmd, self.networkAddress, self.username, self.password)
				break
			except Exception as err:  # pylint: disable=broad-except
				if 'NT_STATUS_LOGON_FAILURE' in str(err):
					logger.warning("Can't connect to %s: check your credentials", self.networkAddress)
				elif 'NT_STATUS_IO_TIMEOUT' in str(err):
					logger.warning("Can't connect to %s: firewall on client seems active", self.networkAddress)

				if trynum == 2:
					raise Exception(f"Failed to execute command on host {self.networkAddress}: winexe error: {err}") from err
				logger.info("Winexe failure %s, retrying", err)
				time.sleep(2)

	def _finaliseInstallation(self):  # pylint: disable=too-many-branches
		if self.reboot or self.shutdown:
			if self.reboot:
				logger.notice("Rebooting machine %s", self.networkAddress)
				cmd = r'"%ProgramFiles%\\opsi.org\\opsi-client-agent\\utilities\\shutdown.exe" /L /R /T:20 "opsi-client-agent installed - reboot" /Y /C'
			else:	# self.shutdown must be set
				logger.notice("Shutting down machine %s", self.networkAddress)
				cmd = r'"%ProgramFiles%\\opsi.org\\opsi-client-agent\\utilities\\shutdown.exe" /L /T:20 "opsi-client-agent installed - shutdown" /Y /C'

			try:
				pf = None
				for const in ('%ProgramFiles(x86)%', '%ProgramFiles%'):
					try:
						lines = winexe(f'cmd.exe /C "echo {const}"', self.networkAddress, self.username, self.password)
					except Exception as err:  # pylint: disable=broad-except
						logger.warning(err)
						continue

					for line in lines:
						line = line.strip()
						if 'unavailable' in line:
							continue
						pf = line

					if pf and pf != const:
						break

					pf = None

				if not pf:
					raise Exception("Failed to get program files path")

				logger.info("Program files path is %s", pf)
				winexe(cmd.replace('%ProgramFiles%', pf), self.networkAddress, self.username, self.password)
			except Exception as err:  # pylint: disable=broad-except
				if self.reboot:
					logger.error("Failed to reboot computer: %s", err)
				else:
					logger.error("Failed to shutdown computer: %s", err)
		elif self.startService:
			try:
				winexe('net start opsiclientd', self.networkAddress, self.username, self.password)
			except Exception as err:  # pylint: disable=broad-except
				logger.error("Failed to start opsiclientd on %s: %s", self.networkAddress, err)

	def _installWithServersideMount(self):  # pylint: disable=too-many-branches,too-many-statements
		logger.debug('Installing using server-side mount.')
		host = forceUnicodeLower(self.host)
		hostId = ''
		hostObj = None
		mountDir = ''
		instDir = ''
		try:
			hostId = self._getHostId(host)
			self._checkIfClientShouldBeSkipped(hostId)

			logger.notice("Starting deployment to host %s", hostId)
			hostObj = self._prepareDeploymentToHost(hostId)
			self._testWinexeConnection()

			mountDir = os.path.join('/tmp', 'mnt_' + randomString(10))
			os.makedirs(mountDir)

			logger.notice("Mounting c$ share")
			try:
				password = self.password.replace("'", "'\"'\"'")
				try:
					execute(f"{which('mount')} -t cifs -o'username={self.username},password={password}' //{self.networkAddress}/c$ {mountDir}",
						timeout=15
					)
				except Exception as err:  # pylint: disable=broad-except
					logger.info("Failed to mount clients c$ share: %s, retrying with port 139", err)
					execute(f"{which('mount')} -t cifs -o'port=139,username={self.username},password={password}' //{self.networkAddress}/c$ {mountDir}",
						timeout=15
					)
			except Exception as err:  # pylint: disable=broad-except
				raise Exception(
					f"Failed to mount c$ share: {err}\n"
					"Perhaps you have to disable the firewall or simple file sharing on the windows machine (folder options)?"
				) from err

			logger.notice("Copying installation files")
			instDirName = f'opsi_{randomString(10)}'
			instDir = os.path.join(mountDir, instDirName)
			os.makedirs(instDir)

			copy('files', instDir)
			copy('utils', instDir)

			logger.notice("Patching config.ini")
			configFile = IniFile(os.path.join(instDir, 'files', 'opsi', 'cfg', 'config.ini'))
			config = configFile.parse()
			if not config.has_section('shareinfo'):
				config.add_section('shareinfo')
			config.set('shareinfo', 'pckey', hostObj.opsiHostKey)
			if not config.has_section('general'):
				config.add_section('general')
			config.set('general', 'dnsdomain', '.'.join(hostObj.id.split('.')[1:]))
			configFile.generate(config)

			logger.notice("Installing opsi-client-agent")
			if not os.path.exists(os.path.join(mountDir, 'tmp')):
				os.makedirs(os.path.join(mountDir, 'tmp'))
			cmd = (
				f"c:\\{instDirName}\\files\\opsi\\opsi-winst\\winst32.exe"
				f" /batch c:\\{instDirName}\\files\\opsi\\setup.opsiscript"
				" c:\\tmp\\opsi-client-agent.log /PARAMETER REMOTEDEPLOY"
			)
			for trynum in (1, 2):
				try:
					winexe(cmd, self.networkAddress, self.username, self.password)
					break
				except Exception as err:  # pylint: disable=broad-except
					if trynum == 2:
						raise Exception(f"Failed to install opsi-client-agent: {err}") from err
					logger.info("Winexe failure %s, retrying", err)
					time.sleep(2)

			logger.notice("opsi-client-agent successfully installed on %s", hostId)
			self.success = True
			self._setOpsiClientAgentToInstalled(hostId)
			self._finaliseInstallation()
		except SkipClientException:
			logger.notice("Skipping host %s", hostId)
			self.success = SKIP_MARKER
			return
		except Exception as err:  # pylint: disable=broad-except
			self.success = False
			logger.error("Deployment to %s failed: %s", self.host, err)
			if self._clientCreatedByScript and hostObj and not self.keepClientOnFailure:
				self._removeHostFromBackend(hostObj)
		finally:
			if instDir or mountDir:
				logger.notice("Cleaning up")

			if instDir:
				try:
					shutil.rmtree(instDir)
				except OSError as err:
					logger.debug('Removing %s failed: %s', instDir, err)

			if mountDir:
				try:
					umount(mountDir)
				except Exception as err:  # pylint: disable=broad-except
					logger.warning('Unmounting %s failed: %s', mountDir, err)

				try:
					os.rmdir(mountDir)
				except OSError as err:
					logger.debug('Removing %s failed: %s', instDir, err)
