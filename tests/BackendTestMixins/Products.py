#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import absolute_import

from OPSI.Object import (NetbootProduct, LocalbootProduct,
    UnicodeProductProperty, BoolProductProperty, ProductDependency,
    ProductOnDepot, ProductOnClient, ProductPropertyState)

from .Hosts import HostsMixin
from .Clients import ClientsMixin


class ProductsMixin(object):
    def setUpProducts(self):
        self.product1 = NetbootProduct(
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

        self.netbootProducts = [self.product1]

        if not hasattr(self, 'products'):
            self.products = []

        self.products.extend(self.netbootProducts)

        self.product2 = LocalbootProduct(
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

        self.product3 = LocalbootProduct(
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

        self.product4 = LocalbootProduct(
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

        self.product5 = LocalbootProduct(
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

        self.product6 = LocalbootProduct(
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

        self.product7 = LocalbootProduct(
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

        self.product8 = LocalbootProduct(
            id='product7',
            name=u'Product 7',
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

        self.product9 = LocalbootProduct(
            id='product9',
            name=u'Product 9',
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

        self.localbootProducts = [self.product2, self.product3, self.product4,
                                  self.product5, self.product6, self.product7, self.product8, self.product9]
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

        # TODO: turn this into tests?
        self.productProperty1 = UnicodeProductProperty(
            productId=self.product1.id,
            productVersion=self.product1.productVersion,
            packageVersion=self.product1.packageVersion,
            propertyId="productProperty1",
            description='Test product property (unicode)',
            possibleValues=['unicode1', 'unicode2', 'unicode3'],
            defaultValues=['unicode1', 'unicode3'],
            editable=True,
            multiValue=True
        )

        # TODO: turn this into tests?
        self.productProperty2 = BoolProductProperty(
            productId=self.product1.id,
            productVersion=self.product1.productVersion,
            packageVersion=self.product1.packageVersion,
            propertyId="productProperty2",
            description='Test product property 2 (bool)',
            defaultValues=True
        )

        self.productProperty3 = BoolProductProperty(
            productId=self.product3.id,
            productVersion=self.product3.productVersion,
            packageVersion=self.product3.packageVersion,
            propertyId=u"productProperty3",
            description=u'Test product property 3 (bool)',
            defaultValues=False
        )

        self.productProperty4 = UnicodeProductProperty(
            productId=self.product1.id,
            productVersion=self.product1.productVersion,
            packageVersion=self.product1.packageVersion,
            propertyId=u"i386_dir",
            description=u'i386 dir to use as installation source',
            possibleValues=["i386"],
            defaultValues=["i386"],
            editable=True,
            multiValue=False
        )

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

        # TODO: test?
        self.productPropertyState1 = ProductPropertyState(
            productId=self.productProperty1.getProductId(),
            propertyId=self.productProperty1.getPropertyId(),
            objectId=self.depotserver1.getId(),
            values='unicode-depot-default'
        )

        # TODO: test?
        self.productPropertyState2 = ProductPropertyState(
            productId=self.productProperty2.getProductId(),
            propertyId=self.productProperty2.getPropertyId(),
            objectId=self.depotserver1.getId(),
            values=[True]
        )

        # TODO: test?
        self.productPropertyState3 = ProductPropertyState(
            productId=self.productProperty2.getProductId(),
            propertyId=self.productProperty2.getPropertyId(),
            objectId=self.depotserver2.getId(),
            values=False
        )

        # TODO: test?
        self.productPropertyState4 = ProductPropertyState(
            productId=self.productProperty1.getProductId(),
            propertyId=self.productProperty1.getPropertyId(),
            objectId=self.client1.getId(),
            values='unicode1'
        )

        # TODO: test?
        self.productPropertyState5 = ProductPropertyState(
            productId=self.productProperty2.getProductId(),
            propertyId=self.productProperty2.getPropertyId(),
            objectId=self.client1.getId(),
            values=[False]
        )

        # TODO: test?
        self.productPropertyState6 = ProductPropertyState(
            productId=self.productProperty2.getProductId(),
            propertyId=self.productProperty2.getPropertyId(),
            objectId=self.client2.getId(),
            values=True
        )

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

        self.backend.productPropertyState_createObjects(
            self.productPropertyStates)

        productPropertyStates = self.backend.productPropertyState_getObjects()
        assert len(productPropertyStates) == len(self.productPropertyStates), u"got: '%s', expected: '%s'" % (
            productPropertyStates, len(self.productPropertyStates))

        self.backend.productPropertyState_deleteObjects(
            self.productPropertyState2)
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
                        if not value is None:
                            if type(value) is list:
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

        excepted = False
        try:
            pps0 = ProductPropertyState(
                productId=self.productProperty1.getProductId(),
                propertyId=self.productProperty1.getPropertyId(),
                objectId='kaputtesdepot.dom.local'
            )
            self.backend.productPropertyState_insertObject(pps0)
        except:
            excepted = True

        assert excepted, u"faulty objectId accepted!"

class ProductDependenciesMixin(ProductsMixin):
    def setUpProductDependencies(self):
        self.setUpProducts()

        self.productDependency1 = ProductDependency(
            productId=self.product2.id,
            productVersion=self.product2.productVersion,
            packageVersion=self.product2.packageVersion,
            productAction='setup',
            requiredProductId=self.product3.id,
            requiredProductVersion=self.product3.productVersion,
            requiredPackageVersion=self.product3.packageVersion,
            requiredAction='setup',
            requiredInstallationStatus=None,
            requirementType='before'
        )

        self.productDependency2 = ProductDependency(
            productId=self.product2.id,
            productVersion=self.product2.productVersion,
            packageVersion=self.product2.packageVersion,
            productAction='setup',
            requiredProductId=self.product4.id,
            requiredProductVersion=None,
            requiredPackageVersion=None,
            requiredAction=None,
            requiredInstallationStatus='installed',
            requirementType='after'
        )

        self.productDependency3 = ProductDependency(
            productId=self.product6.id,
            productVersion=self.product6.productVersion,
            packageVersion=self.product6.packageVersion,
            productAction='setup',
            requiredProductId=self.product7.id,
            requiredProductVersion=self.product7.productVersion,
            requiredPackageVersion=self.product7.packageVersion,
            requiredAction=None,
            requiredInstallationStatus='installed',
            requirementType='after'
        )

        self.productDependency4 = ProductDependency(
            productId=self.product7.id,
            productVersion=self.product7.productVersion,
            packageVersion=self.product7.packageVersion,
            productAction='setup',
            requiredProductId=self.product9.id,
            requiredProductVersion=None,
            requiredPackageVersion=None,
            requiredAction=None,
            requiredInstallationStatus='installed',
            requirementType='after'
        )

        self.productDependencies = [
            self.productDependency1, self.productDependency2,
            self.productDependency3, self.productDependency4
        ]

    def createProductDepedenciesOnBackend(self):
        self.backend.productDependency_createObjects(self.productDependencies)


class ProductDependenciesTestMixin(ProductDependenciesMixin):
    def testProductDependencies(self):
        self.configureBackendOptions()

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

        self.productOnDepot1 = ProductOnDepot(
            productId=self.product1.getId(),
            productType=self.product1.getType(),
            productVersion=self.product1.getProductVersion(),
            packageVersion=self.product1.getPackageVersion(),
            depotId=self.depotserver1.getId(),
            locked=False
        )

        self.productOnDepot2 = ProductOnDepot(
            productId=self.product2.getId(),
            productType=self.product2.getType(),
            productVersion=self.product2.getProductVersion(),
            packageVersion=self.product2.getPackageVersion(),
            depotId=self.depotserver1.getId(),
            locked=False
        )

        self.productOnDepot3 = ProductOnDepot(
            productId=self.product3.getId(),
            productType=self.product3.getType(),
            productVersion=self.product3.getProductVersion(),
            packageVersion=self.product3.getPackageVersion(),
            depotId=self.depotserver1.getId(),
            locked=False
        )

        self.productOnDepot4 = ProductOnDepot(
            productId=self.product3.getId(),
            productType=self.product3.getType(),
            productVersion=self.product3.getProductVersion(),
            packageVersion=self.product3.getPackageVersion(),
            depotId=self.configserver1.getId(),
            locked=False
        )

        self.productOnDepot5 = ProductOnDepot(
            productId=self.product5.getId(),
            productType=self.product5.getType(),
            productVersion=self.product5.getProductVersion(),
            packageVersion=self.product5.getPackageVersion(),
            depotId=self.configserver1.getId(),
            locked=False
        )

        self.productOnDepot6 = ProductOnDepot(
            productId=self.product6.getId(),
            productType=self.product6.getType(),
            productVersion=self.product6.getProductVersion(),
            packageVersion=self.product6.getPackageVersion(),
            depotId=self.depotserver1.getId(),
            locked=False
        )

        self.productOnDepot7 = ProductOnDepot(
            productId=self.product6.getId(),
            productType=self.product6.getType(),
            productVersion=self.product6.getProductVersion(),
            packageVersion=self.product6.getPackageVersion(),
            depotId=self.depotserver2.getId(),
            locked=False
        )

        self.productOnDepot8 = ProductOnDepot(
            productId=self.product7.getId(),
            productType=self.product7.getType(),
            productVersion=self.product7.getProductVersion(),
            packageVersion=self.product7.getPackageVersion(),
            depotId=self.depotserver1.getId(),
            locked=False
        )

        self.productOnDepot9 = ProductOnDepot(
            productId=self.product8.getId(),
            productType=self.product8.getType(),
            productVersion=self.product8.getProductVersion(),
            packageVersion=self.product8.getPackageVersion(),
            depotId=self.depotserver2.getId(),
            locked=False
        )

        self.productOnDepot10 = ProductOnDepot(
            productId=self.product9.getId(),
            productType=self.product9.getType(),
            productVersion=self.product9.getProductVersion(),
            packageVersion=self.product9.getPackageVersion(),
            depotId=self.depotserver1.getId(),
            locked=False
        )

        self.productOnDepot11 = ProductOnDepot(
            productId=self.product9.getId(),
            productType=self.product9.getType(),
            productVersion=self.product9.getProductVersion(),
            packageVersion=self.product9.getPackageVersion(),
            depotId=self.depotserver2.getId(),
            locked=False
        )

        self.productOnDepots = [
            self.productOnDepot1, self.productOnDepot2, self.productOnDepot3,
            self.productOnDepot4, self.productOnDepot5, self.productOnDepot6,
            self.productOnDepot7, self.productOnDepot8, self.productOnDepot9,
            self.productOnDepot10, self.productOnDepot11
        ]


class ProductsOnDepotTestsMixin(ProductsOnDepotMixin):
    def configureBackendOptions(self):
        self.backend.backend_setOptions({
            'processProductPriorities': False,
            'processProductDependencies': False,
            'addProductOnClientDefaults': False,
            'addProductPropertyStateDefaults': False,
            'addConfigStateDefaults': False,
            'deleteConfigStateIfDefault': False,
            'returnObjectsOnUpdateAndCreate': False
        })

    def testProductOnDepotMethods(self):
        self.configureBackendOptions()

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


class ProductsOnClientsMixin(ClientsMixin, ProductsMixin):
    def setUpProductOnClients(self):
        self.setUpProducts()
        self.setUpClients()

        self.productOnClient1 = ProductOnClient(
            productId=self.product1.getId(),
            productType=self.product1.getType(),
            clientId=self.client1.getId(),
            installationStatus='installed',
            actionRequest='setup',
            actionProgress='',
            productVersion=self.product1.getProductVersion(),
            packageVersion=self.product1.getPackageVersion(),
            modificationTime='2009-07-01 12:00:00'
        )

        self.productOnClient2 = ProductOnClient(
            productId=self.product2.getId(),
            productType=self.product2.getType(),
            clientId=self.client1.getId(),
            installationStatus='installed',
            actionRequest='uninstall',
            actionProgress='',
            productVersion=self.product2.getProductVersion(),
            packageVersion=self.product2.getPackageVersion()
        )

        self.productOnClient3 = ProductOnClient(
            productId=self.product2.getId(),
            productType=self.product2.getType(),
            clientId=self.client3.getId(),
            installationStatus='installed',
            actionRequest='setup',
            actionProgress='running',
            productVersion=self.product2.getProductVersion(),
            packageVersion=self.product2.getPackageVersion()
        )

        self.productOnClient4 = ProductOnClient(
            productId=self.product1.getId(),
            productType=self.product1.getType(),
            clientId=self.client3.getId(),
            targetConfiguration='installed',
            installationStatus='installed',
            actionRequest='none',
            lastAction='setup',
            actionProgress='',
            actionResult='successful',
            productVersion=self.product1.getProductVersion(),
            packageVersion=self.product1.getPackageVersion()
        )

        self.productOnClients = [
            self.productOnClient1, self.productOnClient2,
            self.productOnClient3, self.productOnClient4
        ]



class ProductsOnClientTestsMixin(ProductsOnClientsMixin, ProductPropertiesMixin):
    def testProductOnClientMethods(self):
        self.configureBackendOptions()

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
            clientId='client1.uib.local',
            installationStatus='not_installed',
            actionRequest='setup')

        self.backend.productOnClient_delete(
            productId='product7',
            clientId='client1.uib.local')

        self.backend.productOnClient_delete(
            productId='product9',
            clientId='client1.uib.local')

        productOnClients = self.backend.productOnClient_getObjects(
            clientId='client1.uib.local')
        setup = []
        for productOnClient in productOnClients:
            print(u"Got productOnClient: %s" % productOnClient)
            if (productOnClient.actionRequest == 'setup'):
                setup.append(productOnClient.productId)
        assert 'product6' in setup, u"'%s' not in '%s'" % ('product6', setup)
        #assert 'product7' in setup, u"'%s' not in '%s'" % ('product7', setup)
        #assert 'product9' in setup, u"'%s' not in '%s'" % ('product9', setup)

        productOnClients = self.backend.productOnClient_getObjects(
            clientId='client1.uib.local', productId=['product6', 'product7'])
        for productOnClient in productOnClients:
            print(u"Got productOnClient: %s" % productOnClient)
            assert productOnClient.productId in ('product6', 'product7'), u"'%s' not in '%s'" % (
                productOnClient.productId, ('product6', 'product7'))
#           , u"Product id filter failed, got product id: %s" % productOnClient.productId

        productOnClients = self.backend.productOnClient_getObjects(
            clientId='client1.uib.local', productId=['*6*'])
        for productOnClient in productOnClients:
            print(u"Got productOnClient: %s" % productOnClient)
            assert productOnClient.productId in ('product6'), u"'%s' not in '%s'" % (
                productOnClient.productId, ('product6'))
#           , u"Product id filter failed, got product id: %s" % productOnClient.productId

        self.backend.productOnClient_create(
            productId='product6',
            productType='LocalbootProduct',
            clientId='client5.uib.local',
            installationStatus='not_installed',
            actionRequest='setup')

        self.backend.productOnClient_delete(
            productId='product7',
            clientId='client5.uib.local')

        self.backend.productOnClient_delete(
            productId='product9',
            clientId='client5.uib.local')

        productOnClients = self.backend.productOnClient_getObjects(
            clientId='client5.uib.local')
        setup = []
        for productOnClient in productOnClients:
            print(u"Got productOnClient: %s" % productOnClient)
            if (productOnClient.actionRequest == 'setup'):
                setup.append(productOnClient.productId)
        #assert not 'product6' in setup, u"'%s' is in '%s'" % ('product6', setup)
        assert not 'product7' in setup, u"'%s' is in '%s'" % (
            'product7', setup)
        assert not 'product9' in setup, u"'%s' is in '%s'" % (
            'product9', setup)