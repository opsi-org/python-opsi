#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2017 uib GmbH <info@uib.de>

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
Tests for the dynamically loaded legacy extensions.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/20_legacy.conf``.

The legacy extensions are to maintain backwards compatibility for scripts
that were written for opsi 3.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import pytest

from OPSI.Object import (
    BoolProductProperty, LocalbootProduct, OpsiClient, ProductDependency,
    ProductOnDepot, ProductPropertyState, UnicodeProductProperty)
from OPSI.Types import BackendReferentialIntegrityError
from .test_hosts import getDepotServers


def testGetGeneralConfigValueFailsWithInvalidObjectId(backendManager):
    with pytest.raises(ValueError):
        backendManager.getGeneralConfig_hash('foo')


def testGetGeneralConfig(backendManager):
    """
    Calling the function with some valid FQDN must not fail.
    """
    values = backendManager.getGeneralConfig_hash('some.client.fqdn')
    print(values)


def testSetGeneralConfigValue(backendManager):
    backendManager.host_createOpsiClient('some.client.fqdn')  # required by File-backend
    backendManager.setGeneralConfigValue('foo', 'bar', 'some.client.fqdn')

    assert 'bar' == backendManager.getGeneralConfigValue('foo', 'some.client.fqdn')


def testGetDomainShouldWork(backendManager):
    assert backendManager.getDomain()


@pytest.mark.parametrize("value", [None, ""])
def testGetGeneralConfigValueWithoutConfigReturnsNoValue(backendManager, value):
    assert backendManager.getGeneralConfigValue(value) is None


def testGetGeneralConfigIsEmptyAfterStart(backendManager):
    assert {} == backendManager.getGeneralConfig_hash()


@pytest.mark.parametrize("value", [
    {"test": True},
    {"test": 1},
    {"test": None}
])
def testSetGeneralConfigIsUnabledToHandleNonTextValues(backendManager, value):
    with pytest.raises(Exception):
        backendManager.setGeneralConfig(value)


def testSetGeneralConfigValueAndReadValues(backendManager):
    config = {"test.truth": "True", "test.int": "2"}
    backendManager.setGeneralConfig(config)

    for key, value in config.items():
        assert value == backendManager.getGeneralConfigValue(key)

    assert {} != backendManager.getGeneralConfig_hash()
    assert 2 == len(backendManager.getGeneralConfig_hash())


@pytest.mark.parametrize("value, expected", [
    ('yes', "True"),
    ('on', "True"),
    ('1', "True"),
    ('true', "True"),
    ('no', "False"),
    ('off', "False"),
    ('0', "False"),
    ('false', "False"),
    ("noconversion", "noconversion")
])
def testSetGeneralConfigValueTypeConversion(backendManager, value, expected):
    backendManager.setGeneralConfig({"bool": value})
    assert expected == backendManager.getGeneralConfigValue("bool")


def testSetGeneralConfigIsAbleToRemovingMissingValue(backendManager):
    config = {"test.truth": "True", "test.int": "2"}
    backendManager.setGeneralConfig(config)
    assert 2 == len(backendManager.getGeneralConfig_hash())

    del config["test.int"]
    backendManager.setGeneralConfig(config)
    assert 1 == len(backendManager.getGeneralConfig_hash())


def generateLargeConfig(numberOfConfigs):
    numberOfConfigs = 50  # len(config) will be double

    config = {}
    for value in range(numberOfConfigs):
        config["bool.{0}".format(value)] = str(value % 2 == 0)
        config["normal.{0}".format(value)] = "norm-{0}".format(value)

    assert numberOfConfigs * 2 == len(config)

    return config


@pytest.mark.parametrize(
    "config",
    [generateLargeConfig(50), generateLargeConfig(250)],
    ids=['50', '250']
)
def testMassFilling(backendManager, config):
    backendManager.setGeneralConfig(config)

    assert config == backendManager.getGeneralConfig_hash()


