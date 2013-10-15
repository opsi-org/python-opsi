#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import absolute_import

from .Audit import AuditTestsMixin
from .Backend import BackendTestsMixin
from .Configs import ConfigTestsMixin, ConfigStateTestsMixin
from .ExtendedBackend import ExtendedBackendTestsMixin
from .Groups import GroupTestsMixin, ObjectToGroupTestsMixin
from .Licenses import LicensesTestMixin
from .Products import (ProductPropertiesTestMixin, ProductDependenciesTestMixin,
    ProductsTestMixin, ProductsOnClientTestsMixin,
    ProductsOnDepotTestsMixin, ProductPropertyStateTestsMixin)


class BackendTestMixin(ConfigStateTestsMixin, ProductPropertiesTestMixin,
    ProductDependenciesTestMixin, LicensesTestMixin, AuditTestsMixin,
    ConfigTestsMixin, ProductsTestMixin, ProductsOnClientTestsMixin,
    ProductsOnDepotTestsMixin, ProductPropertyStateTestsMixin, GroupTestsMixin,
    ObjectToGroupTestsMixin, ExtendedBackendTestsMixin, BackendTestsMixin):
    """
    Class collecting functional backend tests.

    MultiThreadingTestMixin and BackendPerformanceTest are excluded.
    Please inherit them manually if you feel the need.
    """

