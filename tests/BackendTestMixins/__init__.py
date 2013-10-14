#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import absolute_import

import time
import random

from OPSI.Logger import Logger, LOG_NOTICE
from OPSI.Object import *
from .Configs import ConfigTestsMixin, ConfigStateTestsMixin
from .Products import (ProductPropertiesTestMixin, ProductDependenciesTestMixin,
    ProductsTestMixin, ProductsOnClientTestsMixin,
    ProductsOnDepotTestsMixin, ProductPropertyStateTestsMixin)
from .Licenses import LicensesTestMixin
from .Audit import AuditTestsMixin
from .Groups import GroupTestsMixin, ObjectToGroupTestsMixin
from .ExtendedBackend import ExtendedBackendTestsMixin
from .Backend import BackendTestsMixin

logger = Logger()


class BackendTestMixin(ConfigStateTestsMixin, ProductPropertiesTestMixin,
    ProductDependenciesTestMixin, LicensesTestMixin, AuditTestsMixin,
    ConfigTestsMixin, ProductsTestMixin, ProductsOnClientTestsMixin,
    ProductsOnDepotTestsMixin, ProductPropertyStateTestsMixin, GroupTestsMixin,
    ObjectToGroupTestsMixin, ExtendedBackendTestsMixin, BackendTestsMixin):
    """
    Class collecting all possible backend tests.
    """

