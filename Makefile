# Project metadata obtained via setuptools to keep commands in sync.
NAME := $(shell python3 -B setup.py --name)
VERSION := $(shell python3 -B setup.py --version)
DIST_DIR := dist
ARCHIVE := $(DIST_DIR)/$(NAME)-$(VERSION).tar.gz
WHEEL := $(shell ls $(DIST_DIR)/$(NAME)-$(VERSION)-*.whl 2>/dev/null | head -n 1)


.PHONY: all help test lint build clean install archive coverage docs preview-docs
.DEFAULT_GOAL := help


help:
	@echo "Common targets:"
	@echo "  make test     - run unit tests via tox"
	@echo "  make coverage - run coverage across standard and compat test envs"
	@echo "  make flake8   - run flake8 via tox"
	@echo "  make build    - build wheel and sdist via tox"
	@echo "  make docs     - build Sphinx documentation via tox"
	@echo "  make preview-docs - serve built docs locally"
	@echo "  make install  - install the built wheel into the current user environment"
	@echo "  make archive  - create a source archive from git"
	@echo "  make clean    - remove build artifacts"


test:
	@tox -qe py


flake8:
	@tox -qe flake8


coverage:
	@tox -qe py-cover
	@tox -qe compat-cover
	@tox -qe coverage-report


build:
	@tox -qe build


docs:
	@tox -qe py-cover
	@tox -qe compat-cover
	@tox -qe coverage-report
	@tox -qe docs


preview-docs: docs
	@python3 -B -m http.server -d build/docs -b 127.0.0.1 8000


install: build
	@python3 -B -m pip install --user "$(WHEEL)"


archive:
	@mkdir -p $(DIST_DIR)
	@git archive --format=tar.gz --prefix=$(NAME)-$(VERSION)/ HEAD > "$(ARCHIVE)"
	@echo "Archive written to $(ARCHIVE)"


clean:
	rm -rf $(DIST_DIR) build *.egg-info .tox


# The end.
