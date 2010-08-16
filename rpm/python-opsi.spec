#
# spec file for package python-opsi
#
# Copyright (c) 2010 uib GmbH.
# This file and all modifications and additions to the pristine
# package are under the same license as the package itself.
#
Name:           python-opsi
BuildRequires:  python-devel gettext-devel python-support
Requires:       python-twisted-web python-twisted-conch python-magic python-crypto python-ldap python-simplejson python-newt python-pam python-openssl python-support python-mysql python-sqlalchemy iproute duplicity python-ldaptor lshw
Url:            http://www.opsi.org
License:        GPL v2 or later
Group:          Productivity/Networking/Opsi
AutoReqProv:    on
Version:        3.99.0.0
Release:        1
Summary:        opsi python library
%define tarname python-opsi
Source:         %{tarname}-%{version}.tar.bz2
#Source2:        setup.py
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
%{py_requires}
# python noarch modules are only working on openSUSE 11.2 or higher
# also disabled for non SUSE distros
if %{?suse_version: %{suse_version} >= 1120} %{!?suse_version:1}
BuildArch:      noarch
%endif

# ===[ description ]================================
%description
This package contains the opsi python library.

# ===[ debug_package ]==============================
%debug_package

# ===[ prep ]=======================================
%prep

# ===[ setup ]======================================
%setup -n %{tarname}-%{version}

# ===[ build ]======================================
%build
export CFLAGS="$RPM_OPT_FLAGS"
python setup.py build
#msgfmt -o gettext/opsi_system_de.mo gettext/opsi_system_de.po
#msgfmt -o gettext/opsi_ui_de.mo gettext/opsi_ui_de.po
#msgfmt -o gettext/opsi_system_fr.mo gettext/opsi_system_fr.po
#msgfmt -o gettext/opsi_ui_fr.mo gettext/opsi_ui_fr.po

# ===[ install ]====================================
%install
# install python files and record installed files in INSTALLED_FILES
python setup.py install --prefix=%{_prefix} --root=$RPM_BUILD_ROOT --record-rpm=INSTALLED_FILES
#mkdir -p $RPM_BUILD_ROOT/usr/share/locale/de/LC_MESSAGES
#mkdir -p $RPM_BUILD_ROOT/usr/share/locale/fr/LC_MESSAGES
#install -m 0644 gettext/opsi_system_de.mo $RPM_BUILD_ROOT/usr/share/locale/de/LC_MESSAGES/opsi_system.mo
#install -m 0644 gettext/opsi_ui_de.mo     $RPM_BUILD_ROOT/usr/share/locale/de/LC_MESSAGES/opsi_ui.mo
#install -m 0644 gettext/opsi_system_fr.mo $RPM_BUILD_ROOT/usr/share/locale/fr/LC_MESSAGES/opsi_system.mo
#install -m 0644 gettext/opsi_ui_fr.mo     $RPM_BUILD_ROOT/usr/share/locale/fr/LC_MESSAGES/opsi_ui.mo
#mkdir -p $RPM_BUILD_ROOT/etc/opsi/backendManager
#for i in `(cd files/backendManager.d; ls *.conf)`; do install -m 0644 files/backendManager.d/$i $RPM_BUILD_ROOT/etc/opsi/backendManager.d/; done
#cat files/backendManager.d/13_dhcpd.conf \
#    | sed 's#"dhcpdConfigFile":.*#"dhcpdConfigFile":         "/etc/dhcpd.conf",#' \
#    | sed 's#/etc/init.d/dhcp3-server#/etc/init.d/dhcpd#' \
#    > $RPM_BUILD_ROOT/etc/opsi/backendManager.d/13_dhcpd.conf
#mkdir -p $RPM_BUILD_ROOT/etc/opsi/hwaudit/locales
#install -m 0644 files/hwaudit/opsihwaudit.conf $RPM_BUILD_ROOT/etc/opsi/hwaudit/
#for i in files/hwaudit/locales/*; do install -m 0644 $i $RPM_BUILD_ROOT/etc/opsi/hwaudit/locales/; done
#mkdir -p $RPM_BUILD_ROOT/etc/openldap/schema
#install -m 0644 files/opsi.schema $RPM_BUILD_ROOT/etc/openldap/schema/
#install -m 0644 files/opsi-standalone.schema $RPM_BUILD_ROOT/etc/openldap/schema/
#mkdir -p $RPM_BUILD_ROOT/usr/share/opsi
#install -m 0755 files/share/init-opsi-mysql-db.py $RPM_BUILD_ROOT/usr/share/opsi/
#install -m 0755 files/share/register-depot.py $RPM_BUILD_ROOT/usr/share/opsi/
#install -m 0755 files/share/opsi-fire-event.py $RPM_BUILD_ROOT/usr/share/opsi/
#echo %{version} > $RPM_BUILD_ROOT/etc/opsi/version
#mkdir -p $RPM_BUILD_ROOT/var/lib/opsi

# ===[ clean ]======================================
%clean
rm -rf $RPM_BUILD_ROOT

