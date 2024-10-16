SHELL := bash# we want bash behaviour in all shell invocations
PLATFORM := $(shell uname)

RED := $(shell tput setaf 1)
GREEN := $(shell tput setaf 2)
YELLOW := $(shell tput setaf 3)
BOLD := $(shell tput bold)
NORMAL := $(shell tput sgr0)

ifneq (4,$(firstword $(sort $(MAKE_VERSION) 4)))
  $(warning $(BOLD)$(RED)GNU Make v4 or newer is required$(NORMAL))
  $(info On macOS it can be installed with $(BOLD)brew install make$(NORMAL) and run as $(BOLD)gmake$(NORMAL))
  $(error Please run with GNU Make v4 or newer)
endif

# Documentation code cribbed from the Changelog.com's excellent Makefile

SEPARATOR := ---------------------------------------------------------------------------------
.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:+.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN { FS = "[:#]" } ; { printf "$(SEPARATOR)\n\033[36m%-22s\033[0m %s\n", $$1, $$4 }' ; \
	echo $(SEPARATOR)

.PHONY: build
build:  ## Build the ecosystems validation code with cargo 
	cargo build

.PHONY: validate
validate:  ## Validate the ecosystems toml files 
	cargo run --release -- validate data/ecosystems

.PHONY: sort
sort:  ## Sort and clean up unsorted toml files
	cargo run --release -- sort data/
