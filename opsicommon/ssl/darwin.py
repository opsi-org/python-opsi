# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""

from OpenSSL import crypto

__all__ = ["install_ca", "remove_ca"]


def install_ca(ca_cert: crypto.X509):
	raise NotImplementedError("Not implemented on macOS")


def remove_ca(subject_name: str) -> bool:
	raise NotImplementedError("Not implemented on macOS")
