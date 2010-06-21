


class NonObjectMethodsMixin(object):



	def test_createDepotServer(self):	
		self.backend.host_createOpsiDepotserver(
				id = 'depot100.uib.local',
				opsiHostKey = '123456789012345678901234567890aa',
				depotLocalUrl = 'file:///opt/pcbin/install',
				depotRemoteUrl = 'smb://depot3.uib.local/opt_pcbin/install',
				repositoryLocalUrl = 'file:///var/lib/opsi/products',
				repositoryRemoteUrl = 'webdavs://depot3.uib.local:4447/products',
				description = 'A depot',
				notes = 'Depot 100',
				hardwareAddress = None,
				ipAddress = None,
				networkAddress = '192.168.100.0/24',
				maxBandwidth = 0)

		
		hosts = self.backend.host_getObjects(id = 'depot100.uib.local')
		self.assertEqual(len(hosts), 1, u"Expected one depotserver with id '%s', but found '%s' on backend." % ('depot100.uib.local', len(hosts)))

	def test_createClient(self):
		
		# FIXME
		#self.backend.productOnDepot_create(
		#	productId      = self.product4.getId(),
		#	productType    = self.product4.getType(),
		#	productVersion = self.product4.getProductVersion(),
		#	packageVersion = self.product4.getPackageVersion(),
		#	depotId        = 'depot100.uib.local',
		#	locked         = False
		#)
		#
		
		self.backend.host_createOpsiClient(
				id = 'client100.uib.local',
				opsiHostKey = None,
				description = 'Client 100',
				notes = 'No notes',
				hardwareAddress = '00:00:01:01:02:02',
				ipAddress = '192.168.0.200',
				created = None,
				lastSeen = None)

		hosts = self.backend.host_getObjects(id = 'client100.uib.local')
		self.assertEqual(len(hosts), 1, u"Expected one client with id '%s', but found '%s' on backend." % ('client100.uib.local', len(hosts)))

	def test_hostIdents(self):
		self.test_createDepotServer()
		self.test_createClient()
		
		selfIdents = []
		for host in self.hosts:
			selfIdents.append(host.getIdent(returnType = 'dict'))
		
		selfIdents.append({'id': 'depot100.uib.local'})
		selfIdents.append({'id': 'client100.uib.local'})
		
		ids = self.backend.host_getIdents()
		self.assertEqual(len(ids), len(selfIdents), u"Expected %s idents, but found '%s' on backend." % (len(selfIdents), len(ids)))

		
		selfIds = map((lambda set: set['id']), selfIdents)
		
		for ident in ids:
			assert found, u"'%s' not in '%s'" % (ident, selfIdents)
			
	def oldNonObjectMethodsMixin(self):
		# Hosts
		

		

		

		

		


		
		ids = self.backend.host_getIdents(id = '*100*')
		assert len(ids) == 2, u"got: '%s', expected: '%s'" % (ids, 2)
		for ident in ids:
			found = False
			for selfIdent in selfIdents:
				if (ident == selfIdent['id']):
					found = True; break
			assert found, u"'%s' not in '%s'" % (ident, selfIdents)
		
		ids = self.backend.host_getIdents(returnType = 'tuple')
		assert len(ids) == len(selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
		for ident in ids:
			found = False
			for selfIdent in selfIdents:
				if (ident[0] == selfIdent['id']):
					found = True; break
			assert found, u"'%s' not in '%s'" % (ident, selfIdents)
		
		ids = self.backend.host_getIdents(returnType = 'list')
		assert len(ids) == len(selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
		for ident in ids:
			found = False
			for selfIdent in selfIdents:
				if (ident[0] == selfIdent['id']):
					found = True; break
			assert found, u"'%s' not in '%s'" % (ident, selfIdents)
		
		ids = self.backend.host_getIdents(returnType = 'dict')
		assert len(ids) == len(selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
		for ident in ids:
			found = False
			for selfIdent in selfIdents:
				if (ident['id'] == selfIdent['id']):
					found = True; break
			assert found, u"'%s' not in '%s'" % (ident, selfIdents)
		
		
		
		selfIdents = []
		for config in self.configs:
			selfIdents.append(config.getIdent(returnType = 'dict'))
		
		ids = self.backend.config_getIdents()
		assert len(ids) == len(selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
		for ident in ids:
			found = False
			for selfIdent in selfIdents:
				if (ident == selfIdent['id']):
					found = True; break
			assert found, u"'%s' not in '%s'" % (ident, selfIdents)
		
		
		# some deleted?
		self.backend.configState_createObjects(self.configStates)
		
		selfIdents = []
		for configState in self.configStates:
			selfIdents.append(configState.getIdent(returnType = 'dict'))
		
		ids = self.backend.configState_getIdents()
		assert len(ids) == len(selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
		for ident in ids:
			i = ident.split(';')
			found = False
			for selfIdent in selfIdents:
				if (i[0] == selfIdent['configId']) and (i[1] == selfIdent['objectId']):
					found = True; break
			assert found, u"'%s' not in '%s'" % (ident, selfIdents)
		
		
		
		
		
		
		
		
		
		
		
		ids = self.backend.product_getIdents()
		ids = self.backend.productProperty_getIdents()
		ids = self.backend.productOnDepot_getIdents()
		ids = self.backend.productOnDepot_getIdents()
		ids = self.backend.productPropertyState_getIdents()
		ids = self.backend.productPropertyState_getIdents(returnType = 'tuple')
		ids = self.backend.productPropertyState_getIdents(returnType = 'list')
		ids = self.backend.productPropertyState_getIdents(returnType = 'dict')
		ids = self.backend.group_getIdents()
		ids = self.backend.objectToGroup_getIdents()
		ids = self.backend.product_getIdents(id = '*product*')
		
		# TODO: assertions
		result = self.backend.backend_searchObjects('(&(objectClass=Host)(type=OpsiDepotserver))')
		logger.notice(result)
		result = self.backend.backend_searchObjects('(&(&(objectClass=Host)(type=OpsiDepotserver))(objectClass=Host))')
		logger.notice(result)
		result = self.backend.backend_searchObjects('(|(&(objectClass=OpsiClient)(id=client1*))(&(objectClass=OpsiClient)(id=client2*)))')
		logger.notice(result)
		result = self.backend.backend_searchObjects('(&(&(objectClass=OpsiClient))(&(objectClass=ProductOnClient)(installationStatus=installed))(&(objectClass=ProductOnClient)(productId=product1)))')
		logger.notice(result)
		result = self.backend.backend_searchObjects('(&(&(objectClass=OpsiClient))(&(objectClass=ProductOnClient)(installationStatus=installed))(|(&(objectClass=ProductOnClient)(productId=product1))(&(objectClass=ProductOnClient)(productId=product2))))')
		logger.notice(result)
		result = self.backend.backend_searchObjects('(&(objectClass=OpsiClient)(&(objectClass=ProductOnClient)(installationStatus=installed))(&(objectClass=ProductOnClient)(productId=product1)))')
		logger.notice(result)
		result = self.backend.backend_searchObjects('(&(objectClass=Host)(description=T*))')
		logger.notice(result)
		result = self.backend.backend_searchObjects('(&(objectClass=Host)(description=*))')
		logger.notice(result)
		result = self.backend.backend_searchObjects('(&(&(objectClass=OpsiClient)(ipAddress=192*))(&(objectClass=ProductOnClient)(installationStatus=installed)))')
		logger.notice(result)
		result = self.backend.backend_searchObjects('(&(&(objectClass=Product)(description=*))(&(objectClass=ProductOnClient)(installationStatus=installed)))')
		logger.notice(result)
		
		#self.backend.host_delete(id = [])
		#hosts = self.backend.host_getObjects()
		#assert len(hosts) == 0