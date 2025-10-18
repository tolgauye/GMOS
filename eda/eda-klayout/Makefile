.PHONY: help build deploy test dropbox-deploy

GITCOMMIT := $(shell git rev-parse --short HEAD)
KLAYOUT_VERSION := $(shell source version.sh && echo $$KLAYOUT_VERSION)
ifndef PYTHON_VERSION
    PYTHON_VERSION := B37
endif
ifndef MACOS_VERSION
	MACOS_VERSION := HighSierra
endif

.ONESHELL:

default: help

help:
	@echo "For Mac OS only"
	@echo "make build PYTHON_VERSION=B37"
	@echo "make deploy PYTHON_VERSION=B37"
	@echo "make test MACOS_VERSION=HighSierra"
	@echo "Valid Mac OS Versions: [Yosemite, ElCapitan, Sierra, HighSierra]"
	@echo "Valid Python Version: [nil, Sys, B37]"

build:
	@echo "Building for Mac $(GITCOMMIT)"
	./build4mac.py -p $(PYTHON_VERSION) -q Qt5Brew -c; \
	./build4mac.py -p $(PYTHON_VERSION) -q Qt5Brew

deploy:
	@echo "Deploying 4 Mac $(GITCOMMIT)"
	./build4mac.py -p $(PYTHON_VERSION) -q Qt5Brew -y
	
test:
	@echo "Testing 4 Mac $(GITCOMMIT)"
	qt5.pkg.macos-$(MACOS_VERSION)-release/klayout.app/Contents/MacOS/klayout -b -r test-pylib-script.py; \
	cd qt5.build.macos-$(MACOS_VERSION)-release; \
	ln -s klayout.app/Contents/MacOS/klayout klayout; \
	export TESTTMP=testtmp; \
	export TESTSRC=..; \
	export DYLD_LIBRARY_PATH=.:db_plugins/:lay_plugins/; \
	./ut_runner -h || true; \
	cd ..

dropbox-deploy:
	@echo "Preparing for dropbox deployment $(MACOS_VERSION) $(GITCOMMIT)"
	mkdir -p deploy/$(MACOS_VERSION)/$(PYTHON_VERSION)/$(KLAYOUT_VERSION); \
	pwd; \
	ls -lah; \
	touch build.txt; \
	cp build.txt deploy/$(MACOS_VERSION)/$(PYTHON_VERSION)/$(KLAYOUT_VERSION)/qt5.pkg.macos-$(MACOS_VERSION)-$(PYTHON_VERSION)-release-$(KLAYOUT_VERSION)-$(GITCOMMIT).log.txt; \
	hdiutil convert macbuild/Resources/klayoutDMGTemplate.dmg -format UDRW -o work-KLayout.dmg; \
	hdiutil resize -size 500m work-KLayout.dmg; \
	hdiutil attach work-KLayout.dmg -readwrite -noverify -quiet -mountpoint tempKLayout -noautoopen; \
	cp -a qt5.pkg.macos-$(MACOS_VERSION)-release/ tempKLayout/; \
	hdiutil detach tempKLayout; \
	hdiutil convert work-KLayout.dmg -format UDZO -imagekey zlib-level=9 -o deploy/$(MACOS_VERSION)/$(PYTHON_VERSION)/$(KLAYOUT_VERSION)/qt5.pkg.macos-$(MACOS_VERSION)-$(PYTHON_VERSION)-release-$(KLAYOUT_VERSION)-$(GITCOMMIT).dmg; \
	md5 -q deploy/$(MACOS_VERSION)/$(PYTHON_VERSION)/$(KLAYOUT_VERSION)/qt5.pkg.macos-$(MACOS_VERSION)-$(PYTHON_VERSION)-release-$(KLAYOUT_VERSION)-$(GITCOMMIT).dmg > deploy/$(MACOS_VERSION)/$(PYTHON_VERSION)/$(KLAYOUT_VERSION)/qt5.pkg.macos-$(MACOS_VERSION)-$(PYTHON_VERSION)-release-$(KLAYOUT_VERSION)-$(GITCOMMIT).dmg.md5; \
	rm work-KLayout.dmg
