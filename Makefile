## help commands:

help: ## show this help
	@awk -f ./tools/help.awk $(MAKEFILE_LIST)

## style commands:

PY_FILES = $(shell find -type f -name '*.py'   | grep -f ./tools/style.py.include | grep -v -f ./tools/style.py.exclude )
C_FILES =  $(shell find -type f -name '*.[ch]' | grep -f ./tools/style.c.include  | grep -v -f ./tools/style.c.exclude )


style_check: ## run code style check on application sources and tests
	flake8 --version
	isort --version | awk '/VERSION/{print $$2}'
	black --version
	flake8 $(PY_FILES)
	isort --check-only $(PY_FILES)
	black --check $(PY_FILES)
	make -C python style_check

style: ## apply code style on application sources and tests
	isort $(PY_FILES)
	black $(PY_FILES)
	make -C python style

cstyle_check: ## run code style check on low-level C code
	./tools/clang-format-check $(C_FILES)

cstyle: ## apply code style on low-level C code
	clang-format -i $(C_FILES)
