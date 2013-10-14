#!/usr/bin/env python
#-*- coding: utf-8 -*-

import socket
from OPSI.Object import OpsiConfigserver, OpsiDepotserver

class HostsMixin(object):
    def setUpHosts(self):
        serverId = socket.getfqdn()
        if (serverId.count('.') < 2):
            raise Exception(u"Failed to get fqdn: %s" % serverId)

        self.configserver1 = OpsiConfigserver(
            id=serverId,
            opsiHostKey='71234545689056789012123678901234',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl=u'smb://%s/opt_pcbin/install' % serverId.split(
                '.')[0],
            repositoryLocalUrl='file:///var/lib/opsi/repository',
            repositoryRemoteUrl=u'webdavs://%s:4447/repository' % serverId,
            description='The configserver',
            notes='Config 1',
            hardwareAddress=None,
            ipAddress=None,
            inventoryNumber='00000000001',
            networkAddress='192.168.1.0/24',
            maxBandwidth=10000
        )
        self.configservers = [self.configserver1]

        if not hasattr(self, 'hosts'):
            self.hosts = []
        self.hosts.extend(self.configservers)

        self.depotserver1 = OpsiDepotserver(
            id='depotserver1.uib.local',
            opsiHostKey='19012334567845645678901232789012',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl='smb://depotserver1.uib.local/opt_pcbin/install',
            repositoryLocalUrl='file:///var/lib/opsi/repository',
            repositoryRemoteUrl='webdavs://depotserver1.uib.local:4447/repository',
            description='A depot',
            notes='D€pot 1',
            hardwareAddress=None,
            ipAddress=None,
            inventoryNumber='00000000002',
            networkAddress='192.168.2.0/24',
            maxBandwidth=10000
        )

        self.depotserver2 = OpsiDepotserver(
            id='depotserver2.uib.local',
            opsiHostKey='93aa22f38a678c64ef678a012d2e82f2',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl='smb://depotserver2.uib.local/opt_pcbin',
            repositoryLocalUrl='file:///var/lib/opsi/repository',
            repositoryRemoteUrl='webdavs://depotserver2.uib.local:4447/repository',
            description='Second depot',
            notes='no notes here',
            hardwareAddress='00:01:09:07:11:aa',
            ipAddress='192.168.10.1',
            inventoryNumber='',
            networkAddress='192.168.10.0/24',
            maxBandwidth=240000
        )

        self.depotservers = [self.depotserver1, self.depotserver2]
        self.hosts.extend(self.depotservers)

    def createHostsOnBackend(self):
        for host in self.hosts:
            host.setDefaults()
        self.backend.host_createObjects(self.hosts)