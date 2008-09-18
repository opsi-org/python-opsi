#
# spec file for package python-opsi
#
# Copyright (c) 2008 uib GmbH.
# This file and all modifications and additions to the pristine
# package are under the same license as the package itself.
#

Name:           python-opsi
BuildRequires:  python-devel
Requires:       python-json
Url:            http://www.opsi.org
License:        GPL v2 or later
Group:          Development/Libraries/Python
AutoReqProv:    on
Version:        3.0.0.25
Release:        1
Summary:        opsi python library
%define tarname python-opsi
Source:         %{tarname}-%{version}.tar.bz2
#Source2:        setup.py
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
%{py_requires}

%description
This package contains the OPSI python library.

%debug_package

%prep

%setup -n %{tarname}-%{version}

%build
export CFLAGS="$RPM_OPT_FLAGS" 
python setup.py build

%install
# install python files and record installed files in INSTALLED_FILES
python setup.py install --prefix=%{_prefix} --root=$RPM_BUILD_ROOT --record-rpm=INSTALLED_FILES
mkdir -p $RPM_BUILD_ROOT/usr/share/locale/de/LC_MESSAGES
install -m 0644 gettext/opsi_system.mo $RPM_BUILD_ROOT/usr/share/locale/de/LC_MESSAGES/
install -m 0644 gettext/opsi_ui.mo     $RPM_BUILD_ROOT/usr/share/locale/de/LC_MESSAGES/
mkdir -p $RPM_BUILD_ROOT/etc/opsi/backendManager.d
for i in `(cd files/backendManager.d; ls *.conf)`; do install -m 0644 files/backendManager.d/$i $RPM_BUILD_ROOT/etc/opsi/backendManager.d/; done
mkdir -p $RPM_BUILD_ROOT/etc/opsi/hwaudit/locales
install -m 0644 files/hwaudit/opsihwaudit.conf $RPM_BUILD_ROOT/etc/opsi/hwaudit/
for i in files/hwaudit/locales/*; do install -m 0644 $i $RPM_BUILD_ROOT/etc/opsi/hwaudit/locales/; done
mkdir -p $RPM_BUILD_ROOT/etc/openldap/schema
install -m 0644 files/opsi.schema $RPM_BUILD_ROOT/etc/openldap/schema/
install -m 0644 files/opsi-standalone.schema $RPM_BUILD_ROOT/etc/openldap/schema/
mkdir -p $RPM_BUILD_ROOT/usr/share/opsi
install -m 0755 files/share/init-opsi-mysql-db.py $RPM_BUILD_ROOT/usr/share/opsi/
install -m 0755 files/share/register-depot.py $RPM_BUILD_ROOT/usr/share/opsi/
echo %{version} > $RPM_BUILD_ROOT/etc/opsi/version


%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
# default attributes
%defattr(-,root,root)

# documentation
#%doc LICENSE README RELNOTES doc

# configfiles
%config(noreplace) /etc/opsi/backendManager.d/10_file.conf
%config(noreplace) /etc/opsi/backendManager.d/11_ldap.conf
%config(noreplace) /etc/opsi/backendManager.d/13_dhcpd.conf
%config(noreplace) /etc/opsi/backendManager.d/15_jsonrpc.conf
%config(noreplace) /etc/opsi/backendManager.d/16_etherwake.conf
%config(noreplace) /etc/opsi/backendManager.d/17_wakeonlan.conf
%config(noreplace) /etc/opsi/backendManager.d/18_opsipxeconfd.conf
%config(noreplace) /etc/opsi/backendManager.d/20_file31.conf
%config(noreplace) /etc/opsi/backendManager.d/21_mysql.conf
%config(noreplace) /etc/opsi/backendManager.d/30_vars.conf
%config /etc/opsi/backendManager.d/50_interface.conf
%config /etc/opsi/hwaudit/opsihwaudit.conf
%config /etc/opsi/hwaudit/locales/de_DE
%config /etc/opsi/hwaudit/locales/en_US
%config /etc/openldap/schema/opsi.schema
%config /etc/openldap/schema/opsi-standalone.schema
%config /etc/opsi/version

# other files
/usr/share/locale/de/LC_MESSAGES/opsi_system.mo
/usr/share/locale/de/LC_MESSAGES/opsi_ui.mo
/usr/share/opsi/init-opsi-mysql-db.py
/usr/share/opsi/register-depot.py

# directories
%dir /etc/opsi

%changelog
* Wed Sep 17 2008 - j.schneider@uib.de
- created new package
