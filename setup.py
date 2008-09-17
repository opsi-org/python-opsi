#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from distutils.core import setup, Extension

setup (
    name = 'python-opsi',
    version = '3.3.0.25',
    description = 'opsi python library',
    long_description = 'opsi python library.',
    author = "uib GmbH",
    author_email = 'info@uib.de',
    license = 'GPL',
    url='http://www.opsi.org',
    py_modules = [
	'OPSI'
    ],
)
