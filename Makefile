#!/usr/bin/makee -f

# Hook to Echo Makefile Variable
ifneq ($(emv),)
emv:
	@echo $($(emv))
endif

.DELETE_ON_ERROR:

NOW:=$(shell date "+%Y-%m-%d-%H%M%S")

TGZ = /tmp/bumps-${NOW}.tgz
SRCS = Makefile \
	bumps.html \
	bumps.js \
	bumps.py

release: ${TGZ}

${TGZ}: ${SRCS}
	tar czf $@ ${SRCS}
	tar tvzf $@
	ls -lG $@
