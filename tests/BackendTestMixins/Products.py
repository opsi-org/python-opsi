#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2016 uib GmbH <info@uib.de>

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
Backend functionality for testing the functionality of working with products.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

from OPSI.Object import (BoolProductProperty, LocalbootProduct, NetbootProduct,
    OpsiClient, ProductDependency, ProductOnClient, ProductOnDepot,
    ProductPropertyState, UnicodeProductProperty)
from OPSI.Types import forceHostId
from OPSI.Util import getfqdn

from .Hosts import HostsMixin, getConfigServer, getDepotServers
from .Clients import ClientsMixin, getClients


def getProducts():
    return list(getLocalbootProducts()) + [getNetbootProduct()]


def getNetbootProduct():
    netbootProduct = NetbootProduct(
        id='product1',
        name=u'Product 1',
        productVersion='1.0',
        packageVersion=1,
        licenseRequired=True,
        setupScript="setup.py",
        uninstallScript=None,
        updateScript="update.py",
        alwaysScript=None,
        onceScript=None,
        priority='100',
        description="Nothing",
        advice=u"No advice",
        productClassIds=[],
        windowsSoftwareIds=[
            '{be21bd07-eb19-44e4-893a-fa4e44e5f806}', 'product1'],
        pxeConfigTemplate='special'
    )

    return netbootProduct


def getLocalbootProducts():
    product2 = LocalbootProduct(
        id='product2',
        name=u'Product 2',
        productVersion='2.0',
        packageVersion='test',
        licenseRequired=False,
        setupScript="setup.ins",
        uninstallScript=u"uninstall.ins",
        updateScript="update.ins",
        alwaysScript=None,
        onceScript=None,
        priority=0,
        description=None,
        advice="",
        productClassIds=[],
        windowsSoftwareIds=['{98723-7898adf2-287aab}', 'xxxxxxxx']
    )

    product3 = LocalbootProduct(
        id='product3',
        name=u'Product 3',
        productVersion=3,
        packageVersion=1,
        licenseRequired=True,
        setupScript="setup.ins",
        uninstallScript=None,
        updateScript=None,
        alwaysScript=None,
        onceScript=None,
        priority=100,
        description="---",
        advice="---",
        productClassIds=[],
        windowsSoftwareIds=[]
    )

    product4 = LocalbootProduct(
        id='product4',
        name=u'Product 4',
        productVersion="3.0",
        packageVersion=24,
        licenseRequired=False,
        setupScript="setup.ins",
        uninstallScript="uninstall.ins",
        updateScript=None,
        alwaysScript=None,
        onceScript=None,
        priority=0,
        description="",
        advice="",
        productClassIds=[],
        windowsSoftwareIds=[]
    )

    product5 = LocalbootProduct(
        id='product4',
        name=u'Product 4',
        productVersion="3.0",
        packageVersion=25,
        licenseRequired=False,
        setupScript="setup.ins",
        uninstallScript="uninstall.ins",
        updateScript=None,
        alwaysScript=None,
        onceScript=None,
        priority=0,
        description="",
        advice="",
        productClassIds=[],
        windowsSoftwareIds=[]
    )

    product6 = LocalbootProduct(
        id='product6',
        name=u'Product 6',
        productVersion="1.0",
        packageVersion=1,
        licenseRequired=False,
        setupScript="setup.ins",
        uninstallScript="uninstall.ins",
        updateScript=None,
        alwaysScript=None,
        onceScript=None,
        priority=0,
        description="",
        advice="",
        productClassIds=[],
        windowsSoftwareIds=[]
    )

    product7 = LocalbootProduct(
        id='product7',
        name=u'Product 7',
        productVersion="1.0",
        packageVersion=1,
        licenseRequired=False,
        setupScript="setup.ins",
        uninstallScript="uninstall.ins",
        updateScript=None,
        alwaysScript=None,
        onceScript=None,
        priority=0,
        description="",
        advice="",
        productClassIds=[],
        windowsSoftwareIds=[]
    )

    product8 = LocalbootProduct(
        id='product8',
        name=u'Product 8',
        productVersion="1.0",
        packageVersion=2,
        licenseRequired=False,
        setupScript="setup.ins",
        uninstallScript="uninstall.ins",
        updateScript=None,
        alwaysScript=None,
        onceScript=None,
        customScript="custom.ins",
        priority=0,
        description="",
        advice="",
        productClassIds=[],
        windowsSoftwareIds=[]
    )

    product9 = LocalbootProduct(
        id='product9',
        name=(u'This is a very long name with 128 characters to test the '
              u'creation of long product names that should work now but '
              u'were limited b4'),
        productVersion="1.0",
        packageVersion=2,
        licenseRequired=False,
        setupScript="setup.ins",
        uninstallScript="uninstall.ins",
        updateScript=None,
        alwaysScript=None,
        onceScript=None,
        customScript="custom.ins",
        priority=0,
        description="",
        advice="",
        productClassIds=[],
        windowsSoftwareIds=[]
    )

    return (product2, product3, product4, product5, product6, product7,
            product8, product9)


def getProductDepdencies(products):
    print("Got {0} products: {1!r}".format(len(products), products))

    product2, product3, product4, _, product6, product7, _, product9 = products[1:9]
    productDependency1 = ProductDependency(
        productId=product2.id,
        productVersion=product2.productVersion,
        packageVersion=product2.packageVersion,
        productAction='setup',
        requiredProductId=product3.id,
        requiredProductVersion=product3.productVersion,
        requiredPackageVersion=product3.packageVersion,
        requiredAction='setup',
        requiredInstallationStatus=None,
        requirementType='before'
    )

    productDependency2 = ProductDependency(
        productId=product2.id,
        productVersion=product2.productVersion,
        packageVersion=product2.packageVersion,
        productAction='setup',
        requiredProductId=product4.id,
        requiredProductVersion=None,
        requiredPackageVersion=None,
        requiredAction=None,
        requiredInstallationStatus='installed',
        requirementType='after'
    )

    productDependency3 = ProductDependency(
        productId=product6.id,
        productVersion=product6.productVersion,
        packageVersion=product6.packageVersion,
        productAction='setup',
        requiredProductId=product7.id,
        requiredProductVersion=product7.productVersion,
        requiredPackageVersion=product7.packageVersion,
        requiredAction=None,
        requiredInstallationStatus='installed',
        requirementType='after'
    )

    productDependency4 = ProductDependency(
        productId=product7.id,
        productVersion=product7.productVersion,
        packageVersion=product7.packageVersion,
        productAction='setup',
        requiredProductId=product9.id,
        requiredProductVersion=None,
        requiredPackageVersion=None,
        requiredAction=None,
        requiredInstallationStatus='installed',
        requirementType='after'
    )

    return (productDependency1, productDependency2, productDependency3, productDependency4)


