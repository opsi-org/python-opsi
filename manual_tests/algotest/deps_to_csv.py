# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0

import json
import csv
import sys

try:
  print "opsiadmin-input-file in json format "+sys.argv[1]
  print "csv-output-file"+sys.argv[2]
except:
  print "usage: opsiadmin-input-file csv-output-file"



f = open(sys.argv[1])
data = json.load(f)
f.close()

f=csv.writer(open( sys.argv[2],'wb+'))

for item in data:
    f.writerow([item['productId'], item['requiredProductId'], item['requirementType']])

