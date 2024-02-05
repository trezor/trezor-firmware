## help commands:

help: ## show this help
	@awk -f ./tools/help.awk $(MAKEFILE_LIST)

## style commands:

PY_FILES = $(shell find . -type f -name '*.py'   | sed 'sO^\./OO' | grep -f ./tools/style.py.include | grep -v -f ./tools/style.py.exclude )
C_FILES =  $(shell find . -type f -name '*.[ch]' | grep -f ./tools/style.c.include  | grep -v -f ./tools/style.c.exclude )


style_check: pystyle_check ruststyle_check cstyle_check changelog_check yaml_check docs_summary_check editor_check ## run all style checks

style: pystyle ruststyle cstyle ## apply all code styles (C+Rust+Py)

pystyle_check: ## run code style check on application sources and tests
	flake8 --version
	isort --version | awk '/VERSION/{print $$2}'
	black --version
	pylint --version
	pyright --version
	@echo [TYPECHECK]
	@make -C core typecheck
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

pystyle_quick_check: ## run the basic style checks, suitable for a quick git hook
	@isort --check-only $(PY_FILES)
	@black --check $(PY_FILES)
	make -C python style_quick_check

pystyle: ## apply code style on application sources and tests
	@echo [ISORT]
	@isort $(PY_FILES)
	@echo [BLACK]
	@black $(PY_FILES)
	@echo [TYPECHECK]
	@make -C core typecheck
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
	@cd rust/trezor-client ; cargo fmt

ruststyle_check:
	rustfmt --version
	@echo [RUSTFMT]
	@cd core/embed/rust ; cargo fmt -- --check
	@cd rust/trezor-client ; cargo fmt -- --check

python_support_check:
	./tests/test_python_support.py

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

solana_templates: ## rebuild Solana instruction template file
	./core/tools/build_solana_templates

solana_templates_check: ## check that Solana instruction template file is up to date
	./core/tools/build_solana_templates --check

icons: ## generate FIDO service icons
	python3 core/tools/build_icons.py

icons_check: ## generate FIDO service icons
	python3 core/tools/build_icons.py --check

protobuf: ## generate python and rust protobuf headers
	./tools/build_protobuf
	./rust/trezor-client/scripts/build_protos

protobuf_check: ## check that generated protobuf headers are up to date
	./tools/build_protobuf --check
	./rust/trezor-client/scripts/build_protos --check

ci_docs: ## generate CI documentation
	./tools/generate_ci_docs.py

ci_docs_check: ## check that generated CI documentation is up to date
	./tools/generate_ci_docs.py --check

docs_summary_check: ## check if there are unlinked documentation files
	@echo [DOCS-SUMMARY-MARKDOWN-CHECK]
	python3 tools/check_docs_summary.py

vendorheader: ## generate vendor header
	./core/embed/vendorheader/generate.sh --quiet

vendorheader_check: ## check that vendor header is up to date
	./core/embed/vendorheader/generate.sh --quiet --check

gen:  templates mocks icons protobuf ci_docs vendorheader solana_templates ## regenerate auto-generated files from sources

gen_check: templates_check mocks_check icons_check protobuf_check ci_docs_check vendorheader_check solana_templates_check ## check validity of auto-generated files
