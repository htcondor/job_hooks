%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?is_fedora: %define is_fedora %(/bin/sh -c "if [ -e /etc/fedora-release ];then echo '1'; fi")}
%define rel 14

Summary: Condor Job Hooks
Name: condor-job-hooks
Version: 1.0
Release: %{rel}%{?dist}
License: ASL 2.0
Group: Applications/System
URL: http://www.redhat.com/mrg
# This is a Red Hat maintained package which is specific to
# our distribution.  Thus the source is only available from
# within this srpm.
Source0: %{name}-%{version}-%{rel}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch
Requires: python >= 2.3
Requires: condor >= 7.0.2-4
Requires: python-%{name}-common

%description
This package provides Condor job hooks that communicate with a translation
daemon which interfaces with job delivery protocols outside of condor's
native job delivery protocol.

%package -n python-%{name}-common
Summary: Common functions/utilities for condor job hooks
Group: Applications/System
BuildRequires: python-devel
Requires: python >= 2.3
Obsoletes: condor-job-hooks-common

%description -n python-%{name}-common
Common functions and utilities used by MRG condor job hooks.

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/%_libexecdir/condor/hooks
mkdir -p %{buildroot}/%{python_sitelib}/jobhooks
mkdir -p %{buildroot}/%_sysconfdir/condor
cp -f hook*.py %{buildroot}/%_libexecdir/condor/hooks
rm -f %{buildroot}/%_libexecdir/condor/hooks/hook_evict_claim.*
cp -f functions.py %{buildroot}/%{python_sitelib}/jobhooks
touch %{buildroot}/%{python_sitelib}/jobhooks/__init__.py
cp -f config/job-hooks.conf %{buildroot}/%{_sysconfdir}/condor

%post
%if 0%{?is_fedora} == 0
if [[ -f /etc/opt/grid/job-hooks.conf ]]; then
   mv -f /etc/opt/grid/job-hooks.conf /etc/condor
   rmdir --ignore-fail-on-non-empty -p /etc/opt/grid
fi
%endif
exit 0

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc LICENSE-2.0.txt INSTALL
%config(noreplace) %{_sysconfdir}/condor/job-hooks.conf
%defattr(0755,root,root,-)
%_libexecdir/condor/hooks/hook_fetch_work.py*
%_libexecdir/condor/hooks/hook_job_exit.py*
%_libexecdir/condor/hooks/hook_prepare_job.py*
%_libexecdir/condor/hooks/hook_reply_fetch.py*
%_libexecdir/condor/hooks/hook_update_job_status.py*

%files -n python-%{name}-common
%defattr(-,root,root,-)
%doc LICENSE-2.0.txt
%{python_sitelib}/jobhooks/functions.py*
%{python_sitelib}/jobhooks/__init__.py*

%changelog
* Mon Jan 26 2010  <rrati@redhat> - 1.0-14
- Fixed handling of multiple args using Popen in run_cmd
- Added comments to a few methods
- Fixed type in run_cmd when using the popen2 module

* Fri Sep 11 2009  <rrati@redhat> - 1.0-13
- Use popen2 module instead of subprocess on python versions that don't
  have the subprocess module (BZ522467)

* Tue Aug 18 2009  <rrati@redhat> - 1.0-12
- Job hooks use JOB_HOOK as keyword instead of LL_HOOK
- Fixed version numbering

* Tue Aug 18 2009  <rrati@redhat> - 1.0-11
- Split documentation into two files, one for carod and one for
  the job-hooks

* Mon Aug 17 2009  <rrati@redhat> - 1.0-10
- Minor cleanup in common functions

* Mon Jul 27 2009  <rrati@redhat> - 1.0-9
- Renamed condor-job-hooks-common to python-condor-job-hooks-common to
  conform to packaging guidelines since the package installs in
  python sitelib.

* Mon Jul 27 2009  <rrati@redhat> - 1.0-8
- Fix rpmlint/packaging issues

* Wed Jun 24 2009  <rrati@redhat> - 1.0-7
- Hooks will first look for their configuration in condor's configuration
  files, then fall back to their config file
- The config file has moved from /etc/opt/grid to /etc/condor

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
