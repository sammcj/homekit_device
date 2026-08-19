VENV := .venv
VENV_PY := $(VENV)/bin/python
PYTHON_VERSION := 3.13
UV := $(shell command -v uv 2>/dev/null)

# Use the virtualenv's tools when there is one, otherwise whatever is on PATH.
# CI installs the dependencies directly, so it takes the second branch and runs
# the same `make check` a contributor does rather than a second copy of it.
#
# These are the console scripts on purpose, not `python -m pytest`. The `-m`
# form prepends the working directory to sys.path, and the repo root holds
# select.py (platform modules are named for their HA domain). On Linux `select`
# is a shared object rather than a builtin, so that shadows the stdlib module
# and `import subprocess` fails inside pytest's own startup.
RUFF := $(shell [ -x $(VENV)/bin/ruff ] && echo $(VENV)/bin/ruff || echo ruff)
PYTEST := $(shell [ -x $(VENV)/bin/pytest ] && echo $(VENV)/bin/pytest || echo pytest)

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
	$(RUFF) check .

test:
	# PYTHONSAFEPATH stops Python prepending a path entry of its own, so this
	# target is safe even if PYTEST resolves to something invoked as a module.
	PYTHONSAFEPATH=1 $(PYTEST)

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
