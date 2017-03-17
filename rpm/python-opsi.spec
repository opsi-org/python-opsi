#
# spec file for package python-opsi
#
# Copyright (c) 2013-2017 uib GmbH.
# This file and all modifications and additions to the pristine
# package are under the same license as the package itself.
#
Name:           python-opsi
BuildRequires:  python-devel gettext-devel python-setuptools
Requires:       python >= 2.7 python-twisted-web >= 8.2 python-twisted-conch >= 8.2 python-magic python-sqlalchemy iproute duplicity lshw python-ldaptor

# Dependencies for twisted are a mess because most lack needed packages.
# We try to avoid problems with this:
Requires: python-pyasn1

%if 0%{?suse_version}
BuildRequires:  pwdutils
Requires:       pwdutils
%{py_requires}
%endif
%if 0%{?rhel_version} || 0%{?centos_version} || 0%{?fedora_version}
Requires:       m2crypto python-ctypes pyOpenSSL newt-python python-twisted >= 8.2 PyPAM MySQL-python
%if 0%{?rhel_version} >= 700 || 0%{?centos_version} >= 700
# To have ifconfig available
Requires:	net-tools
%endif
%else
Requires:       python-m2crypto python-openssl lsb-release python-newt python-pam python-mysql
%endif
%if 0%{?suse_version}
# Needed for working python-magic
Requires:       libmagic1 python-pycrypto
%else
Requires:	python-crypto
%endif
Url:            http://www.opsi.org
License:        AGPL-3.0+
Group:          Productivity/Networking/Opsi
AutoReqProv:    on
Version:        4.0.7.35
Release:        1
Summary:        Python library for the client management solution opsi
Source:         python-opsi_4.0.7.35-1.tar.gz
#Source2:        setup.py
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
# python noarch modules are only working on openSUSE 11.2 or higher
# also disabled for non SUSE distros
%if %{?suse_version: %{suse_version} >= 1120} %{!?suse_version:1}
BuildArch:      noarch
%endif
%if 0%{?centos_version} || 0%{?rhel_version} || 0%{?fedora_version}
BuildRequires:  gettext
%else
BuildRequires:  gettext-runtime
%endif

%define toplevel_dir %{name}-%{version}

# ===[ description ]================================
%description
This package contains the opsi python library.

# ===[ debug_package ]==============================
%debug_package

# ===[ prep ]=======================================
%prep

# ===[ setup ]======================================
%setup -n %{name}-%{version}

# ===[ build ]======================================
%build
export CFLAGS="$RPM_OPT_FLAGS"
python setup.py build

# ===[ install ]====================================
%install
mkdir -p $RPM_BUILD_ROOT/etc/opsi/systemdTemplates

# install python files and record installed files in INSTALLED_FILES
%if 0%{?suse_version}
python setup.py install --prefix=%{_prefix} --root=$RPM_BUILD_ROOT --record-rpm=INSTALLED_FILES
%else
python setup.py install --prefix=%{_prefix} --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
%endif

%if 0%{?rhel_version} || 0%{?centos_version}
sed -i 's#/etc/dhcp3/dhcpd.conf#/etc/dhcp/dhcpd.conf#' $RPM_BUILD_ROOT/etc/opsi/backends/dhcpd.conf
sed -i 's#dhcp3-server#dhcpd#' $RPM_BUILD_ROOT/etc/opsi/backends/dhcpd.conf
%else
sed -i 's#/etc/dhcp3/dhcpd.conf#/etc/dhcpd.conf#;s#dhcp3-server#dhcpd#' $RPM_BUILD_ROOT/etc/opsi/backends/dhcpd.conf
%endif

%if 0%{?suse_version} == 1110 || 0%{?suse_version} == 1315
	# We only want to change this on SLES.
	sed -i 's#linux/pxelinux.0#opsi/pxelinux.0#' $RPM_BUILD_ROOT/etc/opsi/backends/dhcpd.conf
%endif

# ===[ clean ]======================================
%clean
rm -rf $RPM_BUILD_ROOT