# ===[ post ]=======================================
%post
if [ -z "`getent group pcpatch`" ]; then
	groupadd -g 992 pcpatch
fi

if [ -z "`getent passwd pcpatch`" ]; then
	useradd -u 992 -g 992 -d /var/lib/opsi -s /bin/bash pcpatch
fi

if [ -z "`getent group opsiadmin`" ]; then
	groupadd opsiadmin
fi

chown -R root:pcpatch /etc/opsi/backendManager
find /etc/opsi/backendManager -type d -exec chmod 770 {} \;
find /etc/opsi/backendManager -type f -exec chmod 660 {} \;
chown -R root:pcpatch /etc/opsi/backends
chmod 770 /etc/opsi/backends
chmod 660 /etc/opsi/backends/*.conf

test -e /etc/opsi/pckeys || touch /etc/opsi/pckeys
chown root:pcpatch /etc/opsi/pckeys
chmod 660 /etc/opsi/pckeys

test -e /etc/opsi/passwd || touch /etc/opsi/passwd
chown root:pcpatch /etc/opsi/passwd
chmod 660 /etc/opsi/passwd

[ -e "/etc/opsi/backendManager/acl.conf" ]      || ln -s /etc/opsi/backendManager/acl.conf.default      /etc/opsi/backendManager/acl.conf
[ -e "/etc/opsi/backendManager/dispatch.conf" ] || ln -s /etc/opsi/backendManager/dispatch.conf.default /etc/opsi/backendManager/dispatch.conf

## ===[ postun ]=====================================
#%postun
#if [ $1 -eq 0 ]; then
#	[ -z "`getent passwd pcpatch`" ] || userdel pcpatch
#	[ -z "`getent group pcpatch`" ] || groupdel pcpatch
#	[ -z "`getent group opsiadmin`" ] || groupdel opsiadmin
#	#[ -e /etc/opsi/pckeys ] && rm -f /etc/opsi/pckeys
#fi

# ===[ files ]======================================
%files -f INSTALLED_FILES
# default attributes
%defattr(-,root,root)

# documentation
#%doc LICENSE README RELNOTES doc

# configfiles
%config(noreplace) /etc/opsi/backends/dhcpd.conf
%config(noreplace) /etc/opsi/backends/file.conf
%config(noreplace) /etc/opsi/backends/jsonrpc.conf
%config(noreplace) /etc/opsi/backends/ldap.conf
%config(noreplace) /etc/opsi/backends/mysql.conf
%config(noreplace) /etc/opsi/backends/opsipxeconfd.conf
%config /etc/opsi/backendManager/acl.conf.default
%config /etc/opsi/backendManager/dispatch.conf.default
%config /etc/opsi/backendManager/extend.d/10_opsi.conf
%config /etc/opsi/backendManager/extend.d/20_legacy.conf
%config /etc/opsi/backendManager/extend.d/configed/30_configed.conf
%config /etc/opsi/hwaudit/opsihwaudit.conf
%config /etc/opsi/hwaudit/locales/de_DE
%config /etc/opsi/hwaudit/locales/en_US
%config /etc/openldap/schema/opsi.schema
%config /etc/openldap/schema/opsi-standalone.schema

# other files
#/usr/share/locale/de/LC_MESSAGES/opsi_system.mo
#/usr/share/locale/de/LC_MESSAGES/opsi_ui.mo
#/usr/share/locale/fr/LC_MESSAGES/opsi_system.mo
#/usr/share/locale/fr/LC_MESSAGES/opsi_ui.mo
#/usr/share/opsi/init-opsi-mysql-db.py
#/usr/share/opsi/register-depot.py
#/usr/share/opsi/opsi-fire-event.py

# directories
#%dir /var/lib/opsi
#%dir /usr/share/opsi
#%dir /usr/share/python-support/python-opsi/OPSI
#%dir /usr/share/python-support/python-opsi/OPSI/Backend
#%dir /usr/share/python-support/python-opsi/OPSI/System
#%dir /usr/share/python-support/python-opsi/OPSI/Util/File/Archive
#%dir /usr/share/python-support/python-opsi/OPSI/Util/File/Opsi
#%dir /etc/opsi/backendManager/extend.d
#%dir /etc/opsi/backendManager/extend.d/configed
#%dir /etc/opsi/backends
#%dir /etc/opsi/hwaudit/locales
#%dir /etc/ldap/schema

# ===[ changelog ]==================================
%changelog
python-opsi (3.99.0.0-1) testing; urgency=low

  * local package
  * opsi 4.0

 -- Jan Schneider <j.schneider@uib.de>  Tue, 18 May 2010 15:38:15 +0200

python-opsi (3.4.99.1-1) testing; urgency=low

  * testing release

 -- Jan Schneider <j.schneider@uib.de>  Tue, 06 Apr 2010 12:19:37 +0200

python-opsi (3.4.99.0-1) experimental; urgency=low

  * starting 3.5 development

 -- Jan Schneider <j.schneider@uib.de>  Fri, 06 Nov 2009 15:33:48 +0100

python-opsi (3.4.0.4-1) stable; urgency=low

  * implemented setIpAddress() in DHCPD, File31

 -- Jan Schneider <j.schneider@uib.de>  Wed, 04 Nov 2009 12:41:51 +0100

python-opsi (3.4.0.3-1) stable; urgency=low

  * Posix 1.3.1
     - fixed getNetworkDeviceConfig

 -- Jan Schneider <j.schneider@uib.de>  Wed, 28 Oct 2009 17:51:07 +0100

python-opsi (3.4.0.2-1) stable; urgency=low

  * Posix 1.3
     - new method getEthernetDevices
     - new method getNetworkDeviceConfig
     - rewritten method getDHCPResult

 -- Jan Schneider <j.schneider@uib.de>  Fri, 11 Sep 2009 19:03:50 +0200

python-opsi (3.4.0.1-1) stable; urgency=low

  * Changed lshw class for DISK_PARITION in hwaudit.conf
  * Posix 1.2.6

 -- Jan Schneider <j.schneider@uib.de>  Mon, 07 Sep 2009 10:12:19 +0200

python-opsi (3.4.0.0-s1) stable; urgency=low

  * New version number

 -- Jan Schneider <j.schneider@uib.de>  Thu, 27 Aug 2009 14:23:40 +0200

python-opsi (3.4.0.0-rc6) unstable; urgency=low

  * MySQL 0.3.3.4: fixed encoding error
  * Fixed db conversion in init-opsi-mysql-db.py
  
 -- Jan Schneider <j.schneider@uib.de>  Wed, 26 Aug 2009 10:19:37 +0200

python-opsi (3.4.0.0-rc5) unstable; urgency=low

  * Posix.py 1.2.4

 -- Jan Schneider <j.schneider@uib.de>  Wed, 29 Jul 2009 16:39:46 +0200

python-opsi (3.4.0.0-rc4) unstable; urgency=low

  * LDAP.py 1.0.9

 -- Jan Schneider <j.schneider@uib.de>  Tue, 28 Jul 2009 11:07:28 +0200

python-opsi (3.4.0.0-rc3) unstable; urgency=low

  * Bugfix in File31
  * LDAP 1.0.7

 -- Jan Schneider <j.schneider@uib.de>  Fri, 26 Jun 2009 16:00:29 +0200

python-opsi (3.4.0.0-rc2) unstable; urgency=low

  * Tools.py 1.0.1: replaced popen by subprocess
  * BackendManager 1.0.6: installPackage() encode defaultValue to utf-8
  * Bugfix in LDAP.py and File31

 -- Jan Schneider <j.schneider@uib.de>  Tue, 16 Jun 2009 12:40:10 +0200

python-opsi (3.4.0.0-rc1) unstable; urgency=low

  * Introducing license management
  * JSONRPC backend: non-blocking connect
  * Introducing modules file /etc/opsi/modules
  * Added /usr/share/opsi/opsi-fire-event.py
  * opsi-admin 1.0

 -- Jan Schneider <j.schneider@uib.de>  Tue, 02 Jun 2009 12:49:22 +0200

python-opsi (3.3.1.5-1) stable; urgency=low

  * Fixed getSelections on lenny in module UI (snack)
  
 -- Jan Schneider <j.schneider@uib.de>  Mon, 06 Apr 2009 15:30:13 +0200

python-opsi (3.3.1.4-1) stable; urgency=low

  * Tools.py 0.9.9.6
      - fixed text mode driver integration
  * BackendManager.py 1.0
      - introducing method getOpsiInformation_hash

 -- Jan Schneider <j.schneider@uib.de>  Wed, 04 Mar 2009 12:32:32 +0100

python-opsi (3.3.1.3-1) stable; urgency=low

  * Product.py 1.1.2
  * BackendManager.py 0.9.9.5
  * LDAP.py 0.9.1.12
  * Tools.py 0.9.9.4
  * Util.py 0.2.1
  
 -- Jan Schneider <j.schneider@uib.de>  Tue, 24 Feb 2009 14:02:42 +0100

python-opsi (3.3.1.2-1) stable; urgency=low

  * Posix.py 1.1.12
     - createPartition: lowest possible start sector now 0
  * Util.py 0.2
  * BackendManager.py 0.9.9.3
     - possibility to pass forced backend instance to constructor 
  * Cache.py 0.1 (starting a new data backend)
  * Backend.py 0.9.9
  * Product.py 1.1.1
     - introducing file-info-file
  * Tools.py 0.9.9.2
     - includeDir, includeFile parms for findFile

 -- Jan Schneider <j.schneider@uib.de>  Tue, 17 Feb 2009 10:28:12 +0100

python-opsi (3.3.1.1-1) stable; urgency=low

  * Product.py 1.0.1
  * Util.py 0.2
  * BackendManager.py 0.9.9.2

 -- Jan Schneider <schneider@pcbon14.uib.local>  Wed, 11 Feb 2009 16:18:17 +0100

python-opsi (3.3.1.0-5) stable; urgency=low

  * File31.py 0.2.7.22
  * Windows.py 0.1.5 

 -- Jan Schneider <j.schneider@uib.de>  Wed, 04 Feb 2009 14:51:24 +0100

python-opsi (3.3.1.0-4) stable; urgency=low

  * Bugfixes in:
      - Windows.py
      - LDAP.py
      - BackendManager.py

 -- Jan Schneider <j.schneider@uib.de>  Wed, 04 Feb 2009 14:50:08 +0100

python-opsi (3.3.1.0-3) stable; urgency=low

  * BackendManager.py 0.9.9
      new methods adjustProductActionRequests, adjustProductStates
  * File.py 0.9.7.9
      pathnams.ini fixes
  * new version of config file 50_interface.conf

 -- Jan Schneider <j.schneider@uib.de>  Mon, 26 Jan 2009 11:54:04 +0100

python-opsi (3.3.1.0-2) stable; urgency=low

  * Fix

 -- Jan Schneider <j.schneider@uib.de>  Wed, 14 Jan 2009 17:57:18 +0100

python-opsi (3.3.1.0-1) stable; urgency=low

  * changed signature of methods getClientIds_list, getClients_listOfHashes
      depotid=None => depotIds=[]
  * added creation timestamp to host hash

 -- Jan Schneider <j.schneider@uib.de>  Tue, 13 Jan 2009 12:42:41 +0100

python-opsi (3.3.0.32-1) stable; urgency=low

  * Posix 1.1.11
      hardwareInventory(): added alsa hdaudio information
  * opsihwaudit.conf: added class HDAUDIO_DEVICE 

 -- Jan Schneider <j.schneider@uib.de>  Tue, 06 Jan 2009 11:49:47 +0100

python-opsi (3.3.0.31-1) stable; urgency=low

  * MySQL.py 0.2.4.4

 -- Jan Schneider <j.schneider@uib.de>  Wed, 17 Dec 2008 16:23:51 +0100

python-opsi (3.3.0.30-1) stable; urgency=low

  * Fixed bug in File31.py method getSoftwareInformation_hash
  * File.py 0.9.7.5

 -- Jan Schneider <j.schneider@uib.de>  Tue, 16 Dec 2008 17:44:35 +0100

python-opsi (3.3.0.29-1) stable; urgency=low

  * Fixed bug in Product.py (Product instance has no attribute 'windowsSoftwareId')

 -- Jan Schneider <j.schneider@uib.de>  Fri, 21 Nov 2008 23:06:59 +0100

python-opsi (3.3.0.28-1) stable; urgency=low

  * Added maxSize param to readLog()

 -- Jan Schneider <j.schneider@uib.de>  Wed, 19 Nov 2008 15:45:47 +0100

python-opsi (3.3.0.27-1) stable; urgency=low

  * new versions of opsi-standalone.schema, opsi.schema
  * new version of 50_interface.conf
  * Windows.py 0.1.1
  * Util.py 0.1.2.1
  * Product.py 0.9.9
  * Backend/LDAP.py 0.9.1.6
  * Backend/BackendManager.py 0.9.7.2
  * Backend/File31.py 0.2.7.14
  * Backend/File.py 0.9.7.4

 -- Jan Schneider <j.schneider@uib.de>  Wed, 19 Nov 2008 13:50:22 +0100

python-opsi (3.3.0.26-1) stable; urgency=low

  * Product.py 0.9.8.9
  * Backend/MySQL.py 0.2.4.3
  * System/Posix.py 1.1.9
  * new version of opsihwaudit.conf
  * register-depot.py 1.1.1

 -- Jan Schneider <j.schneider@uib.de>  Tue, 28 Oct 2008 14:43:01 +0100

python-opsi (3.3.0.25-1) stable; urgency=low

  * Added Twisted.Web2.dav
  * Posix.py 1.1.8
  * JSONRPC.py 0.9.5.8

 -- Jan Schneider <j.schneider@uib.de>  Wed, 08 Oct 2008 15:53:05 +0200

python-opsi (3.3.0.24-1) stable; urgency=low

  * Using librsync from duplicity

 -- Jan Schneider <j.schneider@uib.de>  Mon, 25 Aug 2008 13:59:57 +0200

python-opsi (3.3.0.23-1) stable; urgency=low

  * Util.py 0.1
  * File31.py 0.2.7.13
  * LDAP.py 0.9.1.4
  * System.py removed
  * System/Posix.py 1.1.5
  * System/Windows.py 0.0.1

 -- Jan Schneider <j.schneider@uib.de>  Mon, 11 Aug 2008 11:50:51 +0200

python-opsi (3.3.0.22-1) stable; urgency=low

  * librsync included

 -- Jan Schneider <j.schneider@uib.de>  Wed, 09 Jul 2008 17:12:04 +0200

python-opsi (3.3.0.21-1) stable; urgency=low

  * File31.py 0.2.7.11
     fixed bug in getDefaultNetbootProductId

 -- Jan Schneider <j.schneider@uib.de>  Wed, 09 Jul 2008 17:07:02 +0200

python-opsi (3.3.0.20-1) stable; urgency=low

  * File31.py 0.2.7.10
  * LDAP.py 0.9.1.2

 -- Jan Schneider <j.schneider@uib.de>  Mon, 07 Jul 2008 14:11:40 +0200

python-opsi (3.3.0.19-1) stable; urgency=low

  * LDAP.py 0.9.1.1
  * Univention.py 0.5
  * File31.py 0.2.7.9

 -- Jan Schneider <j.schneider@uib.de>  Thu, 03 Jul 2008 13:46:13 +0200

python-opsi (3.3.0.18-1) stable; urgency=low

  * File.py 0.9.7.3
  * LDAP.py 0.9.0.3
  * Product.py 0.9.8.8

 -- Jan Schneider <j.schneider@uib.de>  Thu, 26 Jun 2008 09:36:36 +0200

python-opsi (3.3.0.17-1) stable; urgency=low

  * LDAP Backend rewritten

 -- Jan Schneider <j.schneider@uib.de>  Mon, 23 Jun 2008 17:16:03 +0200

python-opsi (3.3.0.16-1) stable; urgency=low

  * WakeOnLAN 0.9.2
      Magic Packet changed

 -- Jan Schneider <j.schneider@uib.de>  Tue, 17 Jun 2008 14:08:30 +0200

python-opsi (3.3.0.15-1) stable; urgency=low

  * System.py 1.1.0
      LD_PRELOAD now set temporary while running subprocesses
      new methods getBlockDeviceBusType(), Harddisk.getBusType()

 -- Jan Schneider <j.schneider@uib.de>  Thu, 12 Jun 2008 17:35:19 +0200

python-opsi (3.3.0.14-1) stable; urgency=low

  * System.py 1.0.1
  * interface method getDepot_hash returns depot's ip 

 -- Jan Schneider <j.schneider@uib.de>  Thu, 05 Jun 2008 16:16:46 +0200

python-opsi (3.3.0.13-1) stable; urgency=low

  * System.py 1.0.0.8

 -- Jan Schneider <j.schneider@uib.de>  Thu, 29 May 2008 14:40:20 +0200

python-opsi (3.3.0.12-1) stable; urgency=low

  * System.py 1.0.0.7
  * File31.py 0.2.7.7 

 -- Jan Schneider <j.schneider@uib.de>  Thu, 29 May 2008 13:40:01 +0200

python-opsi (3.3.0.11-1) stable; urgency=low

  * changed logging

 -- Jan Schneider <j.schneider@uib.de>  Wed, 28 May 2008 14:33:22 +0200

python-opsi (3.3.0.10-1) stable; urgency=low

  * added BackendManager method getDiskSpaceUsage

 -- Jan Schneider <j.schneider@uib.de>  Tue, 20 May 2008 09:48:22 +0200

python-opsi (3.3.0.9-1) stable; urgency=low

  * parameter tempDir added to method installPackage in BackendManager

 -- Jan Schneider <j.schneider@uib.de>  Thu, 15 May 2008 14:11:03 +0200

python-opsi (3.3.0.8-1) stable; urgency=low

  * added interface method setMacAddress()
  * repository bandwidth added

 -- Jan Schneider <j.schneider@uib.de>  Tue, 13 May 2008 13:39:56 +0200

python-opsi (3.3.0.7-1) stable; urgency=low

  * setMacAddresses() implemented in DHCPD-Backend
  * added methods readLog(), writeLog()
  * Fixed bug in System.py

 -- Jan Schneider <j.schneider@uib.de>  Mon,  5 May 2008 13:26:45 +0200

python-opsi (3.3.0.6-1) stable; urgency=low

  * Fixed several bugs

 -- Jan Schneider <j.schneider@uib.de>  Fri,  2 May 2008 14:05:46 +0200

python-opsi (3.3.0.5-1) stable; urgency=low

  * Fixed bug in Logger linkLogFile()

 -- Jan Schneider <j.schneider@uib.de>  Thu, 24 Apr 2008 17:08:12 +0200

python-opsi (3.3.0.4-1) stable; urgency=low

  * MySQL lacy connect

 -- Jan Schneider <j.schneider@uib.de>  Wed, 23 Apr 2008 16:25:33 +0200

python-opsi (3.3.0.3-1) stable; urgency=low

  * Fixed unpack of SERVER_DATA

 -- Jan Schneider <j.schneider@uib.de>  Tue, 22 Apr 2008 18:00:03 +0200

python-opsi (3.3.0.2-1) stable; urgency=low

  * MySQL Backend 0.2.3

 -- Jan Schneider <j.schneider@uib.de>  Mon, 21 Apr 2008 16:11:48 +0200

python-opsi (3.3.0.1-1) stable; urgency=high

  * Fixed postinst bug in BackendManager
  * Added method getMD5Sum()

 -- Jan Schneider <j.schneider@uib.de>  Thu, 17 Apr 2008 16:16:55 +0200

python-opsi (3.3.0.0-1) stable; urgency=low

  * Multidepot support
  * Major changes in product/package handling
  * OpsiPXEConfd backend can forward requests to other depots
  * MySQL Backend for hardware audit and software audit
  * Removed Reinstmgr Backend
  * Logger can handle special configuration for class instances

 -- Jan Schneider <j.schneider@uib.de>  Tue, 15 Apr 2008 13:42:27 +0200

python-opsi (3.2.0.16-1) stable; urgency=low

  * JSONRPC - fixed bug in retry request

 -- Jan Schneider <j.schneider@uib.de>  Mon, 31 Mar 2008 10:44:44 +0200

python-opsi (3.2.0.15-1) stable; urgency=low

  * Added backend methods userIsHost() and userIsAdmin()
  * Univention.py fixed some warnings

 -- Jan Schneider <j.schneider@uib.de>  Mon, 10 Mar 2008 13:03:15 +0100

python-opsi (3.2.0.14-1) stable; urgency=low

  * System.py 0.9.9.9
     - hardwareInventory() replacing invalid tokens from lshw output

 -- Jan Schneider <j.schneider@uib.de>  Wed, 27 Feb 2008 12:43:13 +0100

python-opsi (3.2.0.13-1) stable; urgency=low

  * Product.py 0.9.8.0
     - fixes
     - faster unpacking
     - custom only packages
  * System.py: fixed bug in shred()

 -- Jan Schneider <j.schneider@uib.de>  Mon, 18 Feb 2008 11:17:57 +0100

python-opsi (3.2.0.12-1) stable; urgency=low

  * File31.py 0.2.6.1: fixed bug in getProductProperties_hash

 -- Jan Schneider <j.schneider@uib.de>  Sun, 10 Feb 2008 21:04:21 +0100

python-opsi (3.2.0.11-1) stable; urgency=low

  * Product.py 0.9.7.0: productProperty values with space characters
  * Added interface method setProductProperty

 -- Jan Schneider <j.schneider@uib.de>  Fri,  8 Feb 2008 09:12:35 +0100

python-opsi (3.2.0.10-1) stable; urgency=low

  * System.py 0.9.9.7

 -- Jan Schneider <j.schneider@uib.de>  Wed,  6 Feb 2008 12:35:11 +0100

python-opsi (3.2.0.9-1) stable; urgency=low

  * System.py 0.9.9.6

 -- Jan Schneider <j.schneider@uib.de>  Wed,  6 Feb 2008 10:31:49 +0100

python-opsi (3.2.0.8-1) stable; urgency=low

  * System.py 0.9.9.5

 -- Jan Schneider <j.schneider@uib.de>  Fri, 25 Jan 2008 13:52:38 +0100

python-opsi (3.2.0.7-1) stable; urgency=low

  * Fixed bug when passing unicode strings in Logger.log

 -- Jan Schneider <j.schneider@uib.de>  Mon, 21 Jan 2008 14:53:00 +0100

python-opsi (3.2.0.6-1) stable; urgency=low

  * Fixed bug in backend LDAP method getProductIds_list

 -- Jan Schneider <j.schneider@uib.de>  Wed, 16 Jan 2008 17:20:09 +0100

python-opsi (3.2.0.5-1) stable; urgency=low

  * readPartitionTable adapted for cciss

 -- Jan Schneider <j.schneider@uib.de>  Tue, 15 Jan 2008 11:20:26 +0100

python-opsi (3.2.0.4-1) stable; urgency=low

  * getPcpatchRSAPrivateKey updated

 -- Jan Schneider <j.schneider@uib.de>  Tue, 18 Dec 2007 11:29:01 +0100

python-opsi (3.2.0.3-1) stable; urgency=low

  * added default parameter for getProductIds_list in LDAP.py
  
 -- Rupert Roeder <r.roeder@uib.de>  Mon,  3 Dec 2007 15:29:39 +0100
   
python-opsi (3.2.0.2-1) stable; urgency=low
   
  * handling of percent signs in file 3.1

 -- Jan Schneider <j.schneider@uib.de>  Thu,  8 Nov 2007 15:29:39 +0100
      
python-opsi (3.2.0.1-1) stable; urgency=low
      
  * Extended hwaudit
	
 -- Jan Schneider <j.schneider@uib.de>  Thu,  8 Nov 2007 15:29:39 +0100
	 
python-opsi (3.2.0-1) stable; urgency=low
	 
  * Changes in System.hardwareInventory()
  * Bugfix in System.execute()
  * New function Tools.objectToBeautifiedText()

 -- Jan Schneider <j.schneider@uib.de>  Fri,  2 Nov 2007 11:04:35 +0100

python-opsi (3.1.2.1-1) stable; urgency=low

  * File31: Implemented getSoftwareInformation_hash(), setSoftwareInformation(), deleteSoftwareInformation()

 -- Jan Schneider <j.schneider@uib.de>  Tue, 23 Oct 2007 12:56:04 +0200

python-opsi (3.1.2.0-1) stable; urgency=low

  * Added methods comment(), exit() to Logger
  * Fixed bug in Logger (exception if log-file not writable)

 -- Jan Schneider <j.schneider@uib.de>  Mon, 22 Oct 2007 16:09:26 +0200

python-opsi (3.1.1.0-1) stable; urgency=low

  * Added opsi hwaudit
  * SSH RSA authentication for pcpatch
  * Fixed bug on unpacking incremental packages
  * ProductPackageSource.pack() excludes .svn dirs by default

 -- Jan Schneider <j.schneider@uib.de>  Fri, 19 Oct 2007 13:35:55 +0200

python-opsi (3.1.0.1-1) stable; urgency=low

  * fixed bug in Tools.compareVersions()
  * changed permissions for method getClientIds_list in 50_interface.conf
  * fixed bugs in DHCPD.py: inheritance when creating clients, single ; as command
  * added methods getPcpatchRSAPrivateKey(), getHostRSAPublicKey()

 -- Jan Schneider <j.schneider@uib.de>  Tue, 11 Sep 2007 10:12:32 +0200

python-opsi (3.1.0-2) stable; urgency=low

  * added method getProducts_listOfHashes to 50_interface.conf

 -- Jan Schneider <j.schneider@uib.de>  Thu, 30 Aug 2007 15:37:46 +0200

python-opsi (3.1.0-1) stable; urgency=low

  * Opsi 3.1 stable release

 -- Jan Schneider <j.schneider@uib.de>  Tue, 28 Aug 2007 10:02:48 +0200

python-opsi (3.1rc1-8) unstable; urgency=low

  * 50_interface: Corrected hwinvent-backend
  * File-Backend: fixed createProduct()

 -- Jan Schneider <j.schneider@uib.de>  Thu,  2 Aug 2007 13:51:33 +0200

python-opsi (3.1rc1-7) unstable; urgency=low

  * File: keep client property values when reinstalling product with opsiinst 

 -- Jan Schneider <j.schneider@uib.de>  Wed, 25 Jul 2007 13:31:37 +0200

python-opsi (3.1rc1-6) unstable; urgency=low

  * reverted hardware information handling
  * Fixed version information (all backends)

 -- Jan Schneider <j.schneider@uib.de>  Thu, 19 Jul 2007 11:50:27 +0200

python-opsi (3.1rc1-5) unstable; urgency=low

  * opsiaudit adjustments 
  * Bugfixes

 -- Jan Schneider <j.schneider@uib.de>  Tue, 17 Jul 2007 13:19:45 +0200

python-opsi (3.1rc1-4) unstable; urgency=low

  * Fixed: DHCPD-Backend-configuration fixed-address type setting not working 
  * Fixed: makeproductfile does not create Customized products
  * Fixed: LDAP-Backend wrong version information 

 -- Jan Schneider <j.schneider@uib.de>  Thu, 12 Jul 2007 10:34:05 +0200

python-opsi (3.1rc1-3) unstable; urgency=low

  * added support for pxeConfigTemplates defined in netboot products

 -- Jan Schneider <j.schneider@uib.de>  Thu,  5 Jul 2007 12:16:37 +0200

python-opsi (3.1rc1-2) unstable; urgency=low

  * File31 getDepotId() recursion fix

 -- Jan Schneider <j.schneider@uib.de>  Wed,  4 Jul 2007 09:51:24 +0200

python-opsi (3.1rc1-1) unstable; urgency=low

  * opsi 3.1 release candidate 1
  * opsipxeconfd becomes default boot manager
  * getClientIds_list, getClients_listOfHashes: filter by productVersion + packageVersion
  * new method setProductState
  * FileBackend becomes LegacyFileBackend, new FileBackend
  
 -- Jan Schneider <j.schneider@uib.de>  Thu, 26 May 2007 15:17:00 +0200

python-opsi (0.9.6.0-1) unstable; urgency=low

  * getDomain() returns default domain if called without params 
  * setPcpatchPassword / getPcpatchPassword for server
  * Bugfixes
  
 -- Jan Schneider <j.schneider@uib.de>  Fri, 11 May 2007 17:21:46 +0200

python-opsi (0.9.5.1-1) unstable; urgency=low

  * Added support for package-dependencies and incremental packages
 
 -- Jan Schneider <j.schneider@uib.de>  Mon, 07 May 2007 12:18:34 +0200

python-opsi (0.9.5.0-1) unstable; urgency=low

  * Added product state "installing"
  * Added backend OpsiPXEConfd
 
 -- Jan Schneider <j.schneider@uib.de>  Thu, 26 Apr 2007 11:24:56 +0200

python-opsi (0.9.4.4-1) unstable; urgency=low

  * support for product archives without compression
 
 -- Jan Schneider <j.schneider@uib.de>  Mon, 23 Apr 2007 09:54:28 +0200

python-opsi (0.9.4.3-1) unstable; urgency=low

  * BackendManager uses /etc/opsi/backendManager.d for config by default
 
 -- Jan Schneider <j.schneider@uib.de>  Thu, 19 Apr 2007 14:13:31 +0200

python-opsi (0.9.4.2-1) unstable; urgency=high

  * Corrected important errors when creating and extracting tar archives
 
 -- Jan Schneider <j.schneider@uib.de>  Thu, 19 Apr 2007 14:13:31 +0200

python-opsi (0.9.4.1-1) unstable; urgency=low

  * added backend method setPcpatchPassword
 
 -- Jan Schneider <j.schneider@uib.de>  Wed, 18 Apr 2007 16:41:21 +0200

python-opsi (0.9.4.0-1) unstable; urgency=low

  * fixed setGeneralConfig in LDAP backend
 
 -- Jan Schneider <j.schneider@uib.de>  Fri, 13 Apr 2007 16:07:51 +0200

python-opsi (0.9.3.9-1) unstable; urgency=low

  * fixes
 
 -- Jan Schneider <j.schneider@uib.de>  Thu, 12 Apr 2007 14:39:22 +0200

python-opsi (0.9.3.8-1) unstable; urgency=low

  * Product.py pack() fix
 
 -- Jan Schneider <j.schneider@uib.de>  Tue, 05 Apr 2007 15:06:12 +0200

python-opsi (0.9.3.7-1) unstable; urgency=low

  * several fixes, improvements
  * tar as default format for opsi packages 
 
 -- Jan Schneider <j.schneider@uib.de>  Tue, 05 Apr 2007 13:02:23 +0200

python-opsi (0.9.3.6-1) unstable; urgency=low

  * several fixes, improvements
 
 -- Jan Schneider <j.schneider@uib.de>  Thu, 22 Mar 2007 12:16:01 +0200

python-opsi (0.9.3.5-1) unstable; urgency=low

  * Tools.py
      Fixed createArchive() 
 
 -- Jan Schneider <j.schneider@uib.de>  Fri, 13 Mar 2007 17:16:26 +0200

python-opsi (0.9.3.4-1) unstable; urgency=low

  * Latest version of File.py
      Fixed ini writing (uninstall script) on createProduct() 
  * Latest version of LDAP.py
  * Latest version of Univention.py
 
 -- Jan Schneider <j.schneider@uib.de>  Fri, 09 Mar 2007 16:15:02 +0200

python-opsi (0.9.3.3-1) unstable; urgency=low

  * Latest version of Product.py
  
 -- Jan Schneider <j.schneider@uib.de>  Thu, 08 Mar 2007 11:24:01 +0200

python-opsi (0.9.3.2-2) unstable; urgency=low

  * Added LDAP schema /etc/ldap/schema/opsi.schema
  
 -- Jan Schneider <j.schneider@uib.de>  Thu, 15 Feb 2007 14:25:44 +0200

python-opsi (0.9.3.2-1) unstable; urgency=high

  * Product.py (0.9.3.2)
       Bugfix 
  
 -- Jan Schneider <j.schneider@uib.de>  Thu, 15 Feb 2007 14:18:01 +0200

python-opsi (0.9.3.1-1) unstable; urgency=low

  * System.py (0.9.3.1)
       Using -t cifs instead of -t smbfs to mount smb shares 
  
 -- Jan Schneider <j.schneider@uib.de>  Thu, 15 Feb 2007 13:20:03 +0200

python-opsi (0.9.3-1) unstable; urgency=low

  * File.py (0.9.2)
       Improved logging of name resolution errors 
  
 -- Jan Schneider <j.schneider@uib.de>  Wed, 14 Feb 2007 14:51:13 +0200

python-opsi (0.9.2-1) unstable; urgency=low

  * backendManager.conf
       permissions rw-rw---- pcpatch:opsiadmin
  * /usr/bin/opsi-admin
       permissions rwxrwx--- pcpatch:opsiadmin
  * Backend.py (0.9.2)
       added abstract DataBackend.createOpsiBase()
  * File.py (0.9.2)
       createClient() file mode for <pcname>.ini now 660 
  * Product.py (0.9.2)
       added method ProductPackageFile.unpackSource,
       which creates package source from package file
  * Reinstmgr (0.9.2)
       no Exception raised by getBootimages_list if no bootimages present
  
 -- Jan Schneider <j.schneider@uib.de>  Wed, 14 Feb 2007 13:16:10 +0200

python-opsi (0.91-1) unstable; urgency=low

  * backendManager.conf: createClient() creates opsi-hostkey only if missing.
  * some fixes in File backend
  
 -- Jan Schneider <j.schneider@uib.de>  Tue, 13 Feb 2007 8:56:44 +0200


python-opsi (0.9-1) unstable; urgency=low

  * Initial Release.

 -- Jan Schneider <j.schneider@uib.de>  Thu, 18 Jan 2007 11:46:44 +0200
