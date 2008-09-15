.PHONY: build mrg-hooks caro

RPMBUILD_DIRS := BUILD RPMS SOURCES SPECS SRPMS

NAME := mrg-hooks
HOOKS_SPEC := ${NAME}.spec
HOOKS_VERSION := $(shell grep -i version: "${NAME}.spec" | awk '{print $$2}')
HOOKS_SOURCE := ${NAME}-${HOOKS_VERSION}.tar.gz
NAME := caro
CARO_SPEC := ${NAME}.spec
CARO_VERSION := $(shell grep -i version: "${NAME}.spec" | awk '{print $$2}')
CARO_SOURCE := ${NAME}-${CARO_VERSION}.tar.gz
tmpdir := $(shell mktemp -d)

build: mrg-hooks caro

mrg-hooks: SPECS/${HOOKS_SPEC} SOURCES/${HOOKS_SOURCE}
	mkdir -p BUILD RPMS SRPMS
	rpmbuild --define="_topdir ${PWD}" -ba SPECS/${HOOKS_SPEC}

caro: SPECS/${CARO_SPEC} SOURCES/${CARO_SOURCE}
	mkdir -p BUILD RPMS SRPMS
	rpmbuild --define="_topdir ${PWD}" -ba SPECS/${CARO_SPEC}

SPECS/${HOOKS_SPEC}: ${HOOKS_SPEC}
	mkdir -p SPECS
	cp -f ${HOOKS_SPEC} SPECS

SPECS/${CARO_SPEC}: ${CARO_SPEC}
	mkdir -p SPECS
	cp -f ${CARO_SPEC} SPECS

SOURCES/${HOOKS_SOURCE}:
	mkdir -p SOURCES
	rm -rf mrg-hooks-${HOOKS_VERSION}
	mkdir mrg-hooks-${HOOKS_VERSION}
	cp -f hooks/* mrg-hooks-${HOOKS_VERSION}
	tar -cf ${HOOKS_SOURCE} mrg-hooks-${HOOKS_VERSION}
	mv "${HOOKS_SOURCE}" SOURCES

SOURCES/${CARO_SOURCE}:
	mkdir -p SOURCES
	rm -rf caro-${CARO_VERSION}
	mkdir caro-${CARO_VERSION}
	cp -f carod caro-${CARO_VERSION}
	tar -cf ${CARO_SOURCE} caro-${CARO_VERSION}
	mv "${CARO_SOURCE}" SOURCES

clean:
	rm -rf ${RPMBUILD_DIRS} mrg-hooks-${HOOKS_VERSION} caro-${CARO_VERSION}
