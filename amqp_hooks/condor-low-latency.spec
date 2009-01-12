Summary: Low Latency Scheduling
Name: condor-low-latency
Version: 1.0
Release: 7%{?dist}
License: ASL 2.0
Group: Applications/System
URL: http://www.redhat.com/mrg
Source0: %{name}-%{version}.tar.gz
Patch0: condor-low-latency-rhel4-init.patch
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch
Requires: python >= 2.3
Requires: condor >= 7.0.2-4
Requires: condor-job-hooks
Requires: condor-job-hooks-common
Requires: python-qpid

Requires(post):/sbin/chkconfig
Requires(preun):/sbin/chkconfig
Requires(preun):/sbin/service
Requires(postun):/sbin/service

%description
Low Latency Scheduling provides a means for bypassing condor's normal
scheduling process and instead submit work directly to an execute node
using the AMQP protocol.

%prep
%setup -q
%if 0%{?rhel} == 4
%patch0 -p0 -b .rhel4
%endif

%install
mkdir -p %{buildroot}%{_sbindir}
mkdir -p %{buildroot}/%{_sysconfdir}/opt/grid
mkdir -p %{buildroot}/%{_initrddir}
cp -f carod %{buildroot}/%_sbindir
cp -f config/carod.conf %{buildroot}/%{_sysconfdir}/opt/grid
cp -f config/condor-low-latency.init %{buildroot}/%{_initrddir}/condor-low-latency

%post
/sbin/chkconfig --add condor-low-latency

%preun
if [ $1 = 0 ]; then
  /sbin/service condor-low-latency stop >/dev/null 2>&1 || :
  /sbin/chkconfig --del condor-low-latency
fi

%postun
if [ "$1" -ge "1" ]; then
  /sbin/service condor-low-latency condrestart >/dev/null 2>&1 || :
fi

%files
%defattr(-,root,root,-)
%doc LICENSE-2.0.txt
%config(noreplace) %_sysconfdir/opt/grid/carod.conf
%defattr(0755,root,root,-)
%_initrddir/condor-low-latency
%_sbindir/carod

%changelog
* Mon Jan 12 2009  <rrati@redhat> - 1.0-7
- BZ474405

* Tue Dec 16 2008  <rrati@redhat> - 1.0-6
- If TransferOutput is set, only transfer the files listed as well as
  stdout/stderr files if they exist
- Only package files in the job's iwd

* Fri Dec  5 2008  <rrati@redhat> - 1.0-5
- Cleaned up socket close code to provide cleaner shutdown

* Wed Dec  3 2008  <rrati@redhat> - 1.0-4
- Fixed python dependency with RHEL4
- Fixed issues running on python 2.3

* Wed Nov 19 2008  <rrati@redhat> - 1.0-3
- Low Latency daemon is on by default
- Daemon now appropriately handles Universe being set

* Fri Nov  4 2008  <rrati@redhat> - 1.0-2
- Add changelog
- Fix rpmlint issues
- Renamed init script to condor-low-latency

* Fri Nov  4 2008  <rrati@redhat> - 1.0-1
- Initial packaging

