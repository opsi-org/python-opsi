#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, codecs, time

from OPSI.Object import *
from OPSI.Backend.DHCPD import DHCPDBackend
from OPSI.Util.File import DHCPDConfFile
from OPSI.Logger import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG)
logger.setConsoleColor(True)


testData = '''
ddns-update-style none;
default-lease-time 68400;
# max-lease-time 68400;
max-lease-time 68400;
authoritative ;
log-facility local7;
use-host-decl-names on;
option domain-name "domain.local";
option domain-name-servers ns.domain.local;
option routers 192.168.99.254;

# Comment netbios name servers
option netbios-name-servers 192.168.99.2;

subnet 192.168.99.0 netmask 255.255.255.0 {
        group {
                #  Opsi hosts
                       next-server 192.168.99.2;
                filename "linux/pxelinux.0/xxx?{}";
                host opsi-test {
                                    hardware ethernet 9a:e5:3c:10:22:22;
                        fixed-address opsi-test.domain.local;
                }
	}
	host out-of-group {
		hardware ethernet 9a:e5:3c:10:22:22;
		fixed-address out-of-group.domain.local; 
	}
}
host out-of-subnet {
	hardware ethernet 1a:25:31:11:23:21;
	fixed-address out-of-subnet.domain.local; 
}
'''

testFile = u'/tmp/dhcpd.conf'

f = codecs.open(testFile, 'w', 'utf-8')
f.write(testData)
f.close()

dhcpdConf = DHCPDConfFile(testFile)
dhcpdConf.parse()

#print u"--------------------------------------------------------------------------------------------------"
#print dhcpdConf.getGlobalBlock().asText()
#print u"--------------------------------------------------------------------------------------------------"

dhcpdConf.addHost('TestclienT', '0001-21-21:00:00', '192.168.99.112', '192.168.99.112', None)
dhcpdConf.addHost('TestclienT2', '00:01:09:08:99:11', '192.168.99.113', '192.168.99.113', {"next-server": "192.168.99.2", "filename": "linux/pxelinux.0/xxx?{}"})

print dhcpdConf.getHost('TestclienT2')
print dhcpdConf.getHost('notthere')

dhcpdConf.generate()

sys.exit(0)

backend = DHCPDBackend(dhcpdConfigFile = testFile, reloadConfigCommand = u'/bin/echo "Reloading dhcpd.conf"')

backend.host_insertObject(
	OpsiClient(
		id              = 'client1.uib.local',
		hardwareAddress = '00:01:02:03:04:05',
		ipAddress       = '192.168.1.101',
	)
)
backend.host_insertObject(
	OpsiClient(
		id              = 'client2.uib.local',
		hardwareAddress = '00:01:02:03:11:22',
		ipAddress       = '192.168.1.102',
	)
)
backend.host_insertObject(
	OpsiClient(
		id              = 'client3.uib.local',
		hardwareAddress = '1101:02:03-83:22',
		ipAddress       = '192.168.1.103',
	)
)
time.sleep(3)
backend.host_insertObject(
	OpsiClient(
		id              = 'client4.uib.local',
		hardwareAddress = '00:99:88:77:77:11',
		ipAddress       = '192.168.1.104',
	)
)

for i in range(5):
	time.sleep(1)































