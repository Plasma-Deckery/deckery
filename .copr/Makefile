NAME    := deckery
outdir  ?= $(CURDIR)/outdir

# Beta channel: BETA=1 make srpm  →  date+hash release, version from git tag.
# Stable channel: make srpm        →  Release: 1, version from spec file.
ifdef BETA
spec      ?= packaging/deckery-tray-beta.spec
VERSION   := $(shell git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//')
GIT_DATE  := $(shell date +%Y%m%d)
GIT_HASH  := $(shell git rev-parse --short HEAD)
BETA_DEFINES := --define "git_version $(VERSION)" \
                --define "beta_release 0.$(GIT_DATE).g$(GIT_HASH)"
else
spec      ?= packaging/deckery-tray.spec
VERSION   := $(shell awk '/^Version:/{print $$2; exit}' $(spec))
BETA_DEFINES :=
endif

.PHONY: srpm builddeps clean

builddeps:
	if command -v dnf >/dev/null 2>&1; then \
	    dnf -y install git rpm-build; \
	fi

srpm: builddeps
	mkdir -p $(outdir)
	git archive --prefix=$(NAME)-$(VERSION)/ -o $(outdir)/$(NAME)-$(VERSION).tar HEAD
	gzip -f $(outdir)/$(NAME)-$(VERSION).tar
	rpmbuild -bs \
	    --define "_sourcedir $(outdir)" \
	    --define "_srcrpmdir $(outdir)" \
	    --define "_topdir $(outdir)/rpmbuild" \
	    $(BETA_DEFINES) \
	    $(spec)
	@echo "SRPM written to $(outdir)"

clean:
	rm -rf $(outdir)
