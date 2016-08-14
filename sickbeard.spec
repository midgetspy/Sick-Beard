Summary: Sick Beard
Name: sickbeard
Version: fb37d33
Release: 0%{?dist}
Source0: midgetspy-Sick-Beard-%{version}.tar.gz
License: Python license
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Url: https://github.com/midgetspy/Sick-Beard
BuildRequires: python-cheetah

%description
The ultimate PVR application that searches for and manages your TV shows

%prep
%setup -n midgetspy-Sick-Beard-%{version}

%install
mkdir -p $RPM_BUILD_ROOT/opt/sickbeard $RPM_BUILD_ROOT/etc/init.d
mv init.fedora $RPM_BUILD_ROOT/etc/init.d/sickbeard
mv * $RPM_BUILD_ROOT/opt/sickbeard

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
/opt/sickbeard/*
/etc/init.d/sickbeard

%changelog
* Thu May 09 2013 Arnoud Vermeer <arnoud@freshway.biz> fb37d33-0
- Initial packaging