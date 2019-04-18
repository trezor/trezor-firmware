## help commands:

help: ## show this help
	@awk -f ./tools/help.awk $(MAKEFILE_LIST)

## style commands:

style_check: ## run code style check on application sources and tests
	flake8 --version
	isort --version | awk '/VERSION/{print $$2}'
	black --version
	flake8 $(shell find -type f -name '*.py' | grep -f ./tools/style.py.include | grep -v -f ./tools/style.py.exclude )
	isort --check-only $(shell find -type f -name '*.py' | grep -f ./tools/style.py.include | grep -v -f ./tools/style.py.exclude )
	black --check $(shell find -type f -name '*.py' | grep -f ./tools/style.py.include | grep -v -f ./tools/style.py.exclude )

style: ## apply code style on application sources and tests
	isort $(shell find -type f -name '*.py' | grep -f ./tools/style.py.include | grep -v -f ./tools/style.py.exclude )
	black $(shell find -type f -name '*.py' | grep -f ./tools/style.py.include | grep -v -f ./tools/style.py.exclude )

cstyle_check: ## run code style check on low-level C code
	./tools/clang-format-check $(shell find -type f -name '*.c' -o -name '*.h' | grep -f ./tools/style.c.include | grep -v -f ./tools/style.c.exclude )

cstyle: ## apply code style on low-level C code
	clang-format -i $(shell find -type f -name '*.c' -o -name '*.h' | grep -f ./tools/style.c.include | grep -v -f ./tools/style.c.exclude )
