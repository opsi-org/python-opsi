#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Manual test run for pinging clients.
"""

from OPSI.Util.Ping import ping, verbose_ping


if (__name__ == "__main__"):
    verbose_ping("heise.de")
    verbose_ping("google.com")
    verbose_ping("192.168.1.14")
    print(ping("192.168.1.14"))
