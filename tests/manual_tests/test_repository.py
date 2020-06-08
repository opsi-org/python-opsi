#! /usr/bin/env python3
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2019 uib GmbH <info@uib.de>

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
opsi python library - Repository
================================

Functionality to work with opsi repositories.


:copyright: uib GmbH <info@uib.de>
:license: GNU Affero General Public License version 3
.. codeauthor:: Jan Schneider <j.schneider@uib.de>
.. codeauthor:: Erol Ueluekmen <e.ueluekmen@uib.de>
.. codeauthor:: Niko Wenselowski <n.wenselowski@uib.de>
"""

from OPSI.Logger import LOG_DEBUG, LOG_DEBUG2

def workingWithRepositories():
    tempDir = '/tmp/testdir'
    #if os.path.exists(tempDir):
    #   shutil.rmtree(tempDir)
    if not os.path.exists(tempDir):
        os.mkdir(tempDir)

    logger.notice("getRepository")

    #sourceDepot = getRepository(url = u'smb://bonifax/opt_pcbin/install', username = u'pcpatch', password = u'xxx', mount = False)

    #sourceDepot.listdir()
    #print sourceDepot.listdir()

    sourceDepot = getRepository(url = u'smb://lelap530.vmnat.local/opsi_depot', username = u'pcpatch', password = u'linux123', mountPoint = tempDir,  mountOptions = { "iocharset": 'utf8' } )

    print(sourceDepot.listdir())

    sourceDepot.download(u'winxppro/i386/IEXPLORE.CH_', u'/mnt/hd/IEXPLORE.CH_')
    sourceDepot.download(u'winxppro/i386/NTKRNLMP.EX_', u'/mnt/hd/NTKRNLMP.EX_')

    #rep = HTTPRepository(url = u'webdav://download.uib.de:80/opsi4.0', dynamicBandwidth = True)#, maxBandwidth = 100000)
    #rep = HTTPRepository(url = u'webdav://download.uib.de:80/opsi4.0', maxBandwidth = 1000)
    #rep = HTTPRepository(url = u'webdav://download.uib.de:80/opsi4.0', maxBandwidth = 10000)
    #rep = HTTPRepository(url = u'webdav://download.uib.de:80/opsi4.0', maxBandwidth = 100000)
    #rep = HTTPRepository(url = u'webdav://download.uib.de:80/opsi4.0', maxBandwidth = 1000000)
    #rep.download(u'opsi4.0-client-boot-cd_20100927.iso', '/tmp/opsi4.0-client-boot-cd_20100927.iso', progressSubject=None)
    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/repository', username = u'stb-40-wks-101.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3', maxBandwidth = 100)
    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/repository', username = u'stb-40-wks-101.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3', maxBandwidth = 1000)
    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/repository', username = u'stb-40-wks-101.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3', maxBandwidth = 1000000)
    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/repository', username = u'stb-40-wks-101.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3', maxBandwidth = 10000000)
    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/repository', username = u'stb-40-wks-101.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3', dynamicBandwidth = True, maxBandwidth = 1000)
    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/repository', username = u'stb-40-wks-101.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3', dynamicBandwidth = True, maxBandwidth = 100000)
    #rep.download(u'ooffice3_3.3-2.opsi', '/tmp/ooffice3_3.3-2.opsi', progressSubject=None)

    #sourceDepot = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/depot', username = u'stb-40-wks-101.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3')
    #dtlds = DepotToLocalDirectorySychronizer(sourceDepot, destinationDirectory = tempDir, productIds=['opsi-client-agent', 'opsi-winst', 'thunderbird'], maxBandwidth=0, dynamicBandwidth=False)
    #dtlds.synchronize()

    #sourceDepot = getRepository(url = u'cifs://bonifax/opt_pcbin/install', username = u'pcpatch', password = u'xxxxxx', mountOptions = { "iocharset": 'iso8859-1' })
    #dtlds = DepotToLocalDirectorySychronizer(sourceDepot, destinationDirectory = tempDir, productIds=['opsi-client-agent', 'opsi-winst', 'thunderbird'], maxBandwidth=0, dynamicBandwidth=False)
    #dtlds.synchronize()

    #print rep.listdir()
    #print rep.isdir('javavm')

    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/depot', username = u'stb-40-wks-101.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3')
    #print rep.listdir()
    #rep.disconnect()

    #destination = os.path.join(tempDir, 'AdbeRdr940_de_DE.msi')
    #rep.download('/acroread9/files/AdbeRdr940_de_DE.msi', destination, endByteNumber = 20000000)
    #rep.download('/acroread9/files/AdbeRdr940_de_DE.msi', destination, startByteNumber = 20000001)

    #rep = getRepository(url = u'cifs://bonifax/opt_pcbin/install', username = u'', password = u'', mountOptions = { "iocharset": 'iso8859-1' })
    #print rep.listdir()
    #print rep.isdir('javavm')
    #
    #tempFile = '/tmp/testfile.bin'
    #tempDir = '/tmp/testdir'
    #tempDir2 = '/tmp/testdir2'
    #if os.path.exists(tempFile):
    #   os.unlink(tempFile)
    #if os.path.exists(tempDir):
    #   shutil.rmtree(tempDir)
    #if os.path.exists(tempDir2):
    #   shutil.rmtree(tempDir2)

    #rep = HTTPRepository(url = u'http://download.uib.de:80', username = u'', password = u'')
    #rep.download(u'press-infos/logos/opsi/opsi-Logo_4c.pdf', tempFile, progressSubject=None)
    #os.unlink(tempFile)

    #rep = HTTPRepository(url = u'http://download.uib.de', username = u'', password = u'')
    #rep.download(u'press-infos/logos/opsi/opsi-Logo_4c.pdf', tempFile, progressSubject=None)
    #os.unlink(tempFile)
    #
    #rep = HTTPRepository(url = u'http://download.uib.de:80', username = u'', password = u'', proxy="http://192.168.1.254:3128")
    #rep.download(u'press-infos/logos/opsi/opsi-Logo_4c.pdf', tempFile, progressSubject=None)
    #os.unlink(tempFile)
    #
    #rep = HTTPRepository(url = u'http://download.uib.de', username = u'', password = u'', proxy="http://192.168.1.254:3128")
    #rep.download(u'press-infos/logos/opsi/opsi-Logo_4c.pdf', tempFile, progressSubject=None)
    #os.unlink(tempFile)
    #
    #rep = HTTPRepository(url = u'https://forum.opsi.org:443', username = u'', password = u'')
    #rep.download(u'/index.php', tempFile, progressSubject=None)
    #os.unlink(tempFile)

    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/repository', username = u'autotest001.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3')
    #rep.download(u'xpconfig_2.6-1.opsi', tempFile, progressSubject=None)
    #for c in rep.content():
    #   print c
    #print rep.getCountAndSize()
    #print rep.exists('shutdownwanted_1.0-2.opsi')
    #print rep.exists('notthere')
    #rep.copy('shutdownwanted_1.0-2.opsi', tempDir)
    #shutil.rmtree(tempDir)
    #os.makedirs(tempDir)
    #rep.copy('shutdownwanted_1.0-2.opsi', tempDir)
    #rep.copy('shutdownwanted_1.0-2.opsi', tempDir)
    #
    #shutil.rmtree(tempDir)

    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/depot', username = u'autotest001.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3')
    #for c in rep.content('winvista-x64/installfiles', recursive=True):
    #   print c
    #rep.copy(source = 'winvista-x64/installfiles', destination = tempDir)

    #from UI import UIFactory
    #ui = UIFactory()
    #from Message import ProgressObserver
    #overallProgressSubject = ProgressSubject(id = u'copy_overall', title = u'Copy test')
    #currentProgressSubject = ProgressSubject(id = u'copy_current', title = u'Copy test')
    ##class SimpleProgressObserver(ProgressObserver):
    ##  def messageChanged(self, subject, message):
    ##      print u"%s" % message
    ##
    ##  def progressChanged(self, subject, state, percent, timeSpend, timeLeft, speed):
    ##      print u"state: %s, percent: %0.2f%%, timeSpend: %0.2fs, timeLeft: %0.2fs, speed: %0.2f" \
    ##          % (state, percent, timeSpend, timeLeft, speed)
    ##progressSubject.attachObserver(SimpleProgressObserver())
    ##copyBox = ui.createCopyProgressBox(width = 120, height = 20, title = u'Copy', text = u'')
    #copyBox = ui.createCopyDualProgressBox(width = 120, height = 20, title = u'Copy', text = u'')
    #copyBox.show()
    #copyBox.setOverallProgressSubject(overallProgressSubject)
    #copyBox.setCurrentProgressSubject(currentProgressSubject)

    #progressSubject.attachObserver(copyBox)

    #overallProgressSubject = None
    #currentProgressSubject = None
    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/depot', username = u'autotest001.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3')
    #for c in rep.content('swaudit', recursive=True):
    #   print c

    #rep = WebDAVRepository(url = u'webdavs://192.168.1.14:4447/depot/swaudit', username = u'autotest001.uib.local', password = u'b61455728859cfc9988a3d9f3e2343b3')
    #for c in rep.content('swaudit', recursive=True):
    #   print c
    #print rep.listdir()
    #rep.copy(source = '/*', destination = tempDir, overallProgressSubject = overallProgressSubject, currentProgressSubject = currentProgressSubject)

    #time.sleep(1)

    #overallProgressSubject.reset()
    #currentProgressSubject.reset()
    #rep = FileRepository(url = u'file://%s' % tempDir)
    #for c in rep.content('', recursive=True):
    #   print c
    #print rep.exists('/MSVCR71.dll')
    #print rep.isdir('lib')
    #print rep.isfile('äää.txt')
    #print rep.listdir()
    #rep.copy(source = '/*', destination = tempDir2, overallProgressSubject = overallProgressSubject, currentProgressSubject = currentProgressSubject)

    #rep = FileRepository(url = u'file:///usr')
    #print rep.fileInfo('')
    #for f in rep.listdir('src'):
    #   print rep.fileInfo('src' + '/' + f)

    #ui.exit()

if __name__ == "__main__":
	logger.setConsoleLevel(LOG_DEBUG)
	logger.setConsoleColor(True)

    workingWithRepositories()
