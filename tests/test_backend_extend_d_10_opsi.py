#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
import unittest

from OPSI.Backend.BackendManager import BackendManager
from OPSI.Logger import Logger, LOG_DEBUG, LOG_DEBUG2
from OPSI.Object import OpsiClient, LocalbootProduct, ProductOnClient, ProductDependency


logger = Logger()
logger.setConsoleLevel(LOG_DEBUG2)
logger.setConsoleColor(True)

class BackendExtendedThroughOPSITestCase(unittest.TestCase):
    BACKEND_SUBFOLDER = 'data'

    def setUp(self):


        self.TMP_CONFIG_DIR = self._copyOriginalBackendToTemporaryLocation()

        self.backendManager = BackendManager(
            backend='file',
            backendconfigdir=os.path.join(self.TMP_CONFIG_DIR, self.BACKEND_SUBFOLDER, 'backends'),
            extensionconfigdir=os.path.join(self.TMP_CONFIG_DIR, self.BACKEND_SUBFOLDER, 'backendManager', 'extend.d')
        )

        self.backendManager.backend_createBase()

        self.fillBackend()

    @classmethod
    def _copyOriginalBackendToTemporaryLocation(cls):
        tempDir = tempfile.mkdtemp()
        originalBackendDir = cls._getOriginalBackendLocation()

        shutil.copytree(originalBackendDir, os.path.join(tempDir, cls.BACKEND_SUBFOLDER))

        cls._setupFileBackend(tempDir)
        cls._patchDispatchConfig(tempDir)

        return tempDir

    @staticmethod
    def _getOriginalBackendLocation():
        return os.path.normpath(
            os.path.join(
                os.path.dirname(__file__), '..', 'data'
            )
        )

    @classmethod
    def _setupFileBackend(cls, targetDirectory):
        cls._patchFileBackend(targetDirectory)
        cls._createClientTemplates(os.path.join(targetDirectory, 'baseDir'))

    @classmethod
    def _patchFileBackend(cls, backendDirectory):
        baseDir = os.path.join(backendDirectory, 'baseDir', 'config')
        hostKeyDir = os.path.join(backendDirectory, 'keyFiles')

        config_file = os.path.join(backendDirectory, cls.BACKEND_SUBFOLDER, 'backends', 'file.conf')
        with open(config_file, 'w') as config:
            new_configuration = """
# -*- coding: utf-8 -*-

module = 'File'
config = {{
    "baseDir":     u"{basedir}",
    "hostKeyFile": u"{keydir}",
}}
""".format(basedir=baseDir, keydir=hostKeyDir)

            config.write(new_configuration)

    @classmethod
    def _createClientTemplates(cls, targetDirectory):
        templateDirectory = os.path.join(targetDirectory, 'config', 'templates')
        os.makedirs(templateDirectory)

        with open(os.path.join(templateDirectory, 'pcproto.ini'), 'w') as template:
            template.write('')

    @classmethod
    def _patchDispatchConfig(cls, targetDirectory):
        configDir = os.path.join(targetDirectory, 'data', 'backends')

        with open(os.path.join(configDir, 'dispatch.conf'), 'w') as dpconf:
            dpconf.write(
"""
.*                 : file
"""
)

    def fillBackend(self):
        client = OpsiClient(
            id='backend-test-1.vmnat.local',
            description='Unittest Test client.'
        )
        self.client = client

        self.backendManager.host_createObjects([client])

        firstProduct = LocalbootProduct('already_installed', '1.0', '1.0')
        secondProduct = LocalbootProduct('to_install', '1.0', '1.0')

        prodDependency = ProductDependency(
            productId=firstProduct.id,
            productVersion=firstProduct.productVersion,
            packageVersion=firstProduct.packageVersion,
            productAction='setup',
            requiredProductId=secondProduct.id,
            # requiredProductVersion=secondProduct.productVersion,
            # requiredPackageVersion=secondProduct.packageVersion,
            requiredAction='setup',
            requiredInstallationStatus='installed',
            requirementType='after'
        )

        self.backendManager.product_createObjects([firstProduct, secondProduct])
        self.backendManager.productDependency_createObjects([prodDependency])

        poc = ProductOnClient(
            clientId=client.id,
            productId=secondProduct.id,
            productType=secondProduct.getType(),
            productVersion=secondProduct.productVersion,
            packageVersion=secondProduct.packageVersion,
            installationStatus='installed',
            actionResult='successful'
        )

        self.backendManager.productOnClient_createObjects([poc])

    def tearDown(self):
        if os.path.exists(self.TMP_CONFIG_DIR):
            shutil.rmtree(self.TMP_CONFIG_DIR)

        del self.backendManager

    def testSetProductActionRequestWithDependenciesSetsProductsToSetup(self):
        """
        An product action request should set products to setup even if they \
are already installed on a client.
        """
        self.backendManager.setProductActionRequestWithDependencies(
            'to_install',
            'backend-test-1.vmnat.local',
            'setup'
        )


if __name__ == '__main__':
    unittest.main()
