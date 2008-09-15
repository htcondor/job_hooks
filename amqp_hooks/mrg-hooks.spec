%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Hooks to allow condor to communicate with caro
Name: mrg-hooks
Version: 1.0
Release: 1%{?dist}
License: ASL 2.0
Group: Applications/System
Source0: %{name}-%{version}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Requires: python >= 2.4
Requires: condor >= 7.0.2-4

%description
Condor hooks that communicate with the carod AMQP translation daemon.

%prep
%setup -q

%install
mkdir -p %{buildroot}/%_var/lib/condor/hooks
cp hook*.py %{buildroot}/%_var/lib/condor/hooks
mkdir -p %{buildroot}/%{python_sitelib}/%{name}
cp functions.py %{buildroot}/%{python_sitelib}/%{name}
touch %{buildroot}/%{python_sitelib}/%{name}/__init__.py

%files
%defattr(0555,root,root-)
%_var/lib/condor/hooks/hook_evict_claim.py*
%_var/lib/condor/hooks/hook_fetch_work.py*
%_var/lib/condor/hooks/hook_job_exit.py*
%_var/lib/condor/hooks/hook_prepare_job.py*
%_var/lib/condor/hooks/hook_reply_fetch.py*
%_var/lib/condor/hooks/hook_update_job_status.py*
%{python_sitelib}/%{name}/functions.py*
%{python_sitelib}/%{name}/__init__.py*
