# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2015 uib GmbH <info@uib.de>

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
Testing opsi SQL backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import sys
import unittest

import OPSI.Backend.SQL as sql
import OPSI.Object as ob

from .helpers import createTemporaryTestfile

if sys.version_info > (3, ):
    long = int


class SQLBackendWithoutConnectionTestCase(unittest.TestCase):
    """
    Testing the backend functions that do not require an connection
    to an actual database.
    """
    def setUp(self):
        self.backend = sql.SQLBackend()
        self.backend._sql = sql.SQL()

    def tearDown(self):
        del self.backend


class FilterToSQLTestCase(SQLBackendWithoutConnectionTestCase):
    def testCreatingFilter(self):
        self.assertEquals('', self.backend._filterToSql())
        self.assertEquals(u'(`lol` = 0)', self.backend._filterToSql({'lol': False}))

    def testCreatingFilterHasParentheses(self):
        self.assertTrue(self.backend._filterToSql({'lol': False}).startswith('('))
        self.assertTrue(self.backend._filterToSql({'lol': False}).endswith(')'))

    def testNoFilterForNoneValues(self):
        result = self.backend._filterToSql({'a': False, 'b': None})
        self.assertTrue('b' not in result)
        self.assertTrue('NULL' not in result)
        self.assertTrue('None' not in result)

    def testCreatingFilterForNoneInList(self):
        self.assertTrue('`a` is NULL' in self.backend._filterToSql({'a': [None]}))

    def testEmptyListsGetSkipped(self):
        self.assertTrue('a' not in self.backend._filterToSql({'a': []}))
        self.assertEquals('', self.backend._filterToSql({'a': []}))

    def testBoolValueRepresentation(self):
        self.assertTrue('0' in self.backend._filterToSql({'a': False}))
        self.assertTrue('1' in self.backend._filterToSql({'a': True}))

        self.assertEquals(
            u'(`a` = 1) and (`b` = 0)',
            self.backend._filterToSql({'a': True, 'b': False})
        )

    def testMultipleValuesAreAddedWithAnAnd(self):
        self.assertTrue(
            u' and ' in self.backend._filterToSql({'a': True, 'b': False})
        )

    def testNumberRepresentation(self):
        self.assertEquals(u'(`a` = 1)', self.backend._filterToSql({'a': 1}))
        self.assertEquals(u'(`b` = 2.3)', self.backend._filterToSql({'b': 2.3}))
        self.assertEquals(u'(`c` = 4)', self.backend._filterToSql({'c': long(4)}))

    def testCreatingFilterForStringValue(self):
        self.assertEquals(u"(`a` = 'b')", self.backend._filterToSql({'a': "b"}))

    def testListOfValuesCreatesAnOrExpression(self):
        result = self.backend._filterToSql({'a': [1, 2]})
        self.assertTrue(u' or ' in result)
        self.assertTrue(u'1' in result)
        self.assertTrue(u'2' in result)

        anotherResult = self.backend._filterToSql({'a': [1, 2], 'b': False})
        self.assertEquals(u'(`a` = 1 or `a` = 2) and (`b` = 0)', anotherResult)

    def testCreatingFilterWithWildcard(self):
        self.assertEquals(u"(`a` LIKE '%bc')", self.backend._filterToSql({'a': '*bc'}))

    def testCreatingFilterWithGreaterOrLowerOrEqualSign(self):
        self.assertEquals(u"(`a` > 1)", self.backend._filterToSql({'a': '> 1'}))
        self.assertEquals(u"(`a` < 1)", self.backend._filterToSql({'a': '< 1'}))
        self.assertEquals(u"(`a` = 1)", self.backend._filterToSql({'a': '= 1'}))
        self.assertEquals(u"(`a` <=> 1)", self.backend._filterToSql({'a': '<=> 1'}))


class QueryCreationTestCase(SQLBackendWithoutConnectionTestCase):
    def testCreatingQueryIncludesTableName(self):
        self.assertTrue("foo" in self.backend._createQuery('foo'))

    def testWithoutAttributesEverythingIsSelected(self):
        self.assertTrue(u'select * from' in self.backend._createQuery('foo'))

    def testDefiningColumnsToSelect(self):
        self.assertTrue(u'`first`,`second`' in self.backend._createQuery('foo', ['first', 'second']))

    def testHavingFilterAddsWhereClause(self):
        self.assertTrue(u'where' not in self.backend._createQuery('foo'))
        self.assertTrue(u'where' in self.backend._createQuery('foo', filter={'a': 1}))