def getProductProperties(products):
    print("getProductProperties: Got {0} products: {1!r}".format(len(products), products))

    product1, _, product3 = products[:3]

    # TODO: turn this into tests?
    productProperty1 = UnicodeProductProperty(
        productId=product1.id,
        productVersion=product1.productVersion,
        packageVersion=product1.packageVersion,
        propertyId="productProperty1",
        description='Test product property (unicode)',
        possibleValues=['unicode1', 'unicode2', 'unicode3'],
        defaultValues=['unicode1', 'unicode3'],
        editable=True,
        multiValue=True
    )

    # TODO: turn this into tests?
    productProperty2 = BoolProductProperty(
        productId=product1.id,
        productVersion=product1.productVersion,
        packageVersion=product1.packageVersion,
        propertyId="productProperty2",
        description='Test product property 2 (bool)',
        defaultValues=True
    )

    productProperty3 = BoolProductProperty(
        productId=product3.id,
        productVersion=product3.productVersion,
        packageVersion=product3.packageVersion,
        propertyId=u"productProperty3",
        description=u'Test product property 3 (bool)',
        defaultValues=False
    )

    productProperty4 = UnicodeProductProperty(
        productId=product1.id,
        productVersion=product1.productVersion,
        packageVersion=product1.packageVersion,
        propertyId=u"i386_dir",
        description=u'i386 dir to use as installation source',
        possibleValues=["i386"],
        defaultValues=["i386"],
        editable=True,
        multiValue=False
    )

    return productProperty1, productProperty2, productProperty3, productProperty4


def getProductsOnDepot(products, configServer, depotServer):
    print("getProductsOnDepot: Got {0} products: {1!r}".format(len(products), products))

    product1, product2, product3, _, product5, product6, product7, product8, product9 = products[:9]
    depotserver1, depotserver2 = depotServer[:2]

    productOnDepot1 = ProductOnDepot(
        productId=product1.getId(),
        productType=product1.getType(),
        productVersion=product1.getProductVersion(),
        packageVersion=product1.getPackageVersion(),
        depotId=depotserver1.getId(),
        locked=False
    )

    productOnDepot2 = ProductOnDepot(
        productId=product2.getId(),
        productType=product2.getType(),
        productVersion=product2.getProductVersion(),
        packageVersion=product2.getPackageVersion(),
        depotId=depotserver1.getId(),
        locked=False
    )

    productOnDepot3 = ProductOnDepot(
        productId=product3.getId(),
        productType=product3.getType(),
        productVersion=product3.getProductVersion(),
        packageVersion=product3.getPackageVersion(),
        depotId=depotserver1.getId(),
        locked=False
    )

    productOnDepot4 = ProductOnDepot(
        productId=product3.getId(),
        productType=product3.getType(),
        productVersion=product3.getProductVersion(),
        packageVersion=product3.getPackageVersion(),
        depotId=configServer.getId(),
        locked=False
    )

    productOnDepot5 = ProductOnDepot(
        productId=product5.getId(),
        productType=product5.getType(),
        productVersion=product5.getProductVersion(),
        packageVersion=product5.getPackageVersion(),
        depotId=configServer.getId(),
        locked=False
    )

    productOnDepot6 = ProductOnDepot(
        productId=product6.getId(),
        productType=product6.getType(),
        productVersion=product6.getProductVersion(),
        packageVersion=product6.getPackageVersion(),
        depotId=depotserver1.getId(),
        locked=False
    )

    productOnDepot7 = ProductOnDepot(
        productId=product6.getId(),
        productType=product6.getType(),
        productVersion=product6.getProductVersion(),
        packageVersion=product6.getPackageVersion(),
        depotId=depotserver2.getId(),
        locked=False
    )

    productOnDepot8 = ProductOnDepot(
        productId=product7.getId(),
        productType=product7.getType(),
        productVersion=product7.getProductVersion(),
        packageVersion=product7.getPackageVersion(),
        depotId=depotserver1.getId(),
        locked=False
    )

    productOnDepot9 = ProductOnDepot(
        productId=product8.getId(),
        productType=product8.getType(),
        productVersion=product8.getProductVersion(),
        packageVersion=product8.getPackageVersion(),
        depotId=depotserver2.getId(),
        locked=False
    )

    productOnDepot10 = ProductOnDepot(
        productId=product9.getId(),
        productType=product9.getType(),
        productVersion=product9.getProductVersion(),
        packageVersion=product9.getPackageVersion(),
        depotId=depotserver1.getId(),
        locked=False
    )

    productOnDepot11 = ProductOnDepot(
        productId=product9.getId(),
        productType=product9.getType(),
        productVersion=product9.getProductVersion(),
        packageVersion=product9.getPackageVersion(),
        depotId=depotserver2.getId(),
        locked=False
    )

    return (productOnDepot1, productOnDepot2, productOnDepot3, productOnDepot4,
            productOnDepot5, productOnDepot6, productOnDepot7, productOnDepot8,
            productOnDepot9, productOnDepot10, productOnDepot11)


