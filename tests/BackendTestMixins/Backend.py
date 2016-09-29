#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
Mixin for testing various backend methods.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import print_function

import random
import time


class BackendPerformanceTestMixin(object):
    def testBackendPerformance(self, clientCount=500, productCount=50):
        return # TODO: make real test

        start = time.time()
        for i in range(clientCount):
            ip = i
            while (ip > 255):
                ip -= 255
            self.backend.host_createOpsiClient(
                id='client%d.test.invalid' % i,
                opsiHostKey='01234567890123456789012345678912',
                description='Client %d' % i,
                notes='No notes',
                hardwareAddress='',
                ipAddress='192.168.0.%d' % ip,
                created=None,
                lastSeen=None
            )
        print(u"Took %.2f seconds to create %d clients" %
                      ((time.time() - start), clientCount))

        start = time.time()
        self.backend.host_getObjects(
            attributes=['id'], ipAddress='192.168.0.100')
        print(u"Took %.2f seconds to search ip address in %d clients" %
                      ((time.time() - start), clientCount))

        #start = time.time()
        #self.backend.host_delete(id = [])
        #logger.notice(u"Took %.2f seconds to delete %d clients" % ((time.time()-start), clientCount))

        start = time.time()
        for i in range(productCount):
            method = random.choice(
                (self.backend.product_createLocalboot, self.backend.product_createNetboot))
            method(
                id='product%d' % i,
                productVersion=random.choice(
                    ('1.0', '2', 'xxx', '3.1', '4')),
                packageVersion=random.choice(
                    ('1', '2', 'y', '3', '10', 11, 22)),
                name='Product %d' % i,
                licenseRequired=random.choice((None, True, False)),
                setupScript=random.choice(('setup.ins', None)),
                uninstallScript=random.choice(('uninstall.ins', None)),
                updateScript=random.choice(('update.ins', None)),
                alwaysScript=random.choice(('always.ins', None)),
                onceScript=random.choice(('once.ins', None)),
                priority=random.choice((-100, -90, -30, 0, 30, 40, 60, 99)),
                description=random.choice(
                    ('Test product %d' % i, 'Some product', '--------', '', None)),
                advice=random.choice(
                    ('Nothing', 'Be careful', '--------', '', None)),
                changelog=None,
                windowsSoftwareIds=None
            )

        print(u"Took %.2f seconds to create %d products" %
                      ((time.time() - start), productCount))

        #start = time.time()
        #self.backend.product_getObjects(attributes = ['id'], uninstallScript = 'uninstall.ins')
        #logger.notice(u"Took %.2f seconds to search uninstall script in %d products" % ((time.time()-start), productCount))

        start = time.time()
        nrOfproductOnDepots = 0
        for product in self.backend.product_getObjects():
            for depotId in self.backend.host_getIdents(type='OpsiDepotserver'):
                nrOfproductOnDepots += 1
                self.backend.productOnDepot_create(
                    productId=product.id,
                    productType=product.getType(),
                    productVersion=product.productVersion,
                    packageVersion=product.packageVersion,
                    depotId=depotId
                )
        print(u"Took %.2f seconds to create %d productsOnDepot" %
                      ((time.time() - start), nrOfproductOnDepots))

        start = time.time()
        nrOfproductOnClients = 0
        for product in self.backend.product_getObjects():
            actions = ['none', None]
            if product.setupScript:
                actions.append('setup')
            if product.uninstallScript:
                actions.append('uninstall')
            if product.onceScript:
                actions.append('once')
            if product.alwaysScript:
                actions.append('always')
            if product.updateScript:
                actions.append('update')
            for clientId in self.backend.host_getIdents(type='OpsiClient'):
                if random.choice((True, False, False, False)):
                    nrOfproductOnClients += 1
                    self.backend.productOnClient_create(
                        productId=product.id,
                        productType=product.getType(),
                        clientId=clientId,
                        installationStatus=random.choice(
                            ('installed', 'not_installed')),
                        actionRequest=random.choice(actions),
                        actionProgress=random.choice(
                            ('installing 30%', 'uninstalling 30%', 'syncing 60%', None, '', 'failed')),
                        productVersion=product.productVersion,
                        packageVersion=product.packageVersion,
                        modificationTime=None
                    )
        print(
            u"Took %.2f seconds to create %d random productsOnClient" %
            ((time.time() - start), nrOfproductOnClients))