def testDeleteProductDependency(backendManager):
    firstProduct = LocalbootProduct('prod', '1.0', '1.0')
    secondProduct = LocalbootProduct('dependency', '1.0', '1.0')
    backendManager.product_insertObject(firstProduct)
    backendManager.product_insertObject(secondProduct)

    prodDependency = ProductDependency(
        productId=firstProduct.id,
        productVersion=firstProduct.productVersion,
        packageVersion=firstProduct.packageVersion,
        productAction='setup',
        requiredProductId=secondProduct.id,
        requiredAction='setup',
        requirementType='after'
    )
    backendManager.productDependency_insertObject(prodDependency)

    depots = getDepotServers()
    depot = depots[0]
    backendManager.host_insertObject(depot)

    productOnDepot = ProductOnDepot(
        productId=firstProduct.getId(),
        productType=firstProduct.getType(),
        productVersion=firstProduct.getProductVersion(),
        packageVersion=firstProduct.getPackageVersion(),
        depotId=depot.id,
        locked=False
    )
    backendManager.productOnDepot_createObjects([productOnDepot])

    assert backendManager.productDependency_getObjects()

    backendManager.deleteProductDependency(firstProduct.id, "", secondProduct.id, requiredProductClassId="unusedParam", requirementType="unused")

    assert not backendManager.productDependency_getObjects()


def testSetProductPropertyWithoutSideEffects(backendManager):
    product = LocalbootProduct('aboabo', '1.0', '2')
    backendManager.product_insertObject(product)

    testprop = UnicodeProductProperty(
        productId=product.id,
        productVersion=product.productVersion,
        packageVersion=product.packageVersion,
        propertyId=u"changeMe",
        possibleValues=["True", "NO NO NO"],
        defaultValues=["NOT YOUR IMAGE"],
        editable=True,
        multiValue=False
    )
    untouchable = UnicodeProductProperty(
        productId=product.id,
        productVersion=product.productVersion,
        packageVersion=product.packageVersion,
        propertyId=u"ucanttouchthis",
        possibleValues=["Chocolate", "Starfish"],
        defaultValues=["Chocolate"],
        editable=True,
        multiValue=False
    )
    backendManager.productProperty_insertObject(testprop)
    backendManager.productProperty_insertObject(untouchable)

    backendManager.setProductProperty(product.id, testprop.propertyId, 'Starfish')

    results = backendManager.productProperty_getObjects()
    assert len(results) == 2

    for result in results:
        print("Checking {0!r}".format(result))
        assert isinstance(result, UnicodeProductProperty)

        if result.propertyId == untouchable.propertyId:
            assert result.getDefaultValues() == untouchable.getDefaultValues()
            assert result.getPossibleValues() == untouchable.getPossibleValues()
        elif result.propertyId == testprop.propertyId:
            assert result.getDefaultValues() == testprop.getDefaultValues()
            assert result.getPossibleValues() == testprop.getPossibleValues()
        else:
            raise ValueError("Unexpected property: {0!r}".format(result))

    # TODO: add depots and check again
    assert not backendManager.productPropertyState_getObjects()


@pytest.mark.parametrize("productExists", [True, False], ids=["product exists", "product missing"])
@pytest.mark.parametrize("propertyExists", [True, False], ids=["property exists", "property missing"])
@pytest.mark.parametrize("clientExists", [True, False], ids=["client exists", "client missing"])
def testSetProductPropertyHandlingMissingObjects(backendManager, productExists, propertyExists, clientExists):
    expectedProperties = 0

    if productExists:
        product = LocalbootProduct('existence', '1.0', '1')
        backendManager.product_insertObject(product)

        if propertyExists:
            testprop = UnicodeProductProperty(
                productId=product.id,
                productVersion=product.productVersion,
                packageVersion=product.packageVersion,
                propertyId=u"changer",
                possibleValues=["True", "False"],
                defaultValues=["False"],
                editable=True,
                multiValue=False
            )
            backendManager.productProperty_insertObject(testprop)

            expectedProperties += 1

    backendManager.setProductProperty('existence', 'nothere', False)
    assert len(backendManager.productProperty_getObjects()) == expectedProperties

    if clientExists:
        client = OpsiClient('testclient.domain.invalid')
        backendManager.host_insertObject(client)

    with pytest.raises(BackendReferentialIntegrityError):
        backendManager.setProductProperty('existence', 'nothere', False, 'testclient.domain.invalid')
    assert len(backendManager.productProperty_getObjects()) == expectedProperties