def getProductsOnClients(products, clients):
    product1, product2 = products[:2]
    client1, _, client3 = clients[:3]

    productOnClient1 = ProductOnClient(
        productId=product1.getId(),
        productType=product1.getType(),
        clientId=client1.getId(),
        installationStatus='installed',
        actionRequest='setup',
        actionProgress='',
        productVersion=product1.getProductVersion(),
        packageVersion=product1.getPackageVersion(),
        modificationTime='2009-07-01 12:00:00'
    )

    productOnClient2 = ProductOnClient(
        productId=product2.getId(),
        productType=product2.getType(),
        clientId=client1.getId(),
        installationStatus='installed',
        actionRequest='uninstall',
        actionProgress='',
        productVersion=product2.getProductVersion(),
        packageVersion=product2.getPackageVersion()
    )

    productOnClient3 = ProductOnClient(
        productId=product2.getId(),
        productType=product2.getType(),
        clientId=client3.getId(),
        installationStatus='installed',
        actionRequest='setup',
        actionProgress='running',
        productVersion=product2.getProductVersion(),
        packageVersion=product2.getPackageVersion()
    )

    productOnClient4 = ProductOnClient(
        productId=product1.getId(),
        productType=product1.getType(),
        clientId=client3.getId(),
        targetConfiguration='installed',
        installationStatus='installed',
        actionRequest='none',
        lastAction='setup',
        actionProgress='',
        actionResult='successful',
        productVersion=product1.getProductVersion(),
        packageVersion=product1.getPackageVersion()
    )

    return productOnClient1, productOnClient2, productOnClient3, productOnClient4


def getProductPropertyStates(productProperties, depotServer, clients):
    productProperty1, productProperty2 = productProperties[:2]
    depotserver1, depotserver2 = depotServer[:2]
    client1, client2 = clients[:2]

    # TODO: test?
    productPropertyState1 = ProductPropertyState(
        productId=productProperty1.getProductId(),
        propertyId=productProperty1.getPropertyId(),
        objectId=depotserver1.getId(),
        values='unicode-depot-default'
    )

    # TODO: test?
    productPropertyState2 = ProductPropertyState(
        productId=productProperty2.getProductId(),
        propertyId=productProperty2.getPropertyId(),
        objectId=depotserver1.getId(),
        values=[True]
    )

    # TODO: test?
    productPropertyState3 = ProductPropertyState(
        productId=productProperty2.getProductId(),
        propertyId=productProperty2.getPropertyId(),
        objectId=depotserver2.getId(),
        values=False
    )

    # TODO: test?
    productPropertyState4 = ProductPropertyState(
        productId=productProperty1.getProductId(),
        propertyId=productProperty1.getPropertyId(),
        objectId=client1.getId(),
        values='unicode1'
    )

    # TODO: test?
    productPropertyState5 = ProductPropertyState(
        productId=productProperty2.getProductId(),
        propertyId=productProperty2.getPropertyId(),
        objectId=client1.getId(),
        values=[False]
    )

    # TODO: test?
    productPropertyState6 = ProductPropertyState(
        productId=productProperty2.getProductId(),
        propertyId=productProperty2.getPropertyId(),
        objectId=client2.getId(),
        values=True
    )

    return (productPropertyState1, productPropertyState2, productPropertyState3,
            productPropertyState4, productPropertyState5, productPropertyState6)


class ProductsMixin(object):
    def setUpProducts(self):
        self.product1 = getNetbootProduct()
        self.netbootProducts = [self.product1]

        (self.product2, self.product3, self.product4, self.product5,
         self.product6, self.product7, self.product8,
         self.product9) = getLocalbootProducts()

        self.localbootProducts = [self.product2, self.product3, self.product4,
                                  self.product5, self.product6, self.product7,
                                  self.product8, self.product9]

        if not hasattr(self, 'products'):
            self.products = []
        self.products.extend(self.netbootProducts)
        self.products.extend(self.localbootProducts)

    def createProductsOnBackend(self):
        for product in self.products:
            product.setDefaults()

        self.backend.product_createObjects(self.products)


class ProductsTestMixin(ProductsMixin):
    def testProductMethods(self):
        self.setUpProducts()

        self.createProductsOnBackend()

        products = self.backend.product_getObjects()
        assert len(products) == len(self.products), u"got: '%s', expected: '%s'" % (
            products, len(self.products))

        products = self.backend.product_getObjects(type='Product')
        assert len(products) == len(self.products), u"got: '%s', expected: '%s'" % (
            products, len(self.products))

        products = self.backend.product_getObjects(
            type=self.localbootProducts[0].getType())
        assert len(products) == len(self.localbootProducts), u"got: '%s', expected: '%s'" % (
            products, len(self.localbootProducts))
        ids = []
        for product in products:
            ids.append(product.getId())
        for product in self.localbootProducts:
            assert product.id in ids, u"'%s' not in '%s'" % (product.id, ids)

        for product in products:
            for p in self.products:
                if (product.id == p.id) and (product.productVersion == p.productVersion) and (product.packageVersion == p.packageVersion):
                    assert product == p, u"got: '%s', expected: '%s'" % (
                        product.toHash(), p.toHash())

        self.product2.setName(u'Product 2 updated')
        self.product2.setPriority(60)
        products = self.backend.product_updateObject(self.product2)
        products = self.backend.product_getObjects(
            attributes=['name', 'priority'], id='product2')
        assert len(products) == 1, u"got: '%s', expected: '%s'" % (products, 1)
        assert products[0].getName() == u'Product 2 updated', u"got: '%s', expected: '%s'" % (
            products[0].getName(), u'Product 2 updated')
        assert products[0].getPriority() == 60, u"got: '%s', expected: '60'" % products[
            0].getPriority()


class ProductPropertiesMixin(ProductsMixin):
    def setUpProductProperties(self):
        self.setUpProducts()

        (self.productProperty1, self.productProperty2,
         self.productProperty3, self.productProperty4) = getProductProperties(self.products)

        self.productProperties = [
            self.productProperty1, self.productProperty2,
            self.productProperty3, self.productProperty4
        ]

    def createProductPropertiesOnBackend(self):
        self.backend.productProperty_createObjects(self.productProperties)


class ProductPropertyStatesMixin(ProductPropertiesMixin):
    def setUpProductPropertyStates(self):
        self.setUpProductProperties()
        self.setUpHosts()
        self.setUpClients()

        (self.productPropertyState1, self.productPropertyState2,
         self.productPropertyState3, self.productPropertyState4,
         self.productPropertyState5, self.productPropertyState6) = getProductPropertyStates(self.productProperties, self.depotservers, self.clients)

        self.productPropertyStates = [
            self.productPropertyState1, self.productPropertyState2,
            self.productPropertyState3, self.productPropertyState4,
            self.productPropertyState5, self.productPropertyState6
        ]


