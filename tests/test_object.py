# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2018 uib GmbH <info@uib.de>

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
Testing OPSI.Objects

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import pytest

from OPSI.Object import (
    AuditHardwareOnHost, BoolProductProperty, Host, LocalbootProduct,
    OpsiConfigserver, OpsiDepotserver, Product, ProductDependency,
    ProductProperty, ProductPropertyState, UnicodeConfig,
    UnicodeProductProperty,
    getPossibleClassAttributes, mandatoryConstructorArgs)

from .helpers import cleanMandatoryConstructorArgsCache


def testGetPossibleClassAttributes():
    assert getPossibleClassAttributes(Host) == set(
        [
            'masterDepotId', 'depotLocalUrl', 'repositoryRemoteUrl',
            'description', 'created', 'inventoryNumber', 'notes',
            'oneTimePassword', 'isMasterDepot', 'id', 'lastSeen',
            'maxBandwidth', 'hardwareAddress', 'networkAddress',
            'repositoryLocalUrl', 'opsiHostKey', 'ipAddress',
            'depotWebdavUrl', 'depotRemoteUrl', 'type',
            'workbenchRemoteUrl', 'workbenchLocalUrl'
        ]
    )


@pytest.fixture
def configServerReference():
    return OpsiConfigserver(
        id='configserver1.test.invalid',
        opsiHostKey='71234545689056789012123678901234',
        depotLocalUrl='file:///opt/pcbin/install',
        depotRemoteUrl=u'smb://configserver1/opt_pcbin/install',
        repositoryLocalUrl='file:///var/lib/opsi/repository',
        repositoryRemoteUrl=u'webdavs://configserver1:4447/repository',
        description='The configserver',
        notes='Config 1',
        hardwareAddress=None,
        ipAddress=None,
        inventoryNumber='00000000001',
        networkAddress='192.168.1.0/24',
        maxBandwidth=10000
    )


def testComparingConfigServerToOtherObjectWithSameSettings(configServerReference):
    configServer = OpsiConfigserver(
        id='configserver1.test.invalid',
        opsiHostKey='71234545689056789012123678901234',
        depotLocalUrl='file:///opt/pcbin/install',
        depotRemoteUrl=u'smb://configserver1/opt_pcbin/install',
        repositoryLocalUrl='file:///var/lib/opsi/repository',
        repositoryRemoteUrl=u'webdavs://configserver1:4447/repository',
        description='The configserver',
        notes='Config 1',
        hardwareAddress=None,
        ipAddress=None,
        inventoryNumber='00000000001',
        networkAddress='192.168.1.0/24',
        maxBandwidth=10000
    )

    assert configServerReference == configServer


def testComparingConfigserverToDepotserverFails(configServerReference):
    depotserver = OpsiDepotserver(
        id='depotserver1.test.invalid',
        opsiHostKey='19012334567845645678901232789012',
        depotLocalUrl='file:///opt/pcbin/install',
        depotRemoteUrl='smb://depotserver1.test.invalid/opt_pcbin/install',
        repositoryLocalUrl='file:///var/lib/opsi/repository',
        repositoryRemoteUrl='webdavs://depotserver1.test.invalid:4447/repository',
        description='A depot',
        notes='D€pot 1',
        hardwareAddress=None,
        ipAddress=None,
        inventoryNumber='00000000002',
        networkAddress='192.168.2.0/24',
        maxBandwidth=10000
    )
    assert configServerReference != depotserver


def testComparingConfigServerToSomeDictFails(configServerReference):
    assert configServerReference != {"test": 123}


def testComparingTwoLocalbootProductsWithSameSettings():
    firstProduct = LocalbootProduct(
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
        productClassIds=['localboot-products'],
        windowsSoftwareIds=['{98723-7898adf2-287aab}', 'xxxxxxxx']
    )
    secondProduct = LocalbootProduct(
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
        productClassIds=['localboot-products'],
        windowsSoftwareIds=['xxxxxxxx', '{98723-7898adf2-287aab}']
    )

    assert firstProduct == secondProduct


