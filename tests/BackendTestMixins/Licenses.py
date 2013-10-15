#!/usr/bin/env python
#-*- coding: utf-8 -*-

from OPSI.Object import (LicenseContract, RetailSoftwareLicense,
    OEMSoftwareLicense, VolumeSoftwareLicense, ConcurrentSoftwareLicense,
    LicensePool, SoftwareLicenseToLicensePool, LicenseOnClient)


class LicensesMixin(object):
    def setUpLicenseContracts(self):
        self.licenseContract1 = LicenseContract(
            id=u'license contract 1',
            description=u'a license contract',
            notes=None,
            partner=u'',
            conclusionDate=None,
            notificationDate=None,
            expirationDate=None
        )

        self.licenseContract2 = LicenseContract(
            id=u'license contract 2',
            description=u'license contract with company x',
            notes=u'Contract notes',
            partner=u'company x',
            conclusionDate='2009-01-01 00:00:00',
            notificationDate='2010-12-01 00:00:00',
            expirationDate='2011-01-01 00:00:00',
        )
        self.licenseContracts = [self.licenseContract1, self.licenseContract2]

    def setUpSoftwareLicenses(self):
        self.softwareLicense1 = RetailSoftwareLicense(
            id=u'software license 1',
            licenseContractId=self.licenseContract1.getId(),
            maxInstallations=2,
            boundToHost=None,
            expirationDate=self.licenseContract1.getExpirationDate()
        )

        self.softwareLicense2 = OEMSoftwareLicense(
            id=u'software license 2',
            licenseContractId=self.licenseContract1.getId(),
            maxInstallations=None,
            boundToHost=self.client1.getId(),
            expirationDate=self.licenseContract1.getExpirationDate()
        )

        self.softwareLicense3 = VolumeSoftwareLicense(
            id=u'software license 3',
            licenseContractId=self.licenseContract2.getId(),
            maxInstallations=100,
            boundToHost=None,
            expirationDate=self.licenseContract2.getExpirationDate()
        )

        self.softwareLicense4 = ConcurrentSoftwareLicense(
            id=u'software license 4',
            licenseContractId=self.licenseContract2.getId(),
            maxInstallations=10,
            boundToHost=None,
            expirationDate=self.licenseContract2.getExpirationDate()
        )
        self.softwareLicenses = [
            self.softwareLicense1, self.softwareLicense2,
            self.softwareLicense3, self.softwareLicense4
        ]

    def setUpLicensePool(self):
        self.licensePool1 = LicensePool(
            id=u'license_pool_1',
            description=u'licenses for product1',
            productIds=self.product1.getId()
        )

        self.licensePool2 = LicensePool(
            id=u'license_pool_2',
            description=u'licenses for product2',
            productIds=self.product2.getId()
        )
        self.licensePools = [self.licensePool1, self.licensePool2]

    def setUpSoftwareLicenseToLicensePools(self):
        self.softwareLicenseToLicensePool1 = SoftwareLicenseToLicensePool(
            softwareLicenseId=self.softwareLicense1.getId(),
            licensePoolId=self.licensePool1.getId(),
            licenseKey='xxxxx-yyyyy-zzzzz-aaaaa-bbbbb'
        )

        self.softwareLicenseToLicensePool2 = SoftwareLicenseToLicensePool(
            softwareLicenseId=self.softwareLicense2.getId(),
            licensePoolId=self.licensePool1.getId(),
            licenseKey=''
        )

        self.softwareLicenseToLicensePool3 = SoftwareLicenseToLicensePool(
            softwareLicenseId=self.softwareLicense3.getId(),
            licensePoolId=self.licensePool2.getId(),
            licenseKey='12345-56789-00000-11111-aaaaa'
        )

        self.softwareLicenseToLicensePool4 = SoftwareLicenseToLicensePool(
            softwareLicenseId=self.softwareLicense4.getId(),
            licensePoolId=self.licensePool2.getId(),
            licenseKey=None
        )
        self.softwareLicenseToLicensePools = [
            self.softwareLicenseToLicensePool1,
            self.softwareLicenseToLicensePool2,
            self.softwareLicenseToLicensePool3,
            self.softwareLicenseToLicensePool4
        ]

    def setUpLicenseOnClients(self):
        self.licenseOnClient1 = LicenseOnClient(
            softwareLicenseId=self.softwareLicenseToLicensePool1.getSoftwareLicenseId(),
            licensePoolId=self.softwareLicenseToLicensePool1.getLicensePoolId(),
            clientId=self.client1.getId(),
            licenseKey=self.softwareLicenseToLicensePool1.getLicenseKey(),
            notes=None
        )

        self.licenseOnClient2 = LicenseOnClient(
            softwareLicenseId=self.softwareLicenseToLicensePool1.getSoftwareLicenseId(),
            licensePoolId=self.softwareLicenseToLicensePool1.getLicensePoolId(),
            clientId=self.client2.getId(),
            licenseKey=self.softwareLicenseToLicensePool1.getLicenseKey(),
            notes=u'Installed manually'
        )
        self.licenseOnClients = [self.licenseOnClient1, self.licenseOnClient2]


