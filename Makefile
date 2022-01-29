## help commands:

help: ## show this help
	@awk -f ./tools/help.awk $(MAKEFILE_LIST)

## style commands:

PY_FILES = $(shell find . -type f -name '*.py'   | grep -f ./tools/style.py.include | grep -v -f ./tools/style.py.exclude )
C_FILES =  $(shell find . -type f -name '*.[ch]' | grep -f ./tools/style.c.include  | grep -v -f ./tools/style.c.exclude )


style_check: pystyle_check ruststyle_check cstyle_check changelog_check yaml_check editor_check ## run all style checks

style: pystyle ruststyle cstyle ## apply all code styles (C+Rust+Py)

pystyle_check: ## run code style check on application sources and tests
	flake8 --version
	isort --version | awk '/VERSION/{print $$2}'
	black --version
	mypy --version
	pylint --version
	@echo [MYPY]
	@make -C core mypy
	@echo [FLAKE8]
	@flake8 $(PY_FILES)
	@echo [ISORT]
	@isort --check-only $(PY_FILES)
	@echo [BLACK]
	@black --check $(PY_FILES)
	@echo [PYLINT]
	@pylint $(PY_FILES)
	@echo [PYTHON]
	make -C python style_check

pystyle: ## apply code style on application sources and tests
	@echo [ISORT]
	@isort $(PY_FILES)
	@echo [BLACK]
	@black $(PY_FILES)
	@echo [MYPY]
	@make -C core mypy
	@echo [FLAKE8]
	@flake8 $(PY_FILES)
	@echo [PYLINT]
	@pylint $(PY_FILES)
	@echo [PYTHON]
	make -C python style

changelog_check: ## check changelog format
	./tools/generate-changelog.py --check core
	./tools/generate-changelog.py --check core/embed/boardloader
	./tools/generate-changelog.py --check core/embed/bootloader
	./tools/generate-changelog.py --check core/embed/bootloader_ci
	./tools/generate-changelog.py --check legacy/bootloader
	./tools/generate-changelog.py --check legacy/firmware
	./tools/generate-changelog.py --check legacy/intermediate_fw
	./tools/generate-changelog.py --check python

yaml_check: ## check yaml formatting
	yamllint .

editor_check: ## check editorconfig formatting
	editorconfig-checker -exclude '.*\.(so|dat|toif|der)'

cstyle_check: ## run code style check on low-level C code
	clang-format --version
	@echo [CLANG-FORMAT]
	@./tools/clang-format-check $(C_FILES)

cstyle: ## apply code style on low-level C code
	@echo [CLANG-FORMAT]
	@clang-format -i $(C_FILES)

defs_check: ## check validity of coin definitions and protobuf files
	jsonlint common/defs/*.json common/defs/*/*.json
	python3 common/tools/cointool.py check
	python3 common/tools/support.py check
	python3 common/protob/check.py
	python3 common/protob/graph.py common/protob/*.proto

ruststyle:
	@echo [RUSTFMT]
	@cd core/embed/rust ; cargo fmt

ruststyle_check:
	rustfmt --version
	@echo [RUSTFMT]
	@cd core/embed/rust ; cargo fmt -- --check

## code generation commands:

mocks: ## generate mock python headers from C modules
	./core/tools/build_mocks

mocks_check: ## check validity of mock python headers
	./core/tools/build_mocks --check
	flake8 core/mocks/generated

templates: icons ## rebuild coin lists from definitions in common
	./core/tools/build_templates

templates_check: ## check that coin lists are up to date
	./core/tools/build_templates --check

icons: ## generate FIDO service icons
	python3 core/tools/build_icons.py

icons_check: ## generate FIDO service icons
	python3 core/tools/build_icons.py --check

protobuf: ## generate python protobuf headers
	./tools/build_protobuf

protobuf_check: ## check that generated protobuf headers are up to date
	./tools/build_protobuf --check

gen:  mocks icons templates protobuf ## regeneate auto-generated files from sources

gen_check: mocks_check icons_check templates_check protobuf_check ## check validity of auto-generated files
