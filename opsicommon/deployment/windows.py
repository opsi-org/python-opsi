import time
import socket
import shutil
import re
import os

from OPSI.Util.File import IniFile
from OPSI.Util import randomString
from OPSI.Types import forceHostId, forceIPAddress, forceUnicode, forceUnicodeLower
from OPSI.System import copy, execute, getFQDN, umount, which

from opsicommon.deployment.common import logger, LOG_DEBUG, DeployThread, SkipClientException, SKIP_MARKER

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
	except Exception:
		logger.critical(
			"Unable to find 'winexe'. Please install 'opsi-windows-support' "
			"through your operating systems package manager!"
		)
		raise RuntimeError("Missing 'winexe'")

	try:
		logger.info('Winexe Version: %s', ''.join(execute(f'{executable} -V')))
	except Exception as versionError:
		logger.warning("Failed to get version: %s", versionError)

	credentials=username + '%' + password.replace("'", "'\"'\"'")
	if logger.isEnabledFor(LOG_DEBUG):
		return execute(f"{executable} -d 9 -U '{credentials}' //{host} '{cmd}'")
	return execute(f"{executable} -U '{credentials}' //{host} '{cmd}'")

class WindowsDeployThread(DeployThread):
	def __init__(self, host, backend, username, password, shutdown, reboot, startService,
			deploymentMethod="hostname", stopOnPingFailure=True,
			skipExistingClient=False, mountWithSmbclient=True,
			keepClientOnFailure=False, additionalClientSettings=None,
			depot=None, group=None):

		DeployThread.__init__(self, host, backend, username, password, shutdown,
			reboot, startService, deploymentMethod, stopOnPingFailure,
			skipExistingClient, mountWithSmbclient, keepClientOnFailure,
			additionalClientSettings, depot, group)

	def run(self):
		if self.mountWithSmbclient:
			self._installWithSmbclient()
		else:
			self._installWithServersideMount()

	def _installWithSmbclient(self):
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
				if logger.isEnabledFor(LOG_DEBUG):
					cmd = f"{which('smbclient')} -m SMB3 -d 9 //{self.networkAddress}/c$ -U '{credentials}' -c 'prompt; recurse; md tmp; cd tmp; md opsi-client-agent_inst; cd opsi-client-agent_inst; mput files; mput utils; cd files\\opsi\\cfg; lcd /tmp; put {configIniName} config.ini; exit;'"
				else:
					cmd = f"{which('smbclient')} -m SMB3 //{self.networkAddress}/c$ -U '{credentials}' -c 'prompt; recurse; md tmp; cd tmp; md opsi-client-agent_inst; cd opsi-client-agent_inst; mput files; mput utils; cd files\\opsi\\cfg; lcd /tmp; put {configIniName} config.ini; exit;'"
				execute(cmd)

				logger.notice("Installing opsi-client-agent")
				cmd = r'c:\\tmp\\opsi-client-agent_inst\\files\\opsi\\opsi-winst\\winst32.exe /batch c:\\tmp\\opsi-client-agent_inst\\files\\opsi\\setup.opsiscript c:\\tmp\\opsi-client-agent.log /PARAMETER REMOTEDEPLOY'
				for trynum in (1, 2):
					try:
						winexe(cmd, self.networkAddress, self.username, self.password)
						break
					except Exception as error:
						if trynum == 2:
							raise Exception(f"Failed to install opsi-client-agent: {error}")
						logger.info("Winexe failure %s, retrying", error)
						time.sleep(2)
			finally:
				os.remove(f'/tmp/{configIniName}')

				try:
					cmd = r'cmd.exe /C "del /s /q c:\\tmp\\opsi-client-agent_inst && rmdir /s /q c:\\tmp\\opsi-client-agent_inst"'
					winexe(cmd, self.networkAddress, self.username, self.password)
				except Exception as error:
					logger.error(error)

			logger.notice("opsi-client-agent successfully installed on %s", hostId)
			self.success = True
			self._setOpsiClientAgentToInstalled(hostId)
			self._finaliseInstallation()
		except SkipClientException:
			logger.notice("Skipping host %s", hostId)
			self.success = SKIP_MARKER
			return
		except Exception as error:
			logger.error("Deployment to %s failed: %s", self.host, error)
			self.success = False
			if self._clientCreatedByScript and hostObj and not self.keepClientOnFailure:
				self._removeHostFromBackend(hostObj)

	def _getHostId(self, host):
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
				except Exception as error:
					logger.debug("Name lookup via winexe failed: %s", error)
					raise Exception("Can't find name for IP {ip}: {error}")

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
			except Exception as error:
				if 'NT_STATUS_LOGON_FAILURE' in forceUnicode(error):
					logger.warning("Can't connect to %s: check your credentials", self.networkAddress)
				elif 'NT_STATUS_IO_TIMEOUT' in forceUnicode(error):
					logger.warning("Can't connect to %s: firewall on client seems active", self.networkAddress)

				if trynum == 2:
					raise Exception(f"Failed to execute command on host {self.networkAddress}: winexe error: {error}")
				logger.info("Winexe failure %s, retrying", error)
				time.sleep(2)

	def _finaliseInstallation(self):
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
					except Exception as error:
						logger.warning(error)
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
			except Exception as error:
				if self.reboot:
					logger.error("Failed to reboot computer: %s", error)
				else:
					logger.error("Failed to shutdown computer: %s", error)
		elif self.startService:
			try:
				winexe('net start opsiclientd', self.networkAddress, self.username, self.password)
			except Exception as error:
				logger.error("Failed to start opsiclientd on %s: %s", self.networkAddress, error=error)

	def _installWithServersideMount(self):
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
				password = self.password.replace("'", "'\"'\"'"),
				try:
					execute(f"{which('mount')} -t cifs -o'username={self.username},password={password}' //{self.networkAddress}/c$ {mountDir}",
						timeout=15
					)
				except Exception as error:
					logger.info("Failed to mount clients c$ share: %s, retrying with port 139", error)
					execute(f"{which('mount')} -t cifs -o'port=139,username={self.username},password={password}' //{self.networkAddress}/c$ {mountDir}",
						timeout=15
					)
			except Exception as error:
				raise Exception(f"Failed to mount c$ share: {error}\nPerhaps you have to disable the firewall or simple file sharing on the windows machine (folder options)?")

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
			cmd = f'c:\\{instDirName}\\files\\opsi\\opsi-winst\\winst32.exe /batch c:\\{instDirName}\\files\\opsi\\setup.opsiscript c:\\tmp\\opsi-client-agent.log /PARAMETER REMOTEDEPLOY'
			for trynum in (1, 2):
				try:
					winexe(cmd, self.networkAddress, self.username, self.password)
					break
				except Exception as error:
					if trynum == 2:
						raise Exception(f"Failed to install opsi-client-agent: {error}")
					logger.info("Winexe failure %s, retrying", error)
					time.sleep(2)

			logger.notice("opsi-client-agent successfully installed on %s", hostId)
			self.success = True
			self._setOpsiClientAgentToInstalled(hostId)
			self._finaliseInstallation()
		except SkipClientException:
			logger.notice("Skipping host %s", hostId)
			self.success = SKIP_MARKER
			return
		except Exception as error:
			self.success = False
			logger.error("Deployment to %s failed: %s", self.host, error)
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
				except Exception as err:
					logger.warning('Unmounting %s failed: %s', mountDir, err)

				try:
					os.rmdir(mountDir)
				except OSError as err:
					logger.debug('Removing %s failed: %s', instDir, err)
