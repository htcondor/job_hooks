NAME := condor-job-hooks

.PHONY: build ${NAME}

RPMBUILD_DIRS := BUILD BUILDROOT RPMS SOURCES SPECS SRPMS
null :=
space := ${null} ${null}

SPEC := ${NAME}.spec
VER = $(shell cat "VERSION")
ORIG_VER := $(call VER)
ORIG_MAJOR := $(shell cat "VERSION" | cut -d '.' -f 1)
ORIG_MINOR := $(shell cat "VERSION" | cut -d '.' -f 2)
ORIG_PATCH := $(shell cat "VERSION" | cut -d '.' -f 3)
PREFIX := ${NAME}-${ORIG_VER}
SOURCE := ${PREFIX}.tar.gz
RELEASE ?= 1
PATCH_NUM := 0

bump_and_commit_version = \
  $(eval NEW_VER := $(1).$(2).$(3)) \
  sed -i "s/${ORIG_VER}/${NEW_VER}/" VERSION; \
  git commit -m "bumping VERSION from ${ORIG_VER} to ${NEW_VER}" VERSION; \
  git tag ${NEW_VER}; \
  git push origin master ${new_ver}

create_patch_lines = \
Patch${PATCH_NUM}: ${file} \
$(eval APPLY_LINES += %patch${PATCH_NUM} -p1)\
$(eval PATCH_NUM := $(shell expr ${PATCH_NUM} + 1))

build: ${NAME}

${NAME}: rpmdirs gen_patches SPECS/${SPEC} SOURCES/${SOURCE}
	rpmbuild --define="_topdir ${PWD}" -ba SPECS/${SPEC}

bump_major: VERSION
	$(eval MAJOR := $(shell expr ${ORIG_MAJOR} + 1))
	$(call bump_and_commit_version,${MAJOR},0,0)

bump_minor: VERSION
	$(eval MINOR := $(shell expr ${ORIG_MINOR} + 1))
	$(call bump_and_commit_version,${ORIG_MAJOR},${MINOR},0)

bump_patch: VERSION
	$(eval PATCH := $(shell expr ${ORIG_PATCH} + 1))
	$(call bump_and_commit_version,${ORIG_MAJOR},${ORIG_MINOR},${PATCH})

SPECS/${SPEC}: rpmdirs ${SPEC}.in
	sed "s/#VERSION#/${ORIG_VER}/" ${SPEC}.in > ${SPEC}
	sed -i "s/#RELEASE#/${RELEASE}/" ${SPEC}
	$(eval PATCH_FILES := $(sort $(shell ls SOURCES/*.patch)))
	$(eval PATCH_LINES := $(strip $(foreach file,$(notdir ${PATCH_FILES}),$(create_patch_lines))))
	$(eval PATCH_LINES := $(subst patch${space},patch\n, ${PATCH_LINES}))
	$(eval APPLY_LINES := $(subst -p1${space},-p1\n, ${APPLY_LINES}))
	echo "${PATCH_LINES}"
	sed -i 's/#PATCHES#/${PATCH_LINES}/' ${SPEC}
	sed -i 's/#APPLY_PATCHES#/${APPLY_LINES}/' ${SPEC}
	cp -f ${SPEC} SPECS

SOURCES/${SOURCE}: rpmdirs pristine
	cp ${SOURCE} SOURCES

pristine:
	@git archive --format=tar ${ORIG_VER} --prefix=${PREFIX}/ | gzip -9nv > ${SOURCE} 2> /dev/null

upload_pristine: pristine
ifndef FH_USERNAME
	@echo "Please set FH_USERNAME" 
else
	scp ${SOURCE} ${FH_USERNAME}@fedorahosted.org:grid
endif

gen_patches: rpmdirs
ifdef SIMPLE_GIT_PATCH_NAMES
	$(eval SIMPLE_NAMES := --numbered-files)
else
	$(eval SIMPLE_NAMES := )
endif
	git format-patch ${SIMPLE_NAMES} -o SOURCES ${ORIG_VER}

rpmdirs:
	mkdir -p ${RPMBUILD_DIRS}

clean:
	rm -rf ${RPMBUILD_DIRS} ${PREFIX} ${SOURCE} ${SPEC}