class ProductPropertyStateTestsMixin(ProductPropertyStatesMixin):
    def testProductPropertyStateMethods(self):
        self.setUpProductPropertyStates()

        self.createHostsOnBackend()
        self.createProductsOnBackend()
        self.createProductPropertiesOnBackend()

        self.backend.productPropertyState_createObjects(self.productPropertyStates)

        productPropertyStates = self.backend.productPropertyState_getObjects()
        self.assertEquals(len(productPropertyStates), len(self.productPropertyStates),
            u"Expected {0} objects in the backend but got {1} instead.".format(len(self.productPropertyStates), len(productPropertyStates))
        )

        self.backend.productPropertyState_deleteObjects(self.productPropertyState2)

        productPropertyStates = self.backend.productPropertyState_getObjects()
        assert len(productPropertyStates) == len(self.productPropertyStates) - \
            1, u"got: '%s', expected: '%s'" % (
                productPropertyStates, len(self.productPropertyStates) - 1)

        self.backend.productPropertyState_insertObject(
            self.productPropertyState2)
        productPropertyStates = self.backend.productPropertyState_getObjects()
        assert len(productPropertyStates) == len(self.productPropertyStates), u"got: '%s', expected: '%s'" % (
            productPropertyStates, len(self.productPropertyStates))