# ===[ post ]=======================================
%post
fileadmingroup=$(grep "fileadmingroup" /etc/opsi/opsi.conf | cut -d "=" -f 2 | sed 's/\s*//g')
if [ -z "$fileadmingroup" ]; then
	fileadmingroup=pcpatch
fi
if [ $fileadmingroup != pcpatch -a -z "$(getent group $fileadmingroup)" ]; then
	groupmod -n $fileadmingroup pcpatch
else
	if [ -z "$(getent group $fileadmingroup)" ]; then
		groupadd $fileadmingroup
	fi
fi

if [ -z "`getent passwd pcpatch`" ]; then
	useradd --system -g $fileadmingroup -d /var/lib/opsi -s /bin/false pcpatch
fi

if [ -z "`getent passwd opsiconfd`" ]; then
	useradd --system -g $fileadmingroup -d /var/lib/opsi -s /bin/bash opsiconfd
fi

if [ -z "`getent group opsiadmin`" ]; then
	groupadd opsiadmin
fi

chown -R root:$fileadmingroup /etc/opsi/backendManager
find /etc/opsi/backendManager -type d -exec chmod 770 {} \;
find /etc/opsi/backendManager -type f -exec chmod 660 {} \;
chown -R root:$fileadmingroup /etc/opsi/backends
chmod 770 /etc/opsi/backends
chmod 660 /etc/opsi/backends/*.conf
chown root:$fileadmingroup /etc/opsi/opsi.conf
chmod 660 /etc/opsi/opsi.conf

test -e /etc/opsi/pckeys || touch /etc/opsi/pckeys
chown root:$fileadmingroup /etc/opsi/pckeys
chmod 660 /etc/opsi/pckeys

test -e /etc/opsi/passwd || touch /etc/opsi/passwd
chown root:$fileadmingroup /etc/opsi/passwd
chmod 660 /etc/opsi/passwd

[ -e "/etc/opsi/backendManager/acl.conf" ]      || cp /etc/opsi/backendManager/acl.conf.default      /etc/opsi/backendManager/acl.conf
[ -e "/etc/opsi/backendManager/dispatch.conf" ] || cp /etc/opsi/backendManager/dispatch.conf.default /etc/opsi/backendManager/dispatch.conf

# ===[ files ]======================================
%files -f INSTALLED_FILES

# default attributes
%defattr(-,root,root)

# configfiles
%config(noreplace) /etc/opsi/backends/dhcpd.conf
%config(noreplace) /etc/opsi/backends/file.conf
%config(noreplace) /etc/opsi/backends/hostcontrol.conf
%config(noreplace) /etc/opsi/backends/jsonrpc.conf
%config(noreplace) /etc/opsi/backends/mysql.conf
%config(noreplace) /etc/opsi/backends/opsipxeconfd.conf
%config /etc/opsi/backendManager/acl.conf.default
%config /etc/opsi/backendManager/dispatch.conf.default
%config /etc/opsi/backendManager/extend.d/10_opsi.conf
%config /etc/opsi/backendManager/extend.d/10_wim.conf
%config /etc/opsi/backendManager/extend.d/20_legacy.conf
%config /etc/opsi/backendManager/extend.d/40_groupActions.conf
%config /etc/opsi/backendManager/extend.d/40_admin_tasks.conf
%config /etc/opsi/backendManager/extend.d/70_wan.conf
%config /etc/opsi/backendManager/extend.d/70_dynamic_depot.conf
%config /etc/opsi/hwaudit/opsihwaudit.conf
%config /etc/opsi/hwaudit/locales/de_DE
%config /etc/opsi/hwaudit/locales/da_DA
%config /etc/opsi/hwaudit/locales/en_US
%config /etc/opsi/hwaudit/locales/es_ES
%config /etc/opsi/hwaudit/locales/fr_FR
%config /etc/opsi/hwaudit/locales/ru_RU

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
%dir /etc/opsi/systemdTemplates

%if 0%{?rhel_version} || 0%{?centos_version} || 0%{?fedora_version}
%define python_sitearch %(%{__python} -c 'from distutils import sysconfig; print sysconfig.get_python_lib()')
%{python_sitearch}/OPSI/*
%endif

# ===[ changelog ]==================================
%changelog
