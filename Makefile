VENV := .venv
VENV_PY := $(VENV)/bin/python
PYTHON_VERSION := 3.13
UV := $(shell command -v uv 2>/dev/null)

# Use the virtualenv when there is one, otherwise whatever python is on PATH.
# CI installs the dependencies directly, so it takes the second branch and runs
# the same `make check` a contributor does rather than a second copy of it.
PY := $(shell [ -x $(VENV_PY) ] && echo $(VENV_PY) || echo python3)

DOMAIN := $(shell sed -n 's/.*"domain": *"\([^"]*\)".*/\1/p' manifest.json)

# Files that belong in a Home Assistant install, as opposed to this repo. An
# allowlist rather than a set of excludes, so a new dev-only file at the root
# does not silently start shipping.
DEPLOY_PATHS := $(wildcard *.py) manifest.json services.yaml translations

# Where a Home Assistant config directory lives, for `make deploy`.
HA_CONFIG ?= /config

.PHONY: help install lint test check deploy clean

help:
	@echo "install  Create $(VENV) and install the test and lint dependencies"
	@echo "lint     Run ruff over the integration and the tests"
	@echo "test     Run the test suite"
	@echo "check    lint + test"
	@echo "deploy   Copy the integration into HA_CONFIG/custom_components (default $(HA_CONFIG))"
	@echo "clean    Remove the virtualenv and tool caches"

install:
ifdef UV
	uv venv --python $(PYTHON_VERSION) $(VENV)
	uv pip install --python $(VENV_PY) -r requirements-test.txt
else
	python$(PYTHON_VERSION) -m venv $(VENV)
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r requirements-test.txt
endif

lint:
	$(PY) -m ruff check .

test:
	$(PY) -m pytest

check: lint test

# The repo root is the component, so it is copied to a directory named after
# the domain rather than installed as a package.
deploy:
	@test -d "$(HA_CONFIG)" || { echo "No such directory: $(HA_CONFIG)" >&2; exit 1; }
	mkdir -p "$(HA_CONFIG)/custom_components/$(DOMAIN)"
	rsync -a --delete $(DEPLOY_PATHS) "$(HA_CONFIG)/custom_components/$(DOMAIN)/"

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache
	find . -name '__pycache__' -prune -not -path './.venv/*' -exec rm -rf {} +
