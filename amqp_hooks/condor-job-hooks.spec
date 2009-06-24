%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%define rel 6

Summary: Condor Job Hooks
Name: condor-job-hooks
Version: 1.0
Release: %{rel}%{?dist}
License: ASL 2.0
Group: Applications/System
URL: http://www.redhat.com/mrg
Source0: %{name}-%{version}-%{rel}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch
Requires: python >= 2.3
Requires: condor >= 7.0.2-4
Requires: condor-job-hooks-common

%description
This package provides Condor job hooks that communicate with a translation
daemon which interfaces with job delivery protocols outside of condor's
native job delivery protocol.

%package common
Summary: Common functions/utilities for condor job hooks
Group: Applications/System
BuildRequires: python-devel
Requires: python >= 2.3

%description common
Common functions and utilities used by MRG condor job hooks.

%prep
%setup -q

%post
if [[ -f /etc/opt/grid/job-hooks.conf ]]; then
   mv -f /etc/opt/grid/job-hooks.conf /etc/condor
   rmdir --ignore-fail-on-non-empty -p /etc/opt/grid
fi

%install
mkdir -p %{buildroot}/%_libexecdir/condor/hooks
mkdir -p %{buildroot}/%{python_sitelib}/jobhooks
mkdir -p %{buildroot}/%_sysconfdir/condor
cp -f hook*.py %{buildroot}/%_libexecdir/condor/hooks
rm -f %{buildroot}/%_libexecdir/condor/hooks/hook_evict_claim.*
cp -f functions.py %{buildroot}/%{python_sitelib}/jobhooks
touch %{buildroot}/%{python_sitelib}/jobhooks/__init__.py
cp -f config/job-hooks.conf %{buildroot}/%{_sysconfdir}/condor

%files
%defattr(-,root,root,-)
%doc LICENSE-2.0.txt
%config(noreplace) %{_sysconfdir}/condor/job-hooks.conf
%defattr(0755,root,root,-)
%_libexecdir/condor/hooks/hook_fetch_work.py*
%_libexecdir/condor/hooks/hook_job_exit.py*
%_libexecdir/condor/hooks/hook_prepare_job.py*
%_libexecdir/condor/hooks/hook_reply_fetch.py*
%_libexecdir/condor/hooks/hook_update_job_status.py*

%files common
%defattr(-,root,root,-)
%doc LICENSE-2.0.txt
%{python_sitelib}/jobhooks/functions.py*
%{python_sitelib}/jobhooks/__init__.py*

%changelog
* Tue Jun  2 2009  <rrati@redhat> - 1.0-6
- Fixed an exception condition in the prepare hook that wasn't handled
  correctly

* Fri Feb 13 2009  <rrati@redhat> - 1.0-5
- Change source tarball name

* Fri Dec  5 2008  <rrati@redhat> - 1.0-4
- Cleaned up socket close code to provide cleaner shutdown

* Wed Dec  3 2008  <rrati@redhat> - 1.0-3
- Fixed python dependency issue with RHEL4
- Fixed issues running on python 2.3

* Fri Nov  4 2008  <rrati@redhat> - 1.0-2
- Add changelog
- Fix rpmlint issues

* Fri Nov  4 2008  <rrati@redhat> - 1.0-1
- Initial packaging
