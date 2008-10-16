Summary: Low Latency Scheduling
Name: low-latency
Version: 1.0
Release: 1%{?dist}
License: ASL 2.0
Group: Applications/System
Source0: %{name}-%{version}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch
Requires: python >= 2.4
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

%install
mkdir -p %{buildroot}%{_sbindir}
mkdir -p %{buildroot}/%{_sysconfdir}/opt/grid
mkdir -p %{buildroot}/%{_initrddir}
cp -f carod %{buildroot}/%_sbindir
cp -f config/carod.conf %{buildroot}/%{_sysconfdir}/opt/grid
cp -f config/caro.init %{buildroot}/%{_initrddir}/caro

%post
/sbin/chkconfig --add caro

%preun
if [ $1 = 0 ]; then
  /sbin/service caro stop >/dev/null 2>&1 || :
  /sbin/chkconfig --del caro
fi

%postun
if [ "$1" -ge "1" ]; then
  /sbin/service caro condrestart >/dev/null 2>&1 || :
fi

%files
%defattr(-,root,root,-)
%doc LICENSE-2.0.txt
%config(noreplace) %_sysconfdir/opt/grid/carod.conf
%attr(0755,root,root) %_initrddir/caro
%defattr(0555,root,root,-)
%_sbindir/carod
