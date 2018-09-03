PYTHON=python3
SETUP=$(PYTHON) setup.py

EXCLUDES=.vscode
STYLE_TARGETS=trezorlib trezorctl setup.py
EXCLUDE_TARGETS=trezorlib/messages

all: build

build:
	$(SETUP) build

install:
	$(SETUP) install

clean:
	git clean -dfx -e $(EXCLUDES)

style:
	black $(STYLE_TARGETS)
	isort --apply --recursive $(STYLE_TARGETS) --skip-glob "*/$(EXCLUDE_TARGETS)/*"
	autoflake -i --remove-all-unused-imports -r $(STYLE_TARGETS) --exclude "$(EXCLUDE_TARGETS)"

stylecheck:
	black --check $(STYLE_TARGETS)
	isort --diff --check-only --recursive $(STYLE_TARGETS) --skip-glob "*/$(EXCLUDE_TARGETS)/*"
	flake8

.PHONY: all build install clean style stylecheck
