.PHONY: build condor-job-hooks condor-low-latency

RPMBUILD_DIRS := BUILD BUILDROOT RPMS SOURCES SPECS SRPMS

NAME := condor-job-hooks
SPEC := ${NAME}.spec
VERSION := $(shell grep -i version: "${SPEC}" | awk '{print $$2}')
RELEASE := $(shell grep -i 'define rel' "${SPEC}" | awk '{print $$3}')
SOURCE := ${NAME}-${VERSION}-${RELEASE}.tar.gz
DIR := ${NAME}-${VERSION}

build: condor-job-hooks condor-low-latency

condor-job-hooks: SPECS/${SPEC} SOURCES/${SOURCE}
	mkdir -p BUILD RPMS SRPMS
	rpmbuild --define="_topdir ${PWD}" -ba SPECS/${SPEC}

SPECS/${SPEC}: ${SPEC}
	mkdir -p SPECS
	cp -f ${SPEC} SPECS

SOURCES/${SOURCE}: hooks/functions.py hooks/hook_evict_claim.py \
                         hooks/hook_fetch_work.py hooks/hook_job_exit.py \
                         hooks/hook_prepare_job.py hooks/hook_reply_fetch.py \
                         hooks/hook_update_job_status.py
	mkdir -p SOURCES
	rm -rf ${DIR}
	mkdir ${DIR}
	mkdir ${DIR}/config
	cp -f hooks/* ${DIR}
	cp -f config/job-hooks.conf ${DIR}/config
	cp -f LICENSE-2.0.txt ${DIR}
	cp -f INSTALL ${DIR}
	tar -cf ${SOURCE} ${DIR}
	mv "${SOURCE}" SOURCES

clean:
	rm -rf ${RPMBUILD_DIRS} ${DIR}
