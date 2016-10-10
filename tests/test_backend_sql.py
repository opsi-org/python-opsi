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

import sys
import unittest

import pytest

import OPSI.Backend.SQL as sql
import OPSI.Object as ob

from .helpers import cleanMandatoryConstructorArgsCache as cmcac

if sys.version_info > (3, ):
    long = int


@pytest.fixture
def sqlBackendWithoutConnection():
    backend = sql.SQLBackend()
    backend._sql = sql.SQL()

    yield backend


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


@pytest.fixture
def cleanMandatoryConstructorArgsCache():
    with cmcac():
        yield


def testUniqueConditionForHostObject(sqlBackendWithoutConnection, cleanMandatoryConstructorArgsCache):
    host = ob.Host('foo.bar.baz')
    assert "`hostId` = 'foo.bar.baz'" == sqlBackendWithoutConnection._uniqueCondition(host)


def testUniqueConditionOptionalParametersAreIgnored(sqlBackendWithoutConnection, cleanMandatoryConstructorArgsCache):
    host = ob.Host('foo.bar.baz', inventoryNumber='ABC+333')

    assert "`hostId` = 'foo.bar.baz'" == sqlBackendWithoutConnection._uniqueCondition(host)


def testUniqueConditionMultipleParametersAreJoinedWithAnAnd(sqlBackendWithoutConnection, cleanMandatoryConstructorArgsCache):
    softwareLicense = ob.SoftwareLicense('a', 'b')
    condition = sqlBackendWithoutConnection._uniqueCondition(softwareLicense)

    assert ' and ' in condition
    assert "`softwareLicenseId` = 'a' and `licenseContractId` = 'b'" == condition


def testUniqueConditionForHostGroupHasTypeAppended(sqlBackendWithoutConnection, cleanMandatoryConstructorArgsCache):
    group = ob.ProductGroup('t')
    condition = sqlBackendWithoutConnection._uniqueCondition(group)

    assert "`groupId` = 't'" in condition
    assert "and" in condition
    assert "`type` = 'ProductGroup'" in condition


def testUniqueConditionForProductGroupHasTypeAppended(sqlBackendWithoutConnection, cleanMandatoryConstructorArgsCache):
    group = ob.HostGroup('hg')
    condition = sqlBackendWithoutConnection._uniqueCondition(group)

    assert "`groupId` = 'hg'" in condition
    assert "and" in condition
    assert "`type` = 'HostGroup'" in condition


def testUniqueConditionForBooleanParameters(sqlBackendWithoutConnection, cleanMandatoryConstructorArgsCache):
    class Foo(object):
        def __init__(self, true, false):
            self.true = true
            self.false = false

    condition = sqlBackendWithoutConnection._uniqueCondition(Foo(True, False))

    assert "`true` = 1" in condition
    assert "and" in condition
    assert "`false` = 0" in condition


def testAccessingParametersWithAttributenamesFails(sqlBackendWithoutConnection, cleanMandatoryConstructorArgsCache):
    class Foo2(object):
        def __init__(self, something):
            self._something = something

    with pytest.raises(AttributeError):
        sqlBackendWithoutConnection._uniqueCondition(Foo2(True))


def testUniqueConditionMandatoryParametersAreSkippedIfValueIsNone(sqlBackendWithoutConnection, cleanMandatoryConstructorArgsCache):
    assert '' == sqlBackendWithoutConnection._uniqueCondition(FooParam(None))


@pytest.mark.parametrize("number", [1, 2.3, 4])
def testParameterIsNumber(sqlBackendWithoutConnection, number, cleanMandatoryConstructorArgsCache):
    assert '`param` = {0!s}'.format(number) == sqlBackendWithoutConnection._uniqueCondition(FooParam(number))


class FooParam(object):
    def __init__(self, param):
        self.param = param


def testCreatingUniqueHardwareConditionIgnoresHardwareClassAndType(sqlBackendWithoutConnection):
    hwDict = {
        "hardwareClass": "abc",
        "type": 'def'
    }

    assert '' == sqlBackendWithoutConnection._uniqueAuditHardwareCondition(hwDict)


def testCreatingConditionWithNoneTypes(sqlBackendWithoutConnection):
    testDict = {
        "abc": None,
        'def': [None]
    }

    condition = sqlBackendWithoutConnection._uniqueAuditHardwareCondition(testDict)
    assert u'`abc` is NULL' in condition
    assert u' and ' in condition
    assert u'`def` is NULL' in condition


def testAddingMultipleParametersWithAnd(sqlBackendWithoutConnection):
    testDict = {
        "abc": None,
        'def': [None]
    }

    condition = sqlBackendWithoutConnection._uniqueAuditHardwareCondition(testDict)
    assert u' and ' in condition
    assert not condition.strip().endswith('and')
    assert not condition.strip().startswith('and')


def testCreatingQueryWithVariousTypes(sqlBackendWithoutConnection):
    testDict = {
        "int": 1,
        "float": 2.3,
        "long": long(4),
        "bool_true": True,
        "bool_false": False,
        "string": "caramba",
    }

    condition = sqlBackendWithoutConnection._uniqueAuditHardwareCondition(testDict)
    assert u' and ' in condition
    assert u'`int` = 1' in condition
    assert u'`float` = 2.3' in condition
    assert u'`long` = 4' in condition
    assert u'`bool_false` = False' in condition
    assert u'`bool_true` = True' in condition
    assert u"`string` = 'caramba'" in condition


@pytest.mark.parametrize("query", ["SELECT something"])
def testAvoidingMaliciousQueryOnlySelectAllowed(query):
    assert query == returnQueryAfterCheck(query)


@pytest.mark.parametrize("query", [
    "ALTER TABLE blabla",
    "DROP TABLE blabla"
])
def testOnlySelectAllowedRaisesExceptionWithNonSelectQuery(query):
    with pytest.raises(ValueError):
        returnQueryAfterCheck(query)


def returnQueryAfterCheck(query):
    sql.onlyAllowSelect(query)
    return query
