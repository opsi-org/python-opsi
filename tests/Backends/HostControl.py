#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from OPSI.Backend.HostControl import HostControlBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Backend.File import FileBackend

from .File import FileBackendMixin


class HostControlBackendMixin(FileBackendMixin):
    def setUpBackend(self):
        self._fileBackendConfig = {}
        self._fileTempDir = self._copyOriginalBackendToTemporaryLocation()

        self.backend = ExtendedConfigDataBackend(FileBackend(**self._fileBackendConfig))
        # TODO: Make use of a BackendManager Backend.
        # This is to easily check if we have a file backend in the tests.
        # With such a check we can easily skip tests.
        self.backend.backend_createBase()

        self.backend = HostControlBackend(self.backend)
