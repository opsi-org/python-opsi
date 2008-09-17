#
# spec file for package python-opsi
#
# Copyright (c) 2008 uib GmbH.
# This file and all modifications and additions to the pristine
# package are under the same license as the package itself.
#

Name:           python-opsi
BuildRequires:  python-devel
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
python setup.py install --prefix=%{_prefix} --root=$RPM_BUILD_ROOT --record-rpm=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES

%defattr(-,root,root)

#%doc AUTHORS NEWS README ChangeLog COPYING
#%doc examples

%changelog
* Wed Sep 17 2008 - j.schneider@uib.de
- created new package