class LicensesTestMixin(LicensesMixin):
    def testLicenseManagementObjectMethods(self):
        self.configureBackendOptions()

        # LicenseContracts
        print(u"Testing licenseContract methods")
        self.setUpLicenseContracts()

        self.backend.licenseContract_createObjects(self.licenseContracts)

        licenseContracts = self.backend.licenseContract_getObjects()
        self.assertEqual(len(licenseContracts), len(self.licenseContracts))

        # SoftwareLicenses
        print(u"Testing softwareLicense methods")
        self.setUpSoftwareLicenses()
        self.backend.softwareLicense_createObjects(self.softwareLicenses)

        softwareLicenses = self.backend.softwareLicense_getObjects()
        assert len(softwareLicenses) == len(self.softwareLicenses), u"got: '%s', expected: '%s'" % (
            softwareLicenses, self.softwareLicenses)

        # LicensePools
        print(u"Testing licensePool methods")

        self.backend.licensePool_createObjects(self.licensePools)

        licensePools = self.backend.licensePool_getObjects()
        assert len(licensePools) == len(self.licensePools), u"got: '%s', expected: '%s'" % (
            licensePools, self.licensePools)
        for licensePool in licensePools:
            if (licensePool.getId() == self.licensePool1.getId()):
                for productId in licensePool.getProductIds():
                    assert productId in self.licensePool1.getProductIds(), u"'%s' not in '%s'" % (
                        productId, self.licensePool1.getProductIds())

        licensePools = self.backend.licensePool_getObjects(
            productIds=self.licensePool1.productIds)
        assert len(licensePools) == 1, u"got: '%s', expected: '%s'" % (
            licensePools, 1)
        assert licensePools[0].getId() == self.licensePool1.getId(), u"got: '%s', expected: '%s'" % (
            licensePools[0].getId(), self.licensePool1.getId())

        licensePools = self.backend.licensePool_getObjects(
            id=self.licensePool2.id, productIds=self.licensePool1.productIds)
        assert len(licensePools) == 0, u"got: '%s', expected: '%s'" % (
            licensePools, 0)

        licensePools = self.backend.licensePool_getObjects(productIds=None)
        assert len(licensePools) == len(self.licensePools), u"got: '%s', expected: '%s'" % (
            licensePools, len(self.licensePools))

        licensePools = self.backend.licensePool_getObjects(
            productIds=['xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'])
        assert len(licensePools) == 0, u"got: '%s', expected: '%s'" % (
            licensePools, 0)

        # SoftwareLicenseToLicensePools
        print(u"Testing softwareLicenseToLicensePool methods")

        self.backend.softwareLicenseToLicensePool_createObjects(
            self.softwareLicenseToLicensePools)

        softwareLicenseToLicensePools = self.backend.softwareLicenseToLicensePool_getObjects(
        )
        assert len(softwareLicenseToLicensePools) == len(self.softwareLicenseToLicensePools), u"got: '%s', expected: '%s'" % (
            softwareLicenseToLicensePools, len(self.softwareLicenseToLicensePools))

        # LicenseOnClients
        print(u"Testing licenseOnClient methods")

        self.backend.licenseOnClient_createObjects(self.licenseOnClients)

        licenseOnClients = self.backend.licenseOnClient_getObjects()
        assert len(licenseOnClients) == len(self.licenseOnClients), u"got: '%s', expected: '%s'" % (
            licenseOnClients, len(self.licenseOnClients))
