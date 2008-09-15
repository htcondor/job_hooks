%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: AMQP translation daemon for condor
Name: caro
Version: 1.0
Release: 1%{?dist}
License: ASL 2.0
Group: Applications/System
Source0: %{name}-%{version}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Requires: python >= 2.4
Requires: condor >= 7.0.2-4
Requires: mrg-hooks

%description
The caro daemon provides a translation daemon that allows communcation
between condor's job hooks functionality and the AMQP protocol.

This is just the translation daemon.  For a fully functional system,
condor must be configured to use job hooks and execute hooks that can
communicate with the carod daemon.

%prep
%setup -q

%install
mkdir -p %{buildroot}%_sbindir
cp carod %{buildroot}/%_sbindir

%files
%defattr(0555,root,root-)
%_sbindir/carod
