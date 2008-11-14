.PHONY: build condor-job-hooks condor-low-latency

RPMBUILD_DIRS := BUILD RPMS SOURCES SPECS SRPMS

NAME := condor-job-hooks
HOOKS_SPEC := ${NAME}.spec
HOOKS_VERSION := $(shell grep -i version: "${HOOKS_SPEC}" | awk '{print $$2}')
HOOKS_SOURCE := ${NAME}-${HOOKS_VERSION}.tar.gz
HOOKS_DIR := ${NAME}-${HOOKS_VERSION}
NAME := condor-low-latency
LOWLAT_SPEC := ${NAME}.spec
LOWLAT_VERSION := $(shell grep -i version: "${LOWLAT_SPEC}" | awk '{print $$2}')
LOWLAT_SOURCE := ${NAME}-${LOWLAT_VERSION}.tar.gz
LOWLAT_DIR := ${NAME}-${LOWLAT_VERSION}

build: condor-job-hooks condor-low-latency

condor-job-hooks: SPECS/${HOOKS_SPEC} SOURCES/${HOOKS_SOURCE}
	mkdir -p BUILD RPMS SRPMS
	rpmbuild --define="_topdir ${PWD}" -ba SPECS/${HOOKS_SPEC}

condor-low-latency: SPECS/${LOWLAT_SPEC} SOURCES/${LOWLAT_SOURCE}
	mkdir -p BUILD RPMS SRPMS
	rpmbuild --define="_topdir ${PWD}" -ba SPECS/${LOWLAT_SPEC}

SPECS/${HOOKS_SPEC}: ${HOOKS_SPEC}
	mkdir -p SPECS
	cp -f ${HOOKS_SPEC} SPECS

SPECS/${LOWLAT_SPEC}: ${LOWLAT_SPEC}
	mkdir -p SPECS
	cp -f ${LOWLAT_SPEC} SPECS

SOURCES/${HOOKS_SOURCE}: hooks/functions.py hooks/hook_evict_claim.py \
                         hooks/hook_fetch_work.py hooks/hook_job_exit.py \
                         hooks/hook_prepare_job.py hooks/hook_reply_fetch.py \
                         hooks/hook_update_job_status.py
	mkdir -p SOURCES
	rm -rf ${HOOKS_DIR}
	mkdir ${HOOKS_DIR}
	mkdir ${HOOKS_DIR}/config
	cp -f hooks/* ${HOOKS_DIR}
	cp -f config/job-hooks.conf ${HOOKS_DIR}/config
	cp -f LICENSE-2.0.txt ${HOOKS_DIR}
	tar -cf ${HOOKS_SOURCE} ${HOOKS_DIR}
	mv "${HOOKS_SOURCE}" SOURCES

SOURCES/${LOWLAT_SOURCE}: carod config/carod.conf config/condor-low-latency.init
	mkdir -p SOURCES
	rm -rf ${LOWLAT_DIR}
	mkdir ${LOWLAT_DIR}
	mkdir ${LOWLAT_DIR}/config
	cp -f carod ${LOWLAT_DIR}
	cp -f config/carod.conf config/condor-low-latency.init ${LOWLAT_DIR}/config
	cp -f LICENSE-2.0.txt ${LOWLAT_DIR}
	tar -cf ${LOWLAT_SOURCE} ${LOWLAT_DIR}
	mv "${LOWLAT_SOURCE}" SOURCES

clean:
	rm -rf ${RPMBUILD_DIRS} ${HOOKS_DIR} ${LOWLAT_DIR}
