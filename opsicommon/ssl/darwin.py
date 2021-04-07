# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
This file is part of opsi - https://www.opsi.org
"""

from OpenSSL import crypto

__all__ = ["install_ca", "remove_ca"]


def install_ca(ca_cert: crypto.X509):
	raise NotImplementedError("Not implemented on macOS")


def remove_ca(subject_name: str) -> bool:
	raise NotImplementedError("Not implemented on macOS")