class UniqueConditionTestCase(SQLBackendWithoutConnectionTestCase):
    """
    Testing the creation of an unique condition.

    **Notes**: Because of the function that reads the mandatory parameters
    and its caching function the Foo-Classes in the tests must all be
    named different!
    """

    def testHostObject(self):
        host = ob.Host('foo.bar.baz')
        self.assertEquals(
            "`hostId` = 'foo.bar.baz'",
            self.backend._uniqueCondition(host)
        )

    def testOptionalParametersAreIgnored(self):
        host = ob.Host('foo.bar.baz', inventoryNumber='ABC+333')

        self.assertEquals(
            "`hostId` = 'foo.bar.baz'",
            self.backend._uniqueCondition(host)
        )

    def testMultipleParametersAreJoinedWithAnAnd(self):
        license = ob.SoftwareLicense('a', 'b')
        condition = self.backend._uniqueCondition(license)

        self.assertTrue(' and ' in condition)
        self.assertEquals(
            "`softwareLicenseId` = 'a' and `licenseContractId` = 'b'",
            condition
        )

    def testConditionForHostGroupHasTypeAppended(self):
        group = ob.ProductGroup('t')
        condition = self.backend._uniqueCondition(group)

        self.assertTrue("`groupId` = 't'" in condition)
        self.assertTrue("and" in condition)
        self.assertTrue("`type` = 'ProductGroup'" in condition)

    def testConditionForProductGroupHasTypeAppended(self):
        group = ob.HostGroup('hg')
        condition = self.backend._uniqueCondition(group)

        self.assertTrue("`groupId` = 'hg'" in condition)
        self.assertTrue("and" in condition)
        self.assertTrue("`type` = 'HostGroup'" in condition)

    def testBooleanParameters(self):
        class Foo(object):
            def __init__(self, true, false):
                self.true = true
                self.false = false

        f00 = Foo(True, False)
        condition = self.backend._uniqueCondition(f00)

        self.assertTrue("`true` = 1" in condition)
        self.assertTrue("and" in condition)
        self.assertTrue("`false` = 0" in condition)

    def testAccessingParametersWithAttributenamesFails(self):
        class Foo2(object):
            def __init__(self, something):
                self._something = something

        f00 = Foo2(True)

        self.assertRaises(AttributeError, self.backend._uniqueCondition, f00)

    def testMandatoryParametersAreSkippedIfValueIsNone(self):
        class Foo3(object):
            def __init__(self, something):
                self.something = something

        f00 = Foo3(None)

        self.assertEquals('', self.backend._uniqueCondition(f00))

    def testParameterIsNumber(self):
        class FooParam(object):
            def __init__(self, param):
                self.param = param

        self.assertEquals('`param` = 1', self.backend._uniqueCondition(FooParam(1)))
        self.assertEquals('`param` = 2.3', self.backend._uniqueCondition(FooParam(2.3)))
        self.assertEquals('`param` = 4', self.backend._uniqueCondition(FooParam(long(4))))


class UniqueAuditHardwareConditionTestCase(SQLBackendWithoutConnectionTestCase):
    def testCreatingUniqueHardwareConditionIgnoresHardwareClassAndType(self):
        hwDict = {
            "hardwareClass": "abc",
            "type": 'def'
        }

        self.assertEquals('', self.backend._uniqueAuditHardwareCondition(hwDict))

    def testCreatingConditionWithNoneTypes(self):
        testDict = {
            "abc": None,
            'def': [None]
        }

        condition = self.backend._uniqueAuditHardwareCondition(testDict)
        self.assertTrue(u'`abc` is NULL' in condition)
        self.assertTrue(u' and ' in condition)
        self.assertTrue(u'`def` is NULL' in condition)

    def testAddingMultipleParametersWithAnd(self):
        testDict = {
            "abc": None,
            'def': [None]
        }

        condition = self.backend._uniqueAuditHardwareCondition(testDict)
        self.assertTrue(u' and ' in condition)
        self.assertFalse(condition.strip().endswith('and'))
        self.assertFalse(condition.strip().startswith('and'))

    def testCreatingQueryWithVariousTypes(self):
        testDict = {
            "int": 1,
            "float": 2.3,
            "long": long(4),
            "bool_true": True,
            "bool_false": False,
            "string": "caramba",
        }

        condition = self.backend._uniqueAuditHardwareCondition(testDict)
        self.assertTrue(u' and ' in condition)
        self.assertTrue(u'`int` = 1' in condition)
        self.assertTrue(u'`float` = 2.3' in condition)
        self.assertTrue(u'`long` = 4' in condition)
        self.assertTrue(u'`bool_false` = False' in condition)
        self.assertTrue(u'`bool_true` = True' in condition)
        self.assertTrue(u"`string` = 'caramba'" in condition)


class AvoidingMaliciousQueryTestCase(SQLBackendWithoutConnectionTestCase):
    def testOnlySelectAllowedDecorator(self):
        def returnQuery(query):
            sql.onlyAllowSelect(query)
            return query

        self.assertRaises(ValueError, returnQuery, "ALTER TABLE blabla")
        self.assertRaises(ValueError, returnQuery, "DROP TABLE blabla")

        testQuery = "SELECT something"
        self.assertEquals(testQuery, returnQuery(testQuery))


def testAlteringTableAfterChangeOfHardwareAuditConfig(sqlBackendCreationContextManager):
    """
    Test if adding and altering hardware audit tables works.

    We must be able to alter the table after a change of the hardware
    audit configuration took place. This is a commong operation during
    updates.
    """
    configDir = os.path.join(os.path.dirname(__file__), 'testdata', 'backend')
    pathToOldConfig = os.path.join(configDir, 'small_hwaudit.conf')
    pathToNewConfig = os.path.join(configDir, 'small_extended_hwaudit.conf')

    with createTemporaryTestfile(pathToOldConfig) as oldConfig:
        with sqlBackendCreationContextManager(auditHardwareConfigFile=oldConfig) as backend:
            backend.backend_createBase()

            with createTemporaryTestfile(pathToNewConfig) as newConfig:
                backend._auditHardwareConfigFile = newConfig
                backend._setAuditHardwareConfig(backend.auditHardware_getConfig())

                backend.backend_createBase()