class ProductPropertiesTestMixin(ProductPropertiesMixin):

    def testProductAndPropertyWithSameName(self):
        """
        Product and property may have the same name.
        """
        product1 = LocalbootProduct(
            id='cbk',
            name=u'Comeback Kid',
            productVersion='1.0',
            packageVersion="2",
        )

        productProperty1 = BoolProductProperty(
            productId='cbk',
            productVersion=product1.productVersion,
            packageVersion=product1.packageVersion,
            propertyId="dep",
            defaultValues=True,
        )

        self.backend.product_createObjects([product1])
        self.backend.productProperty_createObjects([productProperty1])

        product2 = LocalbootProduct(
            id='dep',
            name=u'The Dillinger Escape Plan',
            productVersion='11.1',
            packageVersion=2,
        )

        productProperty2 = BoolProductProperty(
            productId=product2.id,
            productVersion=product2.productVersion,
            packageVersion=product2.packageVersion,
            propertyId="cbk",
            defaultValues=True,
        )

        self.backend.product_createObjects([product2])
        self.backend.productProperty_createObjects([productProperty2])

        properties = self.backend.productProperty_getObjects(productId='cbk')

        print("Used backend: {0}".format(self.backend))
        self.assertEqual(1, len(properties))
        prop = properties[0]

        self.assertEqual("dep", prop.propertyId)
        self.assertEqual("cbk", prop.productId)
        self.assertEqual("1.0", prop.productVersion)
        self.assertEqual("2", prop.packageVersion)
        self.assertEqual([True], prop.defaultValues)

    def testProductPropertyMethods(self):
        self.setUpProductProperties()

        self.createProductsOnBackend()

        self.backend.productProperty_createObjects(self.productProperties)
        productProperties = self.backend.productProperty_getObjects()
        assert len(productProperties) == len(self.productProperties), u"got: '%s', expected: '%s'" % (
            productProperties, len(self.productProperties))

        for productProperty in productProperties:
            for p in self.productProperties:
                if (productProperty.productId == p.productId)           and (productProperty.propertyId == p.propertyId) and \
                   (productProperty.productVersion == p.productVersion) and (productProperty.packageVersion == p.packageVersion):
                    productProperty = productProperty.toHash()
                    p = p.toHash()
                    for (attribute, value) in p.items():
                        if value is not None:
                            if isinstance(value, list):
                                for v in value:
                                    assert v in productProperty[attribute], u"'%s' not in '%s'" % (
                                        v, productProperty[attribute])
                            else:
                                assert value == productProperty[attribute], u"got: '%s', expected: '%s'" % (
                                    productProperty[attribute], value)
                    break

        self.backend.productProperty_createObjects(self.productProperties)
        productProperties = self.backend.productProperty_getObjects()
        assert len(productProperties) == len(self.productProperties), u"got: '%s', expected: '%s'" % (
            productProperties, len(self.productProperties))

        self.productProperty2.setDescription(u'updatedfortest')
        self.backend.productProperty_updateObject(self.productProperty2)
        productProperties = self.backend.productProperty_getObjects(
            attributes=[],
            description=u'updatedfortest')

        assert len(productProperties) == 1, u"got: '%s', expected: '%s'" % (
            productProperties,  1)
        assert productProperties[0].getDescription() == u'updatedfortest', u"got: '%s', expected: '%s'" % (
            productProperties[0].getDescription(), u'updatedfortest')

        self.backend.productProperty_deleteObjects(self.productProperty2)
        productProperties = self.backend.productProperty_getObjects()
        assert len(productProperties) == len(self.productProperties) - \
            1, u"got: '%s', expected: '%s'" % (
                productProperties, len(self.productProperties) - 1)

        self.backend.productProperty_createObjects(self.productProperty2)
        self.backend.productProperty_createObjects(
            [self.productProperty4, self.productProperty1, self.productProperty4, self.productProperty4, self.productProperty4])
        productProperties = self.backend.productProperty_getObjects()
        assert len(productProperties) == len(self.productProperties), u"got: '%s', expected: '%s'" % (
            productProperties, len(self.productProperties))


    def testProductPropertyStates(self):
        self.setUpProductProperties()

        self.createProductsOnBackend()
        self.createProductPropertiesOnBackend()

        pps0 = ProductPropertyState(
            productId=self.productProperty1.getProductId(),
            propertyId=self.productProperty1.getPropertyId(),
            objectId='kaputtesdepot.dom.local'
        )

        self.assertRaises(Exception, self.backend.productPropertyState_insertObject, pps0)

    def testFixing1554(self):
        """
        The backend must not ignore product property states of a product when \
the name of the product equals the name of a product property.

        The setup here is that there is a product with properties.
        One of these properties has the same ID as the name of a different
        product. For this product all properties must be shown.
        """
        serverFqdn = forceHostId(getfqdn())  # using local FQDN
        depotserver1 = {
            "isMasterDepot" : True,
            "type" : "OpsiConfigserver",
            "id" : serverFqdn,
        }

        product1 = {
            "name" : "Windows Customizing",
            "packageVersion" : "1",
            "productVersion" : "4.0.1",
            "type" : "LocalbootProduct",
            "id" : "config-win-base",
        }

        product2 = {
            "name" : "Software fuer Windows-Clients",
            "packageVersion" : "3",
            "productVersion" : "2.0",
            "type" : "LocalbootProduct",
            "id" : "clientprodukte",
        }

        productProperty1 = {
            "description" : "Masterflag: Do Explorer Settings",
            "possibleValues" : ["0", "1"],
            "defaultValues" : ["1"],
            "productVersion" : "4.0.1",
            "packageVersion" : "1",
            "type" : "UnicodeProductProperty",
            "propertyId" : "flag_explorer",
            "productId" : "config-win-base"
        }

        productProperty2 = {
            "description" : "config-win-base installieren (empfohlen)",
            "possibleValues" : ["ja", "nein"],
            "defaultValues" : ["ja"],
            "productVersion" : "2.0",
            "packageVersion" : "3",
            "type" : "UnicodeProductProperty",
            "propertyId" : "config-win-base",
            "productId" : "clientprodukte"
        }

        pps1 = {
            "objectId" : serverFqdn,
            "values" : ["1"],
            "type" : "ProductPropertyState",
            "propertyId" : "flag_explorer",
            "productId" : "config-win-base"
        }

        pps2 = {
            "objectId" : serverFqdn,
            "values" : ["ja"],
            "type" : "ProductPropertyState",
            "propertyId" : "config-win-base",
            "productId" : "clientprodukte"
        }

        self.backend.product_createObjects([product1, product2])
        self.backend.productProperty_createObjects([productProperty1, productProperty2])
        self.backend.host_createObjects(depotserver1)
        self.backend.productPropertyState_createObjects([pps1])

        product1Properties = self.backend.productProperty_getObjects(productId=product1['id'])
        self.assertTrue(product1Properties)
        product2Properties = self.backend.productProperty_getObjects(productId=product2['id'])
        self.assertTrue(product2Properties)

        # Only one productPropertyState
        property1States = self.backend.productPropertyState_getObjects(productId=product1['id'])
        self.assertTrue(property1States)

        # Upping the game by inserting another productPropertyState
        self.backend.productPropertyState_createObjects([pps2])

        property1States = self.backend.productPropertyState_getObjects(productId=product1['id'])
        self.assertTrue(property1States)
        self.assertEquals(len(property1States), 1)
        property2States = self.backend.productPropertyState_getObjects(productId=product2['id'])
        self.assertTrue(property2States)
        self.assertEquals(len(property2States), 1)
        propertyStatesForServer = self.backend.productPropertyState_getObjects(objectId=depotserver1['id'], productId=product1['id'])
        self.assertTrue(propertyStatesForServer)
        self.assertEquals(len(property2States), 1)
        propertyStatesForServer = self.backend.productPropertyState_getObjects(objectId=depotserver1['id'], productId=product2['id'])
        self.assertTrue(propertyStatesForServer)
        self.assertEquals(len(property2States), 1)
        propertyStatesForServer = self.backend.productPropertyState_getObjects(objectId=depotserver1['id'])
        self.assertTrue(propertyStatesForServer)
        self.assertEquals(len(propertyStatesForServer), 2)

    def test_insertFaultyPropertyState(self):
        product = LocalbootProduct('p1', productVersion=1, packageVersion=1)
        productProp = BoolProductProperty(
            productId=product.id,
            productVersion=product.productVersion,
            packageVersion=product.packageVersion,
            propertyId="testtest",
            defaultValues=True,
        )

        self.backend.product_createObjects(product)
        self.backend.productProperty_createObjects(productProp)

        pps0 = ProductPropertyState(
            productId=productProp.getProductId(),
            propertyId=productProp.getPropertyId(),
            objectId='kaputtesdepot.dom.local'
        )
        self.assertRaises(Exception, self.backend.productPropertyState_insertObject, pps0)

    def test_getProductPropertyStatesFromBackend(self):
        products = getProducts()
        clients = getClients()
        depotServer = getDepotServers()
        properties = getProductProperties(products)
        pps = getProductPropertyStates(properties, depotServer, clients)

        self.backend.host_createObjects(clients)
        self.backend.host_createObjects(depotServer)
        self.backend.product_createObjects(products)
        self.backend.productProperty_createObjects(properties)
        self.backend.productPropertyState_createObjects(pps)

        productPropertyStates = self.backend.productPropertyState_getObjects()
        self.assertEqual(len(pps), len(productPropertyStates))

        for state in pps:
            self.assertIn(state, productPropertyStates)

    def test_deleteProductPropertyState(self):
        products = getProducts()
        clients = getClients()
        depotServer = getDepotServers()
        properties = getProductProperties(products)
        pps = getProductPropertyStates(properties, depotServer, clients)

        self.backend.host_createObjects(clients)
        self.backend.host_createObjects(depotServer)
        self.backend.product_createObjects(products)
        self.backend.productProperty_createObjects(properties)
        self.backend.productPropertyState_createObjects(pps)

        productPropertyState2 = pps[1]
        self.backend.productPropertyState_deleteObjects(productPropertyState2)
        productPropertyStates = self.backend.productPropertyState_getObjects()
        self.assertNotIn(productPropertyState2, productPropertyStates)

    def test_insertProductPropertyState(self):
        self.backend.productPropertyState_deleteObjects(self.backend.productPropertyState_getObjects())

        client = OpsiClient(id='someclient.test.invalid')
        product = LocalbootProduct('p1', productVersion=1, packageVersion=1)
        productProp = BoolProductProperty(
            productId=product.id,
            productVersion=product.productVersion,
            packageVersion=product.packageVersion,
            propertyId="testtest",
            defaultValues=True,
        )
        pps = ProductPropertyState(
            productId=productProp.getProductId(),
            propertyId=productProp.getPropertyId(),
            objectId=client.id
        )

        self.backend.host_createObjects(client)
        self.backend.product_createObjects(product)
        self.backend.productProperty_createObjects(productProp)
        self.backend.productPropertyState_insertObject(pps)

        productPropertyStates = self.backend.productPropertyState_getObjects()
        self.assertIn(pps, productPropertyStates)
        self.assertEqual(1, len(productPropertyStates))


