#!/usr/bin/env python
#-*- coding: utf-8 -*-

from OPSI.Object import OpsiClient


class ClientsMixin(object):
    def setUpClients(self):
        # TODO: turn this into tests?
        self.client1 = OpsiClient(
            id='client1.uib.local',
            description='Test client 1',
            notes='Notes ...',
            hardwareAddress='00:01:02:03:04:05',
            ipAddress='192.168.1.100',
            lastSeen='2009-01-01 00:00:00',
            opsiHostKey='45656789789012789012345612340123',
            inventoryNumber=None
        )

        # TODO: turn this into tests?
        self.client2 = OpsiClient(
            id='client2.uib.local',
            description='Test client 2',
            notes=';;;;;;;;;;;;;;',
            hardwareAddress='00-ff0aa3:0b-B5',
            opsiHostKey='59051234345678890121678901223467',
            inventoryNumber='00000000003',
            oneTimePassword='logmein'
        )

        # TODO: turn this into tests?
        self.client3 = OpsiClient(
            id='client3.uib.local',
            description='Test client 3',
            notes='#############',
            inventoryNumber='XYZABC_1200292'
        )

        self.client4 = OpsiClient(
            id='client4.uib.local',
            description='Test client 4',
        )

        self.client5 = OpsiClient(
            id='client5.uib.local',
            description='Test client 5',
            oneTimePassword='abe8327kjdsfda'
        )

        self.client6 = OpsiClient(
            id='client6.uib.local',
            description='Test client 6',
        )

        self.client7 = OpsiClient(
            id='client7.uib.local',
            description='Test client 7',
        )

        self.clients = [self.client1, self.client2, self.client3,
                        self.client4, self.client5, self.client6, self.client7]

        if not hasattr(self, 'hosts'):
            self.hosts = []
        self.hosts.extend(self.clients)

    def createHostsOnBackend(self):
        for host in self.hosts:
            host.setDefaults()
        self.backend.host_createObjects(self.hosts)