#!/usr/bin/env python
#-*- coding: utf-8 -*-

class ExtendedBackendTestsMixin(object):
    def testExtendedBackend(self):
        self.backend.backend_setOptions({
            'processProductPriorities':            True,
            'processProductDependencies':          True,
            'addProductOnClientDefaults':          True,
            'addProductPropertyStateDefaults':     True,
            'addConfigStateDefaults':              True,
            'deleteConfigStateIfDefault':          True,
            'returnObjectsOnUpdateAndCreate':      False
        })

        self.setUpClients()
        self.setUpHosts()
        self.createHostsOnBackend()

        self.setUpConfigStates()
        self.createConfigOnBackend()
        self.createConfigStatesOnBackend()

        clients = self.backend.host_getObjects(type='OpsiClient')
        clientToDepots = self.backend.configState_getClientToDepotserver()
        assert len(clientToDepots) == len(
            clients), u"got: '%s', expected: '%s'" % (clientToDepots, len(clients))

        for depotserver in self.depotservers:
            productOnDepots = self.backend.productOnDepot_getObjects(
                depotId=depotserver.id)

            # TODO: richtige Tests
            # for productOnDepot in productOnDepots:
            #     logger.info(u"Got productOnDepot: %s" % productOnDepot)

            # for clientToDepot in clientToDepots:
            #     if (clientToDepot['depotId'] == depotserver.id):
            #         # TODO: richtige Tests
            #         logger.info(u"Got client to depot: %s" % clientToDepot)
