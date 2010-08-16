#
# spec file for package python-opsi
#
# Copyright (c) 2010 uib GmbH.
# This file and all modifications and additions to the pristine
# package are under the same license as the package itself.
#
Name:           python-opsi
BuildRequires:  python-devel gettext-devel python-setuptools
Requires:       python-twisted-web python-twisted-conch python-magic python-crypto python-ldap python-simplejson python-newt python-pam python-openssl python-mysql python-sqlalchemy iproute duplicity ldaptor lshw
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
%if %{?suse_version: %{suse_version} >= 1120} %{!?suse_version:1}
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
