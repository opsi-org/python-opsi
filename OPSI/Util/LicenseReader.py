#!/usr/bin/python
# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2015-2016 uib GmbH - http://www.uib.de/

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
Reading Windows licenses from Regsitry or BIOS

:copyright: uib GmbH <info@uib.de>
:author: Mathias Radtke <m.radtke@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import codecs
from OPSI.System.Posix import execute, which

def decodeDigitalProductId(data):
        '''
        Based on VBScript of Mark D. MacLachlan, The Spider's Parlor
        http://www.thespidersparlor.com
        '''
        offset = 52
        i = 28
        chars = "BCDFGHJKMPQRTVWXY2346789"
        productKey = ""
        while (i >= 0):
                acc = 0
                j = 14
                while (j >= 0):
                        acc = acc * 256
                        acc = ord(data[j+offset]) + acc
                        x = acc / 24
                        if x > 255:
                                x = 255
                        data = data[:j+offset] + chr(x) + data[j+offset+1:]
                        acc = acc % 24
                        j -= 1
                i -= 1
                productKey = chars[acc] + productKey
                if (((29 - i) % 6) == 0) and (i != -1):
                        i -= 1
                        productKey = "-" + productKey
        return productKey

def get_software_reg(software_hive):
        try:
                out_file = '/tmp/export.reg'
                subprocess.call(['/usr/sbin/reged.static -x "' + software_hive + '" "HKEY_LOCAL_MACHINE\Software" "Microsoft\Windows NT\CurrentVersion" "' + out_file + '" 1>/dev/null 2>/dev/null'], shell=True)
                f = codecs.open(out_file, 'r', 'iso-8859-1')
                reg = {}
                cur_section = None
                cur_option = None
                for line in f.readlines():
                        line = line.strip()
                        if not line:
                                continue
                        if line.startswith('[') and line.endswith(']'):
                                cur_section = line[1:-1]
                                reg[cur_section] = {}
                                cur_option = None
                        elif line.startswith('"'):
                                (cur_option, value) = line.split('=', 1)
                                cur_option = cur_option.replace('"', '').strip()
                                reg[cur_section][cur_option] = value.strip().rstrip('\\')
                        elif cur_section and cur_option:
                                reg[cur_section][cur_option] += line.strip().rstrip('\\')
                f.close()
                return reg
        finally:
                os.chdir('/')

def get_product_key_from_registry(software_reg):
        data = software_reg['HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion']['DigitalProductId'].split(':')[1].replace(',','')
        return decode_digital_product_id(binascii.unhexlify(data))

def getProductKeyFrom_bios():
	with codecs.open ('/sys/firmware/acpi/tables/MSDM', encoding='iso-8859-1') as biosKey:
		for i, line in biosKey:
			if i == 1:
				return line
#        return execute('%s -b MSDM | dd bs=1 skip=56 2>/dev/null' % which('acpidump')[0].strip()

