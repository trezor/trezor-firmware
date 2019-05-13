## help commands:

help: ## show this help
	@awk -f ./tools/help.awk $(MAKEFILE_LIST)

## style commands:

PY_FILES = $(shell find . -type f -name '*.py'   | grep -f ./tools/style.py.include | grep -v -f ./tools/style.py.exclude )
C_FILES =  $(shell find . -type f -name '*.[ch]' | grep -f ./tools/style.c.include  | grep -v -f ./tools/style.c.exclude )


style_check: pystyle_check cstyle_check

style: pystyle cstyle

pystyle_check: ## run code style check on application sources and tests
	flake8 --version
	isort --version | awk '/VERSION/{print $$2}'
	black --version
	@echo [FLAKE8]
	@flake8 $(PY_FILES)
	@echo [ISORT]
	@isort --check-only $(PY_FILES)
	@echo [BLACK]
	@black --check $(PY_FILES)
	make -C python style_check

pystyle: ## apply code style on application sources and tests
	@echo [ISORT]
	@isort $(PY_FILES)
	@echo [BLACK]
	@black $(PY_FILES)
	make -C python style

cstyle_check: ## run code style check on low-level C code
	@echo [CLANG-FORMAT]
	@./tools/clang-format-check $(C_FILES)

cstyle: ## apply code style on low-level C code
	@echo [CLANG-FORMAT]
	@clang-format -i $(C_FILES)

defs_check: ## check validity of coin definitions and protobuf files
	jsonlint common/defs/*.json common/defs/*/*.json
	python3 common/tools/cointool.py check
	python3 common/tools/support.py check --ignore-missing
	python3 common/protob/check.py
	python3 common/protob/graph.py common/protob/*.proto