def testSetProductPropertyHandlingBoolProductProperties(backendManager):
    product = LocalbootProduct('testproduct', '1.0', '2')
    backendManager.product_insertObject(product)

    testprop = BoolProductProperty(
        productId=product.id,
        productVersion=product.productVersion,
        packageVersion=product.packageVersion,
        propertyId=u"changeMe",
        defaultValues=[False]
    )
    backendManager.productProperty_insertObject(testprop)

    client = OpsiClient('testclient.domain.invalid')
    backendManager.host_insertObject(client)

    backendManager.setProductProperty(product.id, testprop.propertyId, True, client.id)

    result = backendManager.productProperty_getObjects(propertyId=testprop.propertyId)
    assert len(result) == 1
    result = result[0]
    assert isinstance(result, BoolProductProperty)
    assert result.getPossibleValues() == [False, True]
    assert result.getDefaultValues() == [False]

    result = backendManager.productPropertyState_getObjects()
    assert len(result) == 1
    result = result[0]
    assert result.getObjectId() == client.id
    assert result.getValues() == [True]


def testSetProductPropertyNotConcatenatingStrings(backendManager):
    product = LocalbootProduct('testproduct', '1.0', '2')
    backendManager.product_insertObject(product)

    testprop = UnicodeProductProperty(
        productId=product.id,
        productVersion=product.productVersion,
        packageVersion=product.packageVersion,
        propertyId=u"rebootflag",
        possibleValues=["0", "1", "2", "3"],
        defaultValues=["0"],
        editable=False,
        multiValue=False
    )
    donotchange = UnicodeProductProperty(
        productId=product.id,
        productVersion=product.productVersion,
        packageVersion=product.packageVersion,
        propertyId=u"upgradeproducts",
        possibleValues=["firefox", "opsi-vhd-control", "winscp"],
        defaultValues=["firefox", "opsi-vhd-control", "winscp"],
        editable=True,
        multiValue=True
    )

    backendManager.productProperty_insertObject(testprop)
    backendManager.productProperty_insertObject(donotchange)

    client = OpsiClient('testclient.domain.invalid')
    backendManager.host_insertObject(client)

    sideeffectPropState = ProductPropertyState(
        productId=product.id,
        propertyId=donotchange.propertyId,
        objectId=client.id,
        values=donotchange.getDefaultValues()
    )
    backendManager.productPropertyState_insertObject(sideeffectPropState)

    backendManager.setProductProperty(product.id, testprop.propertyId, "1", client.id)

    result = backendManager.productProperty_getObjects(propertyId=donotchange.propertyId)
    assert len(result) == 1
    result = result[0]
    assert isinstance(result, UnicodeProductProperty)
    assert result.getPossibleValues() == ["firefox", "opsi-vhd-control", "winscp"]
    assert result.getDefaultValues() == ["firefox", "opsi-vhd-control", "winscp"]

    result = backendManager.productProperty_getObjects(propertyId=testprop.propertyId)
    assert len(result) == 1
    result = result[0]
    assert isinstance(result, UnicodeProductProperty)
    assert result.getPossibleValues() == ["0", "1", "2", "3"]
    assert result.getDefaultValues() == ["0"]

    results = backendManager.productPropertyState_getObjects()
    assert len(results) == 2

    for result in results:
        assert result.getObjectId() == client.id
        print("Checking {0!r}".format(result))

        if result.propertyId == donotchange.propertyId:
            assert result.getValues() == donotchange.getPossibleValues()
        elif result.propertyId == testprop.propertyId:
            assert result.getValues() == ["1"]
        else:
            raise ValueError("Unexpected property state: {0!r}".format(result))