def testMultivalueUnicodeConfigWithUnicode():
    config = UnicodeConfig(
        id=u'python-opsi.test',
        description="Something from the OPSI forums.",
        possibleValues=[u"Neutron Gerätetechnik GmbH", u"Neutron Mikroelektronik GmbH"],
        defaultValues=[u"Neutron Mikroelektronik GmbH"]
    )

    assert u"Neutron Gerätetechnik GmbH" in config.possibleValues
    assert u"Neutron Mikroelektronik GmbH" in config.possibleValues


@pytest.fixture
def auditHardwareOnHost():
    return AuditHardwareOnHost(
        hostId="client.test.local",
        hardwareClass='COMPUTER_SYSTEM',
        description="Description for auditHardware",
        vendor="Vendor for auditHardware",
        model="Model for auditHardware",
        serialNumber='843391034-2192',
        systemType='Desktop',
        totalPhysicalMemory=1073741824
    )


def testAuditHardwareOnHost__unicode__(auditHardwareOnHost):
    str(auditHardwareOnHost)


def testAuditHardwareOnHost__unicode__with_additionals(auditHardwareOnHost):
    auditHardwareOnHost.name = "Ünicöde name."
    str(auditHardwareOnHost)


def testGettingHelpfulErrorMessageWithBaseclassRelationship():
    """
    Error messages for object.fromHash should be helpful.

    If the creation of a new object from a hash fails the resulting error
    message should show what required attributes are missing.
    """
    try:
        ProductDependency.fromHash({
                "productAction": "setup",
                "requirementType": "after",
                "requiredInstallationStatus": "installed",
                "requiredProductId": "mshotfix",
                "productId": "msservicepack"
                # The following attributes are missing:
                # * productVersion
                # * packageVersion
            })

        assert False, 'Should not get here.'
    except TypeError as typo:
        print(u"Error is: {0!r}".format(typo))

        assert u'__init__() takes at least 6 arguments (6 given)' not in str(typo)

        assert 'productVersion' in str(typo)
        assert 'packageVersion' in str(typo)


def testGettingHelpfulErrorMessageWithBaseclassEntity():
    """
    Error messages for Product.fromHash should be helpful.

    If the creation of a new object from a hash fails the resulting error
    message should show what required attributes are missing.
    """
    try:
        Product.fromHash({
                "id": "newProduct",
                # The following attributes are missing:
                # * productVersion
                # * packageVersion
            })
        assert False, 'Should not get here.'
    except TypeError as typo:
        print(u"Error is: {0!r}".format(typo))

        assert u'__init__() takes at least 6 arguments (6 given)' not in str(typo)

        assert 'productVersion' in str(typo)
        assert 'packageVersion' in str(typo)


def testGetMandatoryConstructorArgsFromConstructorWithNoArguments():
    class NoArgs(object):
        def __init__(self):
            pass

    n = NoArgs()
    with cleanMandatoryConstructorArgsCache():
        args = mandatoryConstructorArgs(n.__class__)

    assert [] == args


def testGetMandatoryConstructorArgsFromConstructorWithOnlyMandatoryArguments():
    class OnlyMandatory(object):
        def __init__(self, give, me, this):
            pass

    om = OnlyMandatory(1, 1, 1)
    with cleanMandatoryConstructorArgsCache():
        args = mandatoryConstructorArgs(om.__class__)

    assert ['give', 'me', 'this'] == args


def testGetMandatoryConstructorArgsFromConstructorWithOnlyOptionalArguments():
    class OnlyOptional(object):
        def __init__(self, only=1, optional=2, arguments=[]):
            pass

    oo = OnlyOptional()
    with cleanMandatoryConstructorArgsCache():
        args = mandatoryConstructorArgs(oo.__class__)

    assert [] == args


def testGetMandatoryConstructorArgsFromConstructorWithMixedArguments():
    class MixedArgs(object):
        def __init__(self, i, want, this, but=0, that=0, notso=0, much=0):
            pass

    ma = MixedArgs(True, True, True)
    with cleanMandatoryConstructorArgsCache():
        args = mandatoryConstructorArgs(ma.__class__)

    assert ['i', 'want', 'this'] == args


