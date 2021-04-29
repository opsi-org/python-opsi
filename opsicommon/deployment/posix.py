# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0

import sys
import os
import re
import socket
from contextlib import closing, contextmanager

from OPSI.Util.File import IniFile
from OPSI.Util import randomString
from OPSI.Types import forceUnicodeLower
from OPSI.System import copy
from OPSI.Object import ProductOnClient

from ..logging import logger
from .common import DeployThread, SkipClientException, SKIP_MARKER

try:
	import paramiko	# type: ignore
	AUTO_ADD_POLICY = paramiko.AutoAddPolicy
	WARNING_POLICY = paramiko.WarningPolicy
	REJECT_POLICY = paramiko.RejectPolicy
except ImportError:
	paramiko = None
	AUTO_ADD_POLICY = None
	WARNING_POLICY = None
	REJECT_POLICY = None

class SSHRemoteExecutionException(Exception):
	pass

class PosixDeployThread(DeployThread):
	def __init__(  # pylint: disable=too-many-arguments,too-many-locals
		self, host, backend, username, password, shutdown, reboot, startService,
		target_os, deploymentMethod="hostname", stopOnPingFailure=True,
		skipExistingClient=False, mountWithSmbclient=True,
		keepClientOnFailure=False, additionalClientSettings=None,
		depot=None, group=None, sshPolicy=WARNING_POLICY
	):

		DeployThread.__init__(self, host, backend, username, password, shutdown,
		reboot, startService, deploymentMethod, stopOnPingFailure,
		skipExistingClient, mountWithSmbclient, keepClientOnFailure,
		additionalClientSettings, depot, group)

		self.target_os = target_os
		self._sshConnection = None
		self._sshPolicy = sshPolicy

	def run(self):
		self._installWithSSH()

	def copy_and_link_macos_ssl(self, remoteFolder, credentialsfile=None):
		lib_origin = os.path.join(remoteFolder, 'files', 'opsi', 'opsi-script_helper')
		libs = [('libssl.1.1.dylib', 'libssl.dylib'), ('libcrypto.1.1.dylib', 'libssl.dylib')]
		lib_dir = '/usr/local/lib/'

		self._executeViaSSH(f"mkdir -p {lib_dir}", credentialsfile=credentialsfile)
		for lib, link in libs:
			command = f"cp {os.path.join(lib_origin, lib)} {os.path.join(lib_dir, lib)}"
			self._executeViaSSH(command, credentialsfile=credentialsfile)

			command = f"ln -sf {os.path.join(lib_dir, lib)} {os.path.join(lib_dir, link)}"
			self._executeViaSSH(command, credentialsfile=credentialsfile)

	def _installWithSSH(self):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
		logger.debug('Installing with files copied to client via scp.')
		host = forceUnicodeLower(self.host)
		hostId = ''
		hostObj = None
		remoteFolder = os.path.join('/tmp', 'opsi-client-agent')
		try:
			hostId = self._getHostId(host)
			self._checkIfClientShouldBeSkipped(hostId)

			logger.notice("Starting deployment to host %s", hostId)
			hostObj = self._prepareDeploymentToHost(hostId)

			if getattr(sys, 'frozen', False):
				localFolder = os.path.dirname(os.path.abspath(sys.executable))		# for running as executable
			else:
				localFolder = os.path.dirname(os.path.abspath(__file__))			# for running from python
			logger.notice("Patching config.ini")
			configIniName = f'{randomString(10)}_config.ini'
			configIniPath = os.path.join('/tmp', configIniName)
			copy(os.path.join(localFolder, 'files', 'opsi', 'cfg', 'config.ini'), configIniPath)
			configFile = IniFile(configIniPath)
			config = configFile.parse()
			if not config.has_section('shareinfo'):
				config.add_section('shareinfo')
			config.set('shareinfo', 'pckey', hostObj.opsiHostKey)
			if not config.has_section('general'):
				config.add_section('general')
			config.set('general', 'dnsdomain', '.'.join(hostObj.id.split('.')[1:]))
			configFile.generate(config)
			logger.debug("Generated config.")

			credentialsfile=None
			try:
				logger.notice("Copying installation scripts...")
				self._copyDirectoryOverSSH(
					os.path.join(localFolder, 'files'),
					remoteFolder
				)

				logger.debug("Copying config for client...")
				self._copyFileOverSSH(configIniPath, os.path.join(remoteFolder, 'files', 'opsi', 'cfg', 'config.ini'))

				if self.target_os == "linux":
					opsiscript = "/tmp/opsi-client-agent/files/opsi-script/opsi-script"
				elif self.target_os == "macos":
					opsiscript = "/tmp/opsi-client-agent/files/opsi-script.app/Contents/MacOS/opsi-script"
				else:
					raise ValueError(f"invalid target os {self.target_os}")

				logger.debug("Will use: %s", opsiscript)
				self._executeViaSSH(f"chmod +x {opsiscript}")

				service_configstate = self.backend.configState_getObjects(configId='clientconfig.configserver.url', objectId=hostObj.id)
				if len(service_configstate) != 1 and len(service_configstate[0].values) != 1:
					raise ValueError("Could not determine associated configservice url")
				service_address = service_configstate[0].values[0]
				finalize = "noreboot"
				if self.reboot:
					finalize = "reboot"
				elif self.shutdown:
					finalize = "shutdown"

				installCommand = (
					f"{opsiscript} -batch -silent /tmp/opsi-client-agent/setup.opsiscript"
					" /var/log/opsi-client-agent/opsi-script/opsi-client-agent.log -parameter"
					f" {service_address}||{hostObj.id}||{hostObj.opsiHostKey}||{finalize}"
				)
				if self.username != 'root':
					credentialsfile = os.path.join(remoteFolder, '.credentials')
					self._executeViaSSH(f"touch {credentialsfile}")
					self._executeViaSSH(f"chmod 600 {credentialsfile}")
					self._executeViaSSH(f"echo '{self.password}' > {credentialsfile}")
					self._executeViaSSH(f'echo "\n" >> {credentialsfile}')

				try:
					if self.target_os == "macos":
						self.copy_and_link_macos_ssl(remoteFolder, credentialsfile=credentialsfile)
					logger.notice('Running installation script...')
					self._executeViaSSH(installCommand, credentialsfile=credentialsfile)
				except Exception:
					if credentialsfile:
						self._executeViaSSH(f"rm -f {credentialsfile}")
					raise

				logger.debug("Testing if folder was created...")
				self._executeViaSSH("test -d /etc/opsi-client-agent/")
				logger.debug("Testing if config can be found...")
				checkCommand = "test -e /etc/opsi-client-agent/opsiclientd.conf"
				self._executeViaSSH(checkCommand, credentialsfile=credentialsfile)

				logger.debug("Testing if executable was found...")
				if self.target_os == "linux":
					self._executeViaSSH("test -e /usr/bin/opsiclientd -o -e /usr/bin/opsi-script-nogui")
				elif self.target_os == "macos":
					self._executeViaSSH("test -e /usr/local/bin/opsiclientd -o -e /usr/local/bin/opsi-script-nogui")
				else:
					raise ValueError(f"invalid target os {self.target_os}")
			finally:
				try:
					os.remove(configIniPath)
				except OSError as error:
					logger.debug("Removing %s failed: %s", configIniPath, error)

			logger.notice("opsi-client-agent successfully installed on %s", hostId)
			self.success = True
			self._setOpsiClientAgentToInstalled(hostId)
		except SkipClientException:
			logger.notice("Skipping host %s", hostId)
			self.success = SKIP_MARKER
			return
		except (Exception, paramiko.SSHException) as err:  # pylint: disable=broad-except
			logger.error("Deployment to %s failed: %s", self.host, err)
			self.success = False
			if 'Incompatible ssh peer (no acceptable kex algorithm)' in str(err):
				logger.error("Please install paramiko v1.15.1 or newer")

			if self._clientCreatedByScript and hostObj and not self.keepClientOnFailure:
				self._removeHostFromBackend(hostObj)

			if self._sshConnection is not None:
				try:
					self._sshConnection.close()
				except Exception as err:  # pylint: disable=broad-except
					logger.trace("Closing SSH connection failed: %s", err)
		finally:
			try:
				self._executeViaSSH(f"rm -rf {remoteFolder}")
			except (Exception, paramiko.SSHException) as err:  # pylint: disable=broad-except
				logger.error(err)

	def _getHostId(self, host):
		hostId = None
		try:
			hostId = super()._getHostId(host)
		except socket.herror:
			logger.warning("Resolving hostName failed, attempting to resolve fqdn via ssh connection to ip")
			if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', host):
				ssh = paramiko.SSHClient()
				ssh.set_missing_host_key_policy(self._sshPolicy())
				ssh.connect(host, "22", self.username, self.password)
				_stdin, stdout, _stderr = ssh.exec_command("hostname -f")
				hostId = stdout.readlines()[0].encode('ascii','ignore').strip()
				logger.info("resolved FQDN: %s (type %s)", hostId, type(hostId))
		if hostId:
			return hostId
		raise ValueError(f"invalid host {host}")

	def _executeViaSSH(self, command, credentialsfile=None):
		"""
		Executing a command via SSH.

		Will return the output of stdout and stderr in one iterable object.
		:raises SSHRemoteExecutionException: if exit code is not 0.
		"""
		self._connectViaSSH()

		if credentialsfile:
			if "&" in command:
				parts = command.split("&", 1)
				command = f"sudo --stdin -- {parts[0]} < {credentialsfile} &{parts[1]}"
			else:
				command = f"sudo --stdin -- {command} < {credentialsfile}"
		logger.debug("Executing on remote: %s", command)

		with closing(self._sshConnection.get_transport().open_session()) as channel:
			channel.set_combine_stderr(True)
			channel.settimeout(None)  # blocking until completion of command

			channel.exec_command(command)
			exitCode = channel.recv_exit_status()
			out = channel.makefile("rb", -1).read().decode("utf-8", "replace")

			logger.debug("Exit code was: %s", exitCode)

			if exitCode:
				logger.debug("Command output: ")
				logger.debug(out)
				raise SSHRemoteExecutionException(
					f"Executing {command} on remote client failed! Got exit code {exitCode}"
				)

			return out

	def _getTargetArchitecture(self):
		logger.debug("Checking architecture of client...")
		output = self._executeViaSSH('uname -m')
		if "64" not in output:
			return "32"
		return "64"

	def _connectViaSSH(self):
		if self._sshConnection is not None:
			return

		self._sshConnection = paramiko.SSHClient()
		self._sshConnection.load_system_host_keys()
		self._sshConnection.set_missing_host_key_policy(self._sshPolicy())

		logger.debug("Connecting via SSH...")
		self._sshConnection.connect(
			hostname=self.networkAddress,
			username=self.username,
			password=self.password
		)

	def _copyFileOverSSH(self, localPath, remotePath):
		self._connectViaSSH()

		with closing(self._sshConnection.open_sftp()) as ftpConnection:
			ftpConnection.put(localPath, remotePath)

	def _copyDirectoryOverSSH(self, localPath, remotePath):
		@contextmanager
		def changeDirectory(path):
			currentDir = os.getcwd()
			os.chdir(path)
			yield
			os.chdir(currentDir)

		def createFolderIfMissing(path):
			try:
				ftpConnection.mkdir(path)
			except Exception as err:  # pylint: disable=broad-except
				logger.debug("Can't create %s on remote: %s", path, err)

		self._connectViaSSH()

		with closing(self._sshConnection.open_sftp()) as ftpConnection:
			createFolderIfMissing(remotePath)

			if not os.path.exists(localPath):
				raise ValueError(f"Can't find local path '{localPath}'")

			# The following stunt is necessary to get results in 'dirpath'
			# that can be easily used for folder creation on the remote.
			with changeDirectory(os.path.join(localPath, '..')):
				directoryToWalk = os.path.basename(localPath)
				for dirpath, _, filenames in os.walk(directoryToWalk):
					createFolderIfMissing(os.path.join(remotePath, dirpath))

					for filename in filenames:
						local = os.path.join(dirpath, filename)
						remote = os.path.join(remotePath, dirpath, filename)

						logger.trace("Copying %s -> %s", local, remote)
						ftpConnection.put(local, remote)

	def _setOpsiClientAgentToInstalled(self, hostId):
		if self.target_os == "linux":
			prod_id = "opsi-linux-client-agent"
		elif self.target_os == "macos":
			prod_id = "opsi-mac-client-agent"
		else:
			raise ValueError(f"invalid target os {self.target_os}")

		poc = ProductOnClient(
			productType='LocalbootProduct',
			clientId=hostId,
			productId=prod_id,
			installationStatus='installed',
			actionResult='successful'
		)
		self.backend.productOnClient_updateObjects([poc])
