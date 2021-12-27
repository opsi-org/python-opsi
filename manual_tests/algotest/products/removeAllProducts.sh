#!/bin/sh
for product in `opsi-package-manager -l | grep "-sequ" | cut -f 4 -d " "`;do
        opsi-package-manager -r  $product
done