class ProductDependenciesMixin(ProductsMixin):
    def setUpProductDependencies(self):
        self.setUpProducts()

        (self.productDependency1, self.productDependency2,
         self.productDependency3, self.productDependency4) = getProductDepdencies(self.products)

        self.productDependencies = [
            self.productDependency1, self.productDependency2,
            self.productDependency3, self.productDependency4
        ]

    def createProductDepedenciesOnBackend(self):
        self.backend.productDependency_createObjects(self.productDependencies)


class ProductDependenciesTestMixin(ProductDependenciesMixin):
    def testProductDependencies(self):
        self.setUpProductDependencies()

        self.createProductsOnBackend()
        self.createProductDepedenciesOnBackend()

        productDependencies = self.backend.productDependency_getObjects()
        assert len(productDependencies) == len(self.productDependencies), u"got: '%s', expected: '%s'" % (
            productDependencies, len(self.productDependencies))

        self.productDependency2.requiredProductVersion = "2.0"
        self.productDependency2.requirementType = None
        self.backend.productDependency_updateObject(self.productDependency2)
        productDependencies = self.backend.productDependency_getObjects()

        assert len(productDependencies) == len(self.productDependencies), u"got: '%s', expected: '%s'" % (
            productDependencies, len(self.productDependencies))
        for productDependency in productDependencies:
            if productDependency.getIdent() == self.productDependency2.getIdent():
                assert productDependency.getRequiredProductVersion() == "2.0", u"got: '%s', expected: '%s'" % (
                    productDependency.getRequiredProductVersion(), "2.0")
                assert productDependency.getRequirementType() == 'after', u"got: '%s', expected: '%s'" % (
                    productDependency.getRequirementType(), 'after')
        #       self.productDependency2.requirementType = 'after'

        self.backend.productDependency_deleteObjects(self.productDependency2)
        productDependencies = self.backend.productDependency_getObjects()
        assert len(productDependencies) == len(self.productDependencies) - \
            1, u"got: '%s', expected: '%s'" % (
                productDependencies, len(self.productDependencies) - 1)

        self.backend.productDependency_createObjects(self.productDependencies)
        productDependencies = self.backend.productDependency_getObjects()
        assert len(productDependencies) == len(self.productDependencies), u"got: '%s', expected: '%s'" % (
            productDependencies, len(self.productDependencies))


class ProductsOnDepotMixin(ProductsMixin, HostsMixin):
    def setUpProductOnDepots(self):
        self.setUpProducts()
        self.setUpHosts()

        (self.productOnDepot1, self.productOnDepot2, self.productOnDepot3,
         self.productOnDepot4, self.productOnDepot5, self.productOnDepot6,
         self.productOnDepot7, self.productOnDepot8, self.productOnDepot9,
         self.productOnDepot10, self.productOnDepot11) = getProductsOnDepot(self.products, self.configserver1, self.depotservers)

        self.productOnDepots = [
            self.productOnDepot1, self.productOnDepot2, self.productOnDepot3,
            self.productOnDepot4, self.productOnDepot5, self.productOnDepot6,
            self.productOnDepot7, self.productOnDepot8, self.productOnDepot9,
            self.productOnDepot10, self.productOnDepot11
        ]


class ProductsOnDepotTestsMixin(ProductsOnDepotMixin):
    def testProductOnDepotMethods(self):
        self.setUpProductOnDepots()

        self.createHostsOnBackend()
        self.createProductsOnBackend()

        self.backend.productOnDepot_createObjects(self.productOnDepots)
        productOnDepots = self.backend.productOnDepot_getObjects(
            attributes=['productId'])
        self.assertEqual(len(productOnDepots), len(self.productOnDepots))

        self.backend.productOnDepot_deleteObjects(self.productOnDepot1)
        productOnDepots = self.backend.productOnDepot_getObjects()
        self.assertEqual(len(productOnDepots), len(self.productOnDepots) - 1)

        # Non-existing product, must fail.
        self.assertRaises(Exception, self.backend.productOnDepot_createObjects, self.productOnDepots)

        self.backend.product_createObjects(self.products)
        self.backend.productOnDepot_createObjects(self.productOnDepots)
        productOnDepots = self.backend.productOnDepot_getObjects()
        self.assertEqual(len(productOnDepots), len(self.productOnDepots))

    def test_getProductOnDepotsFromBackend(self):
        products = getProducts()
        configServer = getConfigServer()
        depots = getDepotServers()
        productsOnDepotOrig = getProductsOnDepot(products, configServer, depots)
        self.backend.host_createObjects(configServer)
        self.backend.host_createObjects(depots)
        self.backend.product_createObjects(products)
        self.backend.productOnDepot_createObjects(productsOnDepotOrig)

        productOnDepots = self.backend.productOnDepot_getObjects(attributes=['productId'])
        self.assertEqual(len(productOnDepots), len(productsOnDepotOrig))

    def test_deleteProductOnDepot(self):
        products = getProducts()
        configServer = getConfigServer()
        depots = getDepotServers()
        productsOnDepotOrig = getProductsOnDepot(products, configServer, depots)
        self.backend.host_createObjects(configServer)
        self.backend.host_createObjects(depots)
        self.backend.product_createObjects(products)
        self.backend.productOnDepot_createObjects(productsOnDepotOrig)

        productOnDepot1 = productsOnDepotOrig[0]
        self.backend.productOnDepot_deleteObjects(productOnDepot1)
        productOnDepots = self.backend.productOnDepot_getObjects()
        self.assertEqual(len(productOnDepots), len(productsOnDepotOrig) - 1)

    def test_createDuplicateProductsOnDepots(self):
        products = getProducts()
        configServer = getConfigServer()
        depots = getDepotServers()
        productsOnDepotOrig = getProductsOnDepot(products, configServer, depots)
        self.backend.host_createObjects(configServer)
        self.backend.host_createObjects(depots)
        self.backend.product_createObjects(products)

        self.backend.productOnDepot_createObjects(productsOnDepotOrig)
        self.backend.productOnDepot_createObjects(productsOnDepotOrig)

        productOnDepots = self.backend.productOnDepot_getObjects()
        self.assertEqual(len(productOnDepots), len(productsOnDepotOrig))


