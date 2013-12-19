#!/usr/bin/env python
#-*- coding: utf-8 -*-

class BackendMixin(object):
    """
    Base class for backend test mixins.

    :param CREATES_INVENTORY_HISTORY: Set to true if the backend keeps a \
history of the inventory. This will affects tests!
    :type CREATES_INVENTORY_HISTORY: bool
    """

    CREATES_INVENTORY_HISTORY = False

    def setUpBackend(self):
        pass

    def tearDownBackend(self):
        pass
