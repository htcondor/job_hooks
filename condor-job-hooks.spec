%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?is_fedora: %define is_fedora %(/bin/sh -c "if [ -e /etc/fedora-release ];then echo '1'; fi")}
%define rel 3

Summary: Condor Job Hooks
Name: condor-job-hooks
Version: 1.4
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
Requires: python-condorutils >= 1.4

%description
This package provides Condor job hooks that communicate with a translation
daemon which interfaces with job delivery protocols outside of condor's
native job delivery protocol.

%package -n python-condorutils
Summary: Common functions/utilities for condor job hooks
Group: Applications/System
BuildRequires: python-devel >= 2.3
Requires: python >= 2.3
Obsoletes: condor-job-hooks-common
Obsoletes: python-condor-job-hooks-common

%description -n python-condorutils
Common functions and utilities used by condor features.

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/%_libexecdir/condor/hooks
mkdir -p %{buildroot}/%{python_sitelib}/condorutils
mkdir -p %{buildroot}/%_sysconfdir/condor
cp -f hooks/hook*.py %{buildroot}/%_libexecdir/condor/hooks
rm -f %{buildroot}/%_libexecdir/condor/hooks/hook_evict_claim.*
cp -f module/*.py %{buildroot}/%{python_sitelib}/condorutils

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
%defattr(0755,root,root,-)
%_libexecdir/condor/hooks/hook_fetch_work.py*
%_libexecdir/condor/hooks/hook_job_exit.py*
%_libexecdir/condor/hooks/hook_prepare_job.py*
%_libexecdir/condor/hooks/hook_reply_fetch.py*
%_libexecdir/condor/hooks/hook_update_job_status.py*

%files -n python-condorutils
%defattr(-,root,root,-)
%doc LICENSE-2.0.txt
%{python_sitelib}/condorutils/__init__.py*
%{python_sitelib}/condorutils/log.py*
%{python_sitelib}/condorutils/osutil.py*
%{python_sitelib}/condorutils/readconfig.py*
%{python_sitelib}/condorutils/socketutil.py*
%{python_sitelib}/condorutils/workfetch.py*

%changelog
* Mon Aug 02 2010  <rrati@redhat> - 1.4-3
- Fixed issue with run_cmd causing a deadlock when commands returned
  a large amount of data on python2.3

* Fri Jul 23 2010  <rrati@redhat> - 1.4-2
- Fixed output of run_cmd on python2.3 when using popen2
- Fixed resetting of environment variables when run on python2.3

* Mon Jun 28 2010  <rrati@redhat> - 1.4-1
- Updated dependecy versions

* Fri Jun 11 2010  <rrati@redhat> - 1.4-0.6
- The prepare hook only logs on non-windows machines

* Fri Jun 11 2010  <rrati@redhat> - 1.4-0.5
- Additional logging
- Prepare hook will log to syslog

* Thu Jun 03 2010  <rrati@redhat> - 1.4-0.4
- Fix setting of PATH on non-Unix machines in run_cmd
- Better handle errors when running commands in run_cmd
 
* Wed Apr 14 2010  <rrati@redhat> - 1.4-0.3
- Added optional environ param to read_condor_config

* Wed Apr 14 2010  <rrati@redhat> - 1.4-0.2
- Fixed issue setting/reseting environment variables when popen2 is used.
  Any params set by the caller were not getting reset by the time run_cmd
  was exiting, so the environment was permanently modified.

* Thu Apr  8 2010  <rrati@redhat> - 1.4-0.1
- Added option param to run_cmd (inter).  This will allow commands to be
  run that require user interaction
- Fixed setting of environment before executing the command.  PATH is
  always overriden and defined as a trusted set of directories.
- Updated usage of run_cmd

* Mon Mar 29 2010  <rrati@redhat> - 1.3-0.1
- Changed Exception names
- Changed log_messages to log
- Renamed python module to condorutils
- Removed functions.py and moved to separate modules
- Improved error handling for when calling close_socket and pickle.loads
- log_messages no long takes an exception, but a list of strings to print

* Thu Mar 11 2010  <rrati@redhat> - 1.2-0.2
- Added importing of logging module into common functions

* Tue Mar 09 2010  <rrati@redhat> - 1.2-0.1
- Changed log_messages to use native logging module rather than syslog
- Changed general_execption to GeneralError
- Exception no longer takes a level
- log_messages now requires a level passed to it
- Changed run_cmd to return 3 values rather than a list of 3 values
- Fixed read_config_config to be able to handle 1 word params (ie LOG)
- log_messages takes an optional 3rd arg that specifies the name of a
  logging subsystem to use.  If none is given, the base logger is used

* Thu Mar 04 2010  <rrati@redhat> - 1.1-0.1
- run_cmd takes an optional 3rd arg that specifies environment vars to set

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