class ProductsOnClientsMixin(ClientsMixin, ProductsMixin):
    def setUpProductOnClients(self):
        self.setUpProducts()
        self.setUpClients()

        (self.productOnClient1, self.productOnClient2, self.productOnClient3,
         self.productOnClient4) = getProductsOnClients(self.products, self.clients)

        self.productOnClients = [
            self.productOnClient1, self.productOnClient2,
            self.productOnClient3, self.productOnClient4
        ]


class ProductsOnClientTestsMixin(ProductsOnClientsMixin, ProductPropertiesMixin):
    def testProductOnClientMethods(self):
        self.setUpProductOnClients()
        self.setUpProductProperties()
        self.setUpProductPropertyStates(),

        self.createHostsOnBackend()
        self.createProductsOnBackend()

        self.backend.productOnClient_createObjects(self.productOnClients)
        productOnClients = self.backend.productOnClient_getObjects()
        assert len(productOnClients) == len(self.productOnClients), u"got: '%s', expected: '%s'" % (
            productOnClients, len(self.productOnClients))

        client1ProductOnClients = []
        for productOnClient in self.productOnClients:
            if (productOnClient.getClientId() == self.client1.id):
                client1ProductOnClients.append(productOnClient)
        productOnClients = self.backend.productOnClient_getObjects(
            clientId=self.client1.getId())
        for productOnClient in productOnClients:
            assert productOnClient.getClientId() == self.client1.getId(), u"got: '%s', expected: '%s'" % (
                productOnClient.getClientId(), self.client1.getId())

        productOnClients = self.backend.productOnClient_getObjects(
            clientId=self.client1.getId(), productId=self.product2.getId())
        assert len(productOnClients) == 1, u"got: '%s', expected: '%s'" % (
            productOnClients, 1)
        assert productOnClients[0].getProductId() == self.product2.getId(), u"got: '%s', expected: '%s'" % (
            productOnClients[0].getProductId(), self.product2.getId())
        assert productOnClients[0].getClientId() == self.client1.getId(), u"got: '%s', expected: '%s'" % (
            productOnClients[0].getClientId(), self.client1.getId())

        self.productOnClient2.setTargetConfiguration('forbidden')
        self.backend.productOnClient_updateObject(self.productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(
            targetConfiguration='forbidden')
        assert len(productOnClients) == 1, u"got: '%s', expected: '%s'" % (
            productOnClients, 1)

        self.productOnClient2.setInstallationStatus('unknown')
        self.backend.productOnClient_updateObject(self.productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(
            installationStatus='unknown')
        assert len(productOnClients) == 1, u"got: '%s', expected: '%s'" % (
            productOnClients, 1)

        self.productOnClient2.setActionRequest('custom')
        self.backend.productOnClient_updateObject(self.productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(
            actionRequest='custom')
        assert len(productOnClients) == 1, u"got: '%s', expected: '%s'" % (
            productOnClients, 1)

        self.productOnClient2.setLastAction('once')
        self.backend.productOnClient_updateObject(self.productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(
            lastAction='once')
        assert len(productOnClients) == 1, u"got: '%s', expected: '%s'" % (
            productOnClients, 1)

        self.productOnClient2.setActionProgress('aUniqueProgress')
        self.backend.productOnClient_updateObject(self.productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(
            actionProgress='aUniqueProgress')
        assert len(productOnClients) == 1, u"got: '%s', expected: '%s'" % (
            productOnClients, 1)

        productOnClients = self.backend.productOnClient_getObjects(
            productType=self.productOnClient2.productType, clientId=self.productOnClient2.clientId)
        assert len(productOnClients) >= 1, u"got: '%s', expected: >=1" % len(
            productOnClients)
        for productOnClient in productOnClients:
            if (productOnClient.productId == self.productOnClient2.productId):
                assert productOnClient.actionProgress == self.productOnClient2.actionProgress, u"got: '%s', expected: '%s'" % (
                    productOnClient.actionProgress, self.productOnClient2.actionProgress)

        self.productOnClient2.setActionResult('failed')
        self.backend.productOnClient_updateObject(self.productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(
            actionResult='failed')
        assert len(productOnClients) == 1, u"got: '%s', expected: '%s'" % (
            productOnClients, 1)

        self.productOnClient2.setInstallationStatus('installed')
        self.productOnClient2.setProductVersion('777777')
        self.productOnClient2.setPackageVersion('1')
        self.backend.productOnClient_updateObject(self.productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(
            productVersion='777777')
        assert len(productOnClients) == 1, u"got: '%s', expected: '%s'" % (
            productOnClients, 1)

        self.productOnClient2.setPackageVersion('999999')
        self.backend.productOnClient_updateObject(self.productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(
            packageVersion='999999')
        assert len(productOnClients) == 1, u"got: '%s', expected: '%s'" % (
            productOnClients, 1)

        self.productOnClient2.setModificationTime('2010-01-01 05:55:55')
        self.backend.productOnClient_updateObject(self.productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(
            modificationTime='2010-01-01 05:55:55')
        # You cant set modification time on update!
        assert len(productOnClients) == 0, u"got: '%s', expected: '%s'" % (
            productOnClients, 0)

        self.backend.productOnClient_createObjects(self.productOnClients)
        self.backend.productOnClient_deleteObjects(self.productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects()
        assert len(productOnClients) == len(self.productOnClients) - \
            1, u"got: '%s', expected: '%s'" % (
                productOnClients, len(self.productOnClients) - 1)

        self.backend.productOnClient_createObjects(self.productOnClients)

    def testProductOnClientDependencies(self):
        self.setUpProductOnClients()

        self.createHostsOnBackend()
        self.createProductsOnBackend()
        # TODO

        # depotserver1: client1, client2, client3, client4
        # depotserver2: client5, client6, client7

        # depotserver1: product6_1.0-1, product7_1.0-1, product9_1.0-1
        # depotserver2: product6_1.0-1, product7_1.0-2, product9_1.0-1

        # product6_1.0-1: setup requires product7_1.0-1
        # product7_1.0-1: setup requires product9

        self.backend.productOnClient_create(
            productId='product6',
            productType='LocalbootProduct',
            clientId='client1.test.invalid',
            installationStatus='not_installed',
            actionRequest='setup')

        self.backend.productOnClient_delete(
            productId='product7',
            clientId='client1.test.invalid')

        self.backend.productOnClient_delete(
            productId='product9',
            clientId='client1.test.invalid')

        productOnClients = self.backend.productOnClient_getObjects(
            clientId='client1.test.invalid')
        setup = []
        for productOnClient in productOnClients:
            print(u"Got productOnClient: %s" % productOnClient)
            if (productOnClient.actionRequest == 'setup'):
                setup.append(productOnClient.productId)
        assert 'product6' in setup, u"'%s' not in '%s'" % ('product6', setup)
        #assert 'product7' in setup, u"'%s' not in '%s'" % ('product7', setup)
        #assert 'product9' in setup, u"'%s' not in '%s'" % ('product9', setup)

        productOnClients = self.backend.productOnClient_getObjects(
            clientId='client1.test.invalid', productId=['product6', 'product7'])
        for productOnClient in productOnClients:
            print(u"Got productOnClient: %s" % productOnClient)
            assert productOnClient.productId in ('product6', 'product7'), u"'%s' not in '%s'" % (
                productOnClient.productId, ('product6', 'product7'))

        productOnClients = self.backend.productOnClient_getObjects(
            clientId='client1.test.invalid', productId=['*6*'])
        for productOnClient in productOnClients:
            print(u"Got productOnClient: %s" % productOnClient)
            assert productOnClient.productId in ('product6'), u"'%s' not in '%s'" % (
                productOnClient.productId, ('product6'))

        self.backend.productOnClient_create(
            productId='product6',
            productType='LocalbootProduct',
            clientId='client5.test.invalid',
            installationStatus='not_installed',
            actionRequest='setup')

        self.backend.productOnClient_delete(
            productId='product7',
            clientId='client5.test.invalid')

        self.backend.productOnClient_delete(
            productId='product9',
            clientId='client5.test.invalid')

        productOnClients = self.backend.productOnClient_getObjects(
            clientId='client5.test.invalid')
        setup = []
        for productOnClient in productOnClients:
            print(u"Got productOnClient: %s" % productOnClient)
            if (productOnClient.actionRequest == 'setup'):
                setup.append(productOnClient.productId)
        assert 'product7' not in setup, u"'%s' is in '%s'" % (
            'product7', setup)
        assert 'product9' not in setup, u"'%s' is in '%s'" % (
            'product9', setup)

    def testLongProductName(self):
        """
        Can the backend handle product names of 128 characters length?
        """
        product = LocalbootProduct(
            id='new_prod',
            name='New Product for Tests',
            productVersion=1,
            packageVersion=1
        )

        newName = (
            u'This is a very long name with 128 characters to test the '
            u'creation of long product names that should work now but '
            u'were limited b4'
        )

        product.setName(newName)

        self.backend.product_createObjects(product)
        backendProduct = self.backend.product_getObjects(id=product.id)

        self.assertEquals(1, len(backendProduct))
        backendProduct = backendProduct[0]

        self.assertEquals(newName, backendProduct.name)

    def test_getProductsOnClientsFromBackend(self):
        clients = getClients()
        products = getLocalbootProducts()
        pocs = getProductsOnClients(products, clients)

        self.backend.host_createObjects(clients)
        self.backend.product_createObjects(products)
        self.backend.productOnClient_createObjects(pocs)

        productOnClients = self.backend.productOnClient_getObjects()
        for poc in pocs:
            self.assertIn(poc, productOnClients)

    def test_selectProductOnClient(self):
        products = getProducts()
        clients = getClients()
        pocs = getProductsOnClients(products, clients)

        self.backend.host_createObjects(clients)
        self.backend.product_createObjects(products)
        self.backend.productOnClient_createObjects(pocs)

        client1 = clients[0]
        client1ProductOnClients = [productOnClient for productOnClient in pocs
                                   if productOnClient.getClientId() == client1.id]

        productOnClients = self.backend.productOnClient_getObjects(clientId=client1.getId())
        for productOnClient in productOnClients:
            self.assertEqual(productOnClient.getClientId(), client1.getId())

    def test_selectProductOnClientById(self):
        products = getProducts()
        clients = getClients()
        pocs = getProductsOnClients(products, clients)

        self.backend.host_createObjects(clients)
        self.backend.product_createObjects(products)
        self.backend.productOnClient_createObjects(pocs)

        client1 = clients[0]
        product2 = products[1]

        productOnClients = self.backend.productOnClient_getObjects(clientId=client1.getId(), productId=product2.getId())
        self.assertEqual(1, len(productOnClients))
        poc = productOnClients[0]
        self.assertEqual(poc.getProductId(), product2.getId())
        self.assertEqual(poc.getClientId(), client1.getId())

    def test_updateProductsOnClients(self):
        products = getProducts()
        clients = getClients()
        pocs = getProductsOnClients(products, clients)

        self.backend.host_createObjects(clients)
        self.backend.product_createObjects(products)
        self.backend.productOnClient_createObjects(pocs)

        productOnClient2 = pocs[1]
        productOnClient2.setTargetConfiguration('forbidden')
        self.backend.productOnClient_updateObject(productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(targetConfiguration='forbidden')
        self.assertIn(productOnClient2, productOnClients)

        productOnClient2.setInstallationStatus('unknown')
        self.backend.productOnClient_updateObject(productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects(installationStatus='unknown')
        self.assertEqual(len(productOnClients), 1)

    def test_deleteProductOnClient(self):
        products = getProducts()
        clients = getClients()
        pocs = getProductsOnClients(products, clients)

        self.backend.host_createObjects(clients)
        self.backend.product_createObjects(products)
        self.backend.productOnClient_createObjects(pocs)

        productOnClient2 = pocs[1]
        self.backend.productOnClient_deleteObjects(productOnClient2)
        productOnClients = self.backend.productOnClient_getObjects()

        self.assertEquals(len(pocs) - 1, len(productOnClients))
        self.assertNotIn(productOnClient2, productOnClients)
