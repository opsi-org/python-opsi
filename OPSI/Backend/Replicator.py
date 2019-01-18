# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2010-2019 uib GmbH <info@uib.de>

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
Backend-Replicator.

The replicator allows replication from one backend into another.


:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Logger import LOG_DEBUG, Logger
from OPSI.Object import *
from OPSI.Types import forceBool, forceHostId, forceList
from OPSI.Util.Message import ProgressSubject

__all__ = ('BackendReplicator', )

logger = Logger()


class BackendReplicator(object):
	OBJECT_CLASSES = [
		'Host',
		'Product',
		'Config',
		'Group',
		'LicenseContract',
		'LicensePool',
		'SoftwareLicense',
		'AuditHardware',
		'AuditSoftware',
		'ProductDependency',
		'ProductProperty',
		'ProductOnDepot',
		'ProductOnClient',
		'ProductPropertyState',
		'ConfigState',
		'ObjectToGroup',
		'AuditHardwareOnHost',
		'AuditSoftwareOnClient',
		'SoftwareLicenseToLicensePool',
		'LicenseOnClient',
		'AuditSoftwareToLicensePool'
	]

	def __init__(self, readBackend, writeBackend, newServerId=None, oldServerId=None, cleanupFirst=True):
		self.__readBackend = readBackend
		self.__writeBackend = writeBackend

		self._extendedReadBackend = ExtendedConfigDataBackend(self.__readBackend)
		self._extendedWriteBackend = ExtendedConfigDataBackend(self.__writeBackend)

		self.__newServerId = None
		self.__oldServerId = None

		self.__cleanupFirst = forceBool(cleanupFirst)
		self.__strict = False
		self.__serverIds = []
		self.__depotIds = []
		self.__clientIds = []
		self.__groupIds = []
		self.__productIds = []

		if newServerId:
			self.__newServerId = forceHostId(newServerId)
		if oldServerId:
			self.__oldServerId = forceHostId(oldServerId)

		self.__overallProgressSubject = ProgressSubject(
			id=u'overall_replication',
			title=u'Replicating',
			end=100,
			fireAlways=True
		)
		self.__currentProgressSubject = ProgressSubject(
			id=u'current_replication',
			fireAlways=True
		)

	def getCurrentProgressSubject(self):
		return self.__currentProgressSubject

	def getOverallProgressSubject(self):
		return self.__overallProgressSubject

	def replicate(self, serverIds=[], depotIds=[], clientIds=[], groupIds=[],
			productIds=[], productTypes=[], audit=True, license=True):
		'''
		Replicate (a part) of a opsi configuration database
		An empty list passed as a param means: replicate all known
		None as the only element of a list means: replicate none
		'''
		serverIds = forceList(serverIds)
		depotIds = forceList(depotIds)
		clientIds = forceList(clientIds)
		groupIds = forceList(serverIds)
		productIds = forceList(productIds)
		productTypes = forceList(productTypes)
		audit = forceBool(audit)
		license = forceBool(license)

		logger.info(
			u"Replicating: serverIds={serverIds}, depotIds={depotIds}, "
			u"clientIds={clientIds}, groupIds={groupIds}, "
			u"productIds={productIds}, productTypes={productTypes}, "
			u"audit: {audit}, license: {license}".format(**locals())
		)

		rb = self._extendedReadBackend
		wb = self.__writeBackend
		aric = wb.backend_getOptions().get('additionalReferentialIntegrityChecks', True)
		if self.__strict:
			wb = self._extendedWriteBackend
		else:
			wb.backend_setOptions({'additionalReferentialIntegrityChecks': False})

		try:
			if serverIds or depotIds or clientIds:
				if not serverIds:
					serverIds = rb.host_getIdents(type='OpsiConfigserver', returnType=list)
				if not depotIds:
					depotIds = rb.host_getIdents(type='OpsiDepotserver', returnType=list)
				if not clientIds:
					clientIds = rb.host_getIdents(type='OpsiClient', returnType=list)

			hostIds = set()
			for serverId in serverIds:
				hostIds.add(serverId)

			for depotId in depotIds:
				hostIds.add(depotId)

			for clientId in clientIds:
				hostIds.add(clientId)

			self.__overallProgressSubject.reset()
			end = self._getNumberOfObjectClassesToProcess(audit, license)
			if self.__cleanupFirst:
				end += 1
			if self.__newServerId:
				end += 1
			self.__overallProgressSubject.setEnd(end)

			if self.__cleanupFirst:
				wb.backend_deleteBase()
				self.__overallProgressSubject.addToState(1)

			wb.backend_createBase()

			productOnDepots = []
			if depotIds:
				productOnDepots = rb.productOnDepot_getObjects(depotId=depotIds, productId=productIds, productType=productTypes)
				productIdsOnDepot = set()
				for productOnDepot in productOnDepots:
					productIdsOnDepot.add(productOnDepot.productId)

				if productIdsOnDepot:
					if not productIds:
						productIds = list(productIdsOnDepot)
					else:
						newProductIds = []
						for productId in productIds:
							if productId in productIdsOnDepot:
								newProductIds.append(productId)
						productIds = newProductIds

			auditClasses = set([
				'AuditHardware',
				'AuditSoftware',
				'AuditHardwareOnHost',
				'AuditSoftwareOnClient'
			])
			licenseClasses = set([
				'LicenseContract',
				'SoftwareLicense',
				'LicensePool',
				'SoftwareLicenseToLicensePool',
				'LicenseOnClient',
				'AuditSoftwareToLicensePool'
			])

			configServer = None
			depotServers = []
			for objClass in self.OBJECT_CLASSES:
				if not audit and objClass in auditClasses:
					continue
				if not license and objClass in licenseClasses:
					continue

				subClasses = [None]
				if objClass == 'Host':
					subClasses = ['OpsiConfigserver', 'OpsiDepotserver', 'OpsiClient']

				methodPrefix = eval("%s.backendMethodPrefix" % objClass)

				self.__overallProgressSubject.setMessage(u"Replicating %s" % objClass)
				self.__currentProgressSubject.setTitle(u"Replicating %s" % objClass)
				for subClass in subClasses:
					filter = {}
					if subClass == 'OpsiConfigserver':
						filter = {'type': subClass, 'id': serverIds}
					elif subClass == 'OpsiDepotserver':
						filter = {'type': subClass, 'id': depotIds}
					elif subClass == 'OpsiClient':
						filter = {'type': subClass, 'id': clientIds}
					elif objClass == 'Group':
						filter = {'type': subClass, 'id': groupIds}
					elif objClass == 'Product':
						filter = {'type': subClass, 'id': productIds}
					elif objClass == 'ProductOnClient':
						filter = {
							'productType': productTypes,
							'productId': productIds,
							'clientId': clientIds
						}
					elif objClass == 'ProductOnDepot':
						filter = {
							'productType': productTypes,
							'productId': productIds,
							'depotId': depotIds
						}
					elif objClass == 'ProductDependency':
						filter = {'productId': productIds}
					elif objClass == 'ProductProperty':
						filter = {'productId': productIds}
					elif objClass == 'ProductPropertyState':
						filter = {
							'productId': productIds,
							'objectId': forceList(hostIds)
						}
					elif objClass == 'ConfigState':
						filter = {'objectId': forceList(hostIds)}
					elif objClass == 'ObjectToGroup':
						if productIds and hostIds:
							objectIds = productIds + forceList(hostIds)
						else:
							objectIds = []

						filter = {'objectId': objectIds}
					elif objClass == 'LicenseOnClient':
						filter = {'clientId': clientIds}

					logger.notice("Replicating class '%s', filter: %s" % (objClass, filter))
					if not subClass:
						subClass = objClass
					Class = eval(subClass)

					self.__currentProgressSubject.reset()
					self.__currentProgressSubject.setMessage(u"Reading objects")
					self.__currentProgressSubject.setEnd(1)
					objs = []

					if objClass == 'ProductOnDepot' and productOnDepots:
						objs = productOnDepots
					else:
						meth = '%s_getObjects' % Class.backendMethodPrefix
						meth = getattr(rb, meth)
						objs = meth(**filter)

					self.__currentProgressSubject.addToState(1)
					if objClass == 'Group':
						# Sort groups
						sortedObjs = []
						groupIds = []
						while True:
							notAddedObjs = []
							for obj in objs:
								if not obj.getParentGroupId() or obj.getParentGroupId() in groupIds:
									if not obj.getParentGroupId():
										logger.debug(u"Adding group '%s' without parent group set" % obj)
									else:
										logger.debug(u"Adding group '%s' with parent group '%s' already added" % (obj, obj.getParentGroupId()))
									sortedObjs.append(obj)
									groupIds.append(obj.getId())
								else:
									logger.debug(u"Cannot add group '%s' parent group '%s' not added yet" % (obj, obj.getParentGroupId()))
									notAddedObjs.append(obj)
							if not notAddedObjs:
								break
							if len(notAddedObjs) == len(objs):
								for obj in notAddedObjs:
									logger.error(u"Failed to add group: %s" % obj)
								break
							objs = notAddedObjs
						objs = sortedObjs

					self.__currentProgressSubject.reset()
					self.__currentProgressSubject.setMessage(u"Writing objects")
					if subClass == 'OpsiConfigserver' and objs:
						configServer = objs[0]
						depotServers.extend(objs)
					if subClass == 'OpsiDepotserver':
						depotServers.extend(objs)

					if self.__strict:
						self.__currentProgressSubject.setEnd(1)
						meth = '%s_createObjects' % Class.backendMethodPrefix
						meth = getattr(wb, meth)
						meth(objs)
						self.__currentProgressSubject.addToState(1)
					else:
						self.__currentProgressSubject.setEnd(len(objs))
						meth = '%s_insertObject' % Class.backendMethodPrefix
						meth = getattr(wb, meth)

						for obj in objs:
							try:
								meth(obj)
							except Exception as e:
								logger.logException(e, LOG_DEBUG)
								logger.error(u"Failed to replicate object %s: %s" % (obj, e))
							self.__currentProgressSubject.addToState(1)
					self.__currentProgressSubject.setState(len(objs))

				self.__overallProgressSubject.addToState(1)

			if self.__newServerId:
				self.__currentProgressSubject.reset()
				self.__currentProgressSubject.setMessage(u"Renaming server")
				self.__currentProgressSubject.setTitle(u"Renaming server")
				self.__currentProgressSubject.setEnd(1)
				if not self.__oldServerId:
					if configServer:
						self.__oldServerId = configServer.id
					elif depotServers:
						self.__oldServerId = depotServers[0].id
					else:
						logger.error(u"No config/depot servers found")

				if self.__oldServerId and self.__oldServerId != self.__newServerId:
					logger.notice(u"Renaming config server {0!r} to {1!r}".format(self.__oldServerId, self.__newServerId))
					renamingBackend = wb
					try:
						renamingBackend.host_renameOpsiDepotserver()
					except TypeError:
						pass  # Missing arguments but method exists
					except AttributeError:
						# Missing the method - need to use extended backend
						renamingBackend = self._extendedWriteBackend

					renamingBackend.host_renameOpsiDepotserver(oldId=self.__oldServerId, newId=self.__newServerId)

					newDepots = []
					for depot in renamingBackend.host_getObjects(type='OpsiDepotserver'):
						hash = depot.toHash()
						del hash['type']
						if depot.id == self.__newServerId:
							newDepots.append(OpsiConfigserver.fromHash(hash))
						else:
							newDepots.append(OpsiDepotserver.fromHash(hash))
					renamingBackend.host_createObjects(newDepots)

				self.__overallProgressSubject.addToState(1)
		finally:
			wb.backend_setOptions({'additionalReferentialIntegrityChecks': aric})

	@classmethod
	def _getNumberOfObjectClassesToProcess(cls, audit=True, license=True):
		auditClasses = set([
			'AuditHardware', 'AuditSoftware', 'AuditHardwareOnHost',
			'AuditSoftwareOnClient'
		])
		licenseManagementClasses = set([
			'LicenseContract', 'SoftwareLicense', 'LicensePool',
			'SoftwareLicenseToLicensePool', 'LicenseOnClient',
			'AuditSoftwareToLicensePool'
		])

		classesToProgress = set(cls.OBJECT_CLASSES)
		if not audit:
			classesToProgress = classesToProgress - auditClasses
		if not license:
			classesToProgress = classesToProgress - licenseManagementClasses

		return len(classesToProgress)
