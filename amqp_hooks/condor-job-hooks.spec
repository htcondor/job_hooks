%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Condor Job Hooks
Name: condor-job-hooks
Version: 1.0
Release: 1%{?dist}
License: ASL 2.0
Group: Applications/System
Source0: %{name}-%{version}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Requires: python >= 2.4
Requires: condor >= 7.0.2-4
Requires: condor-job-hooks-common

%description
This package provides Condor job hooks that communicate with a translation
daemon which interfaces with job delivery protocols outside of condor's
native job delivery protocol.

%package common
Summary: Common functions/utilties for condor job hooks
Group: Applications/System
BuildRequires: python-devel

%description common
Common functions and utilities used by MRG condor job hooks.

%prep
%setup -q

%install
mkdir -p %{buildroot}/%_libexecdir/condor/hooks
mkdir -p %{buildroot}/%{python_sitelib}/jobhooks
mkdir -p %{buildroot}/%_sysconfdir/opt/grid
cp -f hook*.py %{buildroot}/%_libexecdir/condor/hooks
rm -f %{buildroot}/%_libexecdir/condor/hooks/hook_evict_claim.*
cp -f functions.py %{buildroot}/%{python_sitelib}/jobhooks
touch %{buildroot}/%{python_sitelib}/jobhooks/__init__.py
cp -f config/job-hooks.conf %{buildroot}/%{_sysconfdir}/opt/grid

%files
%defattr(-,root,root,-)
%doc LICENSE-2.0.txt
%config(noreplace) %{_sysconfdir}/opt/grid/job-hooks.conf
%defattr(0555,root,root,-)
%_libexecdir/condor/hooks/hook_fetch_work.py*
%_libexecdir/condor/hooks/hook_job_exit.py*
%_libexecdir/condor/hooks/hook_prepare_job.py*
%_libexecdir/condor/hooks/hook_reply_fetch.py*
%_libexecdir/condor/hooks/hook_update_job_status.py*

%files common
%{python_sitelib}/jobhooks/functions.py*
%{python_sitelib}/jobhooks/__init__.py*