def testGetMandatoryConstructorArgsFromConstructorWithWildcardArguments():
    class WildcardOnly(object):
        def __init__(self, *only):
            pass

    wo = WildcardOnly("yeah", "great", "thing")
    with cleanMandatoryConstructorArgsCache():
        args = mandatoryConstructorArgs(wo.__class__)

    assert [] == args


def testGetMandatoryConstructorArgsFromConstructorWithKeywordArguments():
    class Kwargz(object):
        def __init__(self, **kwargs):
            pass

    kw = Kwargz(go=1, get="asdf", them=[], girl=True)
    with cleanMandatoryConstructorArgsCache():
        args = mandatoryConstructorArgs(kw.__class__)

    assert [] == args


def testGetMandatoryConstructorArgsFromConstructorWithMixedWithArgsAndKwargs():
    class KwargzAndMore(object):
        def __init__(self, crosseyed, heart, *more, **kwargs):
            pass

    kwam = KwargzAndMore(False, True, "some", "more", things="here")
    with cleanMandatoryConstructorArgsCache():
        args = mandatoryConstructorArgs(kwam.__class__)

    assert ["crosseyed", "heart"] == args


def testProductNameCanBeVeryLong():
    """
    Namens with a length of more than 128 characters can are supported.
    """
    product = Product(
        id='new_prod',
        name='New Product for Tests',
        productVersion='1.0',
        packageVersion='1.0'
    )

    newName = (
        u'This is a very long name with 128 characters to test the '
        u'creation of long product names that should work now but '
        u'were limited b4'
    )

    product.setName(newName)

    nameFromProd = product.getName()

    assert newName == nameFromProd
    assert 128 == len(nameFromProd)


@pytest.mark.parametrize("propertyClass", [ProductProperty, BoolProductProperty, UnicodeProductProperty])
@pytest.mark.parametrize("requiredAttribute", ["description", "defaultValues"])
def testProductPropertyShowsOptionalArgumentsInRepr(propertyClass, requiredAttribute):
    additionalParam = {requiredAttribute: [True]}
    prodProp = propertyClass('testprod', '1.0', '2', 'myproperty', **additionalParam)

    r = repr(prodProp)
    assert requiredAttribute in r
    assert r.startswith('<')
    assert r.endswith('>')


@pytest.mark.parametrize("propertyClass", [ProductProperty, BoolProductProperty, UnicodeProductProperty])
@pytest.mark.parametrize("attributeName", ['description'])
@pytest.mark.parametrize("attributeValue", [
    'someText',
    pytest.param('', marks=pytest.mark.xfail),
    pytest.param(None, marks=pytest.mark.xfail),
])
def testProductPropertyRepresentationShowsValueIfFilled(propertyClass, attributeName, attributeValue):
    attrs = {attributeName: attributeValue}
    prodProp = propertyClass('testprod', '1.0', '2', 'myproperty', **attrs)

    r = repr(prodProp)
    assert '{0}='.format(attributeName) in r
    assert repr(attributeValue) in r


@pytest.mark.parametrize("propertyClass", [ProductProperty, UnicodeProductProperty])
@pytest.mark.parametrize("requiredAttribute", ["multiValue", "editable", "possibleValues"])
def testProductPropertyShowsOptionalArgumentsInRepr2(propertyClass, requiredAttribute):
    additionalParam = {requiredAttribute: [True]}
    prodProp = propertyClass('testprod', '1.0', '2', 'myproperty', **additionalParam)

    r = repr(prodProp)
    assert requiredAttribute in r
    assert r.startswith('<')
    assert r.endswith('>')


@pytest.mark.parametrize("testValues", [
    [1, 2, 3],
    [False],
    False,
    [True],
    True,
])
def testProductPropertyStateShowSelectedValues(testValues):
    productId = 'testprod'
    propertyId = 'myproperty'
    objectId = 'testobject.foo.bar'
    state = ProductPropertyState(productId, propertyId, objectId, values=testValues)

    r = repr(state)
    assert state.__class__.__name__ in r
    assert productId in r
    assert propertyId in r
    assert objectId in r
    assert 'values=' in r
    assert repr(testValues) in r
    assert r.startswith('<')
    assert r.endswith('>')
