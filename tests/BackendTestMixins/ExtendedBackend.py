#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014 uib GmbH <info@uib.de>

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
Mixin for testing an extended backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""


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
        self.assertEquals(len(clientToDepots), len(clients))

        for depotserver in self.depotservers:
            productOnDepots = self.backend.productOnDepot_getObjects(depotId=depotserver.id)

            # TODO: richtige Tests
            # for productOnDepot in productOnDepots:
            #     logger.info(u"Got productOnDepot: %s" % productOnDepot)

            # for clientToDepot in clientToDepots:
            #     if (clientToDepot['depotId'] == depotserver.id):
            #         # TODO: richtige Tests
            #         logger.info(u"Got client to depot: %s" % clientToDepot)
