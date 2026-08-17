.PHONY: help \
	style_check style \
	pystyle_check pystyle_quick_check pystyle \
	changelog_check changelog_style \
	translations_style translations_style_check \
	yaml_check editor_check \
	cstyle_check cstyle \
	protostyle protostyle_check \
	defs_check \
	ruststyle ruststyle_check \
	sdk_fmt sdk_fmt_check \
	sdk_check sdk_clippy \
	sdk_test sdk_doctest sdk_doc \
	sdk_audit sdk_vet \
	modular_xtask_fmt modular_xtask_fmt_check \
	modular_xtask_check modular_xtask_clippy \
	modular_xtask_test modular_xtask_doctest modular_xtask_doc \
	modular_xtask_audit modular_xtask_vet \
	extapp_build_firmware extapp_build_emu \
	extapp_unit_tests extapp_test_emu extapp_test_emu_ui \
	extapp_fmt extapp_fmt_check \
	extapp_py_style extapp_py_style_check \
	extapp_translation_style extapp_translation_style_check \
	extapp_clippy extapp_vet \
	typecheck pyright \
	mocks mocks_check \
	templates templates_check \
	solana_templates solana_templates_check \
	icons icons_check \
	protobuf protobuf_check \
	docs_summary_check \
	vendorheader vendorheader_check \
	bootloader_hashes bootloader_hashes_check \
	lsgen lsgen_check \
	tropic_config tropic_config_check \
	hsm_keys hsm_keys_check \
	prodtest_error_codes prodtest_error_codes_check \
	certs certs_check \
	python_doc python_doc_check \
	gen gen_check \
	uvlock_check

## help commands:

help: ## show this help
	@awk -f ./tools/help.awk $(MAKEFILE_LIST)

## style commands:

PY_FILES = $(shell find . -type f -name '*.py'   | sed 'sO^\./OO' | grep -f ./tools/style.py.include | grep -v -f ./tools/style.py.exclude ) common/protob/pb2py
C_FILES =  $(shell find . -type f -name '*.[ch]' | grep -f ./tools/style.c.include  | grep -v -f ./tools/style.c.exclude )
PROTO_FILES = $(shell find common core sdk -type f -name '*.proto')
RUST_CRATES = $(shell find core -type f -name Cargo.toml -printf "%h\n")

# suppress black's warning - remove when using Python 3.14
BLACK_FAST ?= 1

ifeq ($(BLACK_FAST),1)
BLACK_FLAGS=--fast
else
BLACK_FLAGS=
endif

style_check: pystyle_check ruststyle_check cstyle_check protostyle_check changelog_check translations_style_check yaml_check docs_summary_check editor_check ## run all style checks

style: pystyle ruststyle cstyle protostyle changelog_style translations_style ## apply all code styles (Python+Rust+C+protobuf+changelog+translation JSON)

pystyle_check: ## run code style check on application sources and tests
	flake8 --version
	isort --version | awk '/VERSION/{print $$2}'
	black --version
	pylint --version
	pyright --version
	@echo [TYPECHECK]
	@make -C core typecheck
	@echo [TYPECHECK - COMMON and TOOLS]
	@make typecheck
	@echo [FLAKE8]
	@flake8 $(PY_FILES)
	@echo [ISORT]
	@isort --check-only $(PY_FILES)
	@echo [BLACK]
	@black --check $(BLACK_FLAGS) $(PY_FILES)
	@echo [PYLINT]
	@pylint $(PY_FILES)
	@echo [PYTHON]
	make -C python style_check BLACK_FLAGS=$(BLACK_FLAGS)
	EXTAPP=ethereum make extapp_py_style_check
	EXTAPP=tron make extapp_py_style_check

pystyle_quick_check: ## run the basic style checks, suitable for a quick git hook
	@isort --check-only $(PY_FILES)
	@black --check $(BLACK_FLAGS) $(PY_FILES)
	make -C python style_quick_check BLACK_FLAGS=$(BLACK_FLAGS)

pystyle: ## apply code style on application sources and tests
	@echo [ISORT]
	@isort $(PY_FILES)
	@echo [BLACK]
	@black $(BLACK_FLAGS) $(PY_FILES)
	@echo [TYPECHECK]
	@make -C core typecheck
	@echo [TYPECHECK - COMMON and TOOLS]
	@make typecheck
	@echo [FLAKE8]
	@flake8 $(PY_FILES)
	@echo [PYLINT]
	@pylint $(PY_FILES)
	@echo [PYTHON]
	make -C python style BLACK_FLAGS=$(BLACK_FLAGS)
	EXTAPP=ethereum make extapp_py_style
	EXTAPP=tron make extapp_py_style

changelog_check: ## check changelog format
	@echo [CHANGELOG-CHECK]
	./tools/changelog.py check

changelog_style: ## fix changelog format
	@echo [CHANGELOG-STYLE]
	./tools/changelog.py style

translations_style: ## Format translation files
	@echo [TRANSLATIONS-STYLE]
	@./core/tools/translations/sort_keys.py
	EXTAPP=ethereum make extapp_translation_style
	EXTAPP=tron make extapp_translation_style

translations_style_check: ## Check that translation files are properly formatted
	@echo [TRANSLATIONS-STYLE-CHECK]
	@./core/tools/translations/sort_keys.py check
	EXTAPP=ethereum make extapp_translation_style_check
	EXTAPP=tron make extapp_translation_style_check

yaml_check: ## check yaml formatting
	@echo [YAML-STYLE-CHECK]
	yamllint --strict .

editor_check: ## check editorconfig formatting
	@echo [EDITORCONFIG-STYLE-CHECK]
	editorconfig-checker -exclude '.*\.(so|dat|toif|der)|^crypto/aes/'

cstyle_check: ## run code style check on low-level C code
	clang-format --version
	@echo [CLANG-FORMAT]
	@./tools/clang-format-check $(C_FILES)

cstyle: ## apply code style on low-level C code
	@echo [CLANG-FORMAT]
	@clang-format -i $(C_FILES)

protostyle: ## Format protobuf definitions
	@echo [PROTOBUF-STYLE]
	@clang-format -i $(PROTO_FILES)

protostyle_check: ## Check that protobuf definitions are properly formatted
	@echo [PROTOBUF-STYLE-CHECK]
	clang-format --version
	@./tools/clang-format-check $(PROTO_FILES)

defs_check: ## check validity of coin definitions and protobuf files
	jsonlint common/defs/*.json common/defs/*/*.json
	python3 common/tools/cointool.py check
	python3 common/tools/support.py check
	python3 common/protob/check.py
	python3 common/protob/graph.py common/protob/*.proto

ruststyle: ## apply code style on rust sources
	@echo [RUSTFMT]
	@cd core/embed ; cargo fmt
	make -C rust style
	make extapp_fmt
	make modular_xtask_fmt
	make sdk_fmt

ruststyle_check: ## run code style check on rust sources
	@echo [RUSTFMT]
	@cd core/embed ; cargo fmt -- --check
	make -C rust style_check
	make extapp_fmt_check
	make modular_xtask_fmt_check
	make sdk_fmt_check

## sdk commands:

sdk_fmt: ## apply code style on the trezor-app-sdk crate
	@echo [SDK-RUSTFMT]
	@cd sdk/crates/trezor-app-sdk ; cargo fmt

sdk_fmt_check: ## run code style check on the trezor-app-sdk crate
	@echo [SDK-RUSTFMT]
	@cd sdk/crates/trezor-app-sdk ; cargo fmt -- --check

sdk_check: ## run cargo check on the trezor-app-sdk crate across its feature sets
	@echo [SDK-CHECK]
	@cd sdk/crates/trezor-app-sdk ; cargo check
	@cd sdk/crates/trezor-app-sdk ; cargo check --no-default-features
	@cd sdk/crates/trezor-app-sdk ; cargo check --features debug
	@cd sdk/crates/trezor-app-sdk ; cargo check --features test
	@cd sdk/crates/trezor-app-sdk ; cargo check --all-features

sdk_clippy: ## run clippy on the trezor-app-sdk crate
	@echo [SDK-CLIPPY]
	@cd sdk/crates/trezor-app-sdk ; cargo clippy --no-default-features
	@cd sdk/crates/trezor-app-sdk ; cargo clippy --all-features

sdk_test: ## run unit tests for the trezor-app-sdk crate
	@echo [SDK-TEST]
	@cd sdk/crates/trezor-app-sdk ; cargo test --lib --features test

sdk_doctest: ## run doc tests for the trezor-app-sdk crate
	@echo [SDK-DOCTEST]
	@cd sdk/crates/trezor-app-sdk ; cargo test --doc --features test

sdk_doc: ## build documentation for the trezor-app-sdk crate
	@echo [SDK-DOC]
	@cd sdk/crates/trezor-app-sdk ; cargo doc --no-deps --all-features

sdk_audit: ## run cargo audit on the trezor-app-sdk crate's dependencies
	@echo [SDK-AUDIT]
	@cd sdk/crates/trezor-app-sdk ; cargo audit

sdk_vet: ## run cargo vet on the trezor-app-sdk crate's dependencies
	@echo [SDK-VET]
	@cd sdk/crates/trezor-app-sdk ; cargo vet --locked

## modular-xtask commands:

modular_xtask_fmt: ## apply code style on the modular-xtask crate
	@echo [MODULAR-XTASK-RUSTFMT]
	@cd sdk/crates/modular-xtask ; cargo fmt

modular_xtask_fmt_check: ## run code style check on the modular-xtask crate
	@echo [MODULAR-XTASK-RUSTFMT]
	@cd sdk/crates/modular-xtask ; cargo fmt -- --check

modular_xtask_check: ## run cargo check on the modular-xtask crate
	@echo [MODULAR-XTASK-CHECK]
	@cd sdk/crates/modular-xtask ; cargo check --all-targets

modular_xtask_clippy: ## run clippy on the modular-xtask crate
	@echo [MODULAR-XTASK-CLIPPY]
	@cd sdk/crates/modular-xtask ; cargo clippy --all-targets

modular_xtask_test: ## run unit tests for the modular-xtask crate
	@echo [MODULAR-XTASK-TEST]
	@cd sdk/crates/modular-xtask ; cargo test --lib

modular_xtask_doctest: ## run doc tests for the modular-xtask crate
	@echo [MODULAR-XTASK-DOCTEST]
	@cd sdk/crates/modular-xtask ; cargo test --doc

modular_xtask_doc: ## build documentation for the modular-xtask crate
	@echo [MODULAR-XTASK-DOC]
	@cd sdk/crates/modular-xtask ; cargo doc --no-deps

modular_xtask_audit: ## run cargo audit on the modular-xtask crate's dependencies
	@echo [MODULAR-XTASK-AUDIT]
	@cd sdk/crates/modular-xtask ; cargo audit

modular_xtask_vet: ## run cargo vet on the modular-xtask crate's dependencies
	@echo [MODULAR-XTASK-VET]
	@cd sdk/crates/modular-xtask ; cargo vet --locked

## extapp commands:

EXTAPP ?= tron
EXTAPP_MODEL ?= t3w1
EXTAPP_LANG ?= en

# Same emulator-running setup as core/Makefile, so extapp device tests behave
# the same way as core's own (see core/Makefile's own TREZOR_MODEL/EMU/etc.).
TREZOR_MODEL ?= T3W1
PYTEST_TIMEOUT ?= 500
TEST_LANG ?= "en"

EMU = core/emu.py
EMU_LOG_FILE ?= tests/trezor.log
EMU_TEST_ARGS = --disable-animation --headless --output=$(EMU_LOG_FILE) --temporary-profile
EMU_TEST = $(EMU) $(EMU_TEST_ARGS) -c

extapp_build_firmware: ## build an extapp's firmware (set EXTAPP/EXTAPP_MODEL/EXTAPP_LANG)
	@echo [EXTAPP-BUILD-FIRMWARE]
	@xtask modular build -p $(EXTAPP) -m $(EXTAPP_MODEL) --lang $(EXTAPP_LANG)

extapp_build_emu: ## build an extapp's emulator (set EXTAPP/EXTAPP_MODEL/EXTAPP_LANG)
	@echo [EXTAPP-BUILD-EMU]
	@xtask modular build -p $(EXTAPP) -m $(EXTAPP_MODEL) --lang $(EXTAPP_LANG) -e

extapp_unit_tests: ## run unit tests for an extapp (set EXTAPP/EXTAPP_MODEL/EXTAPP_LANG)
	@echo [EXTAPP-UNIT-TESTS]
	@xtask modular unit-tests -p $(EXTAPP) -m $(EXTAPP_MODEL) --lang $(EXTAPP_LANG)

extapp_test_emu: ## run device tests for an extapp against a universal firmware emulator (set EXTAPP/EXTAPP_MODEL/TEST_LANG)
	@echo [EXTAPP-TEST-EMU]
	$(EMU_TEST) xtask modular device-tests -p $(EXTAPP) -m $(EXTAPP_MODEL) -e --lang $(TEST_LANG)

extapp_test_emu_ui: ## run device tests with UI screenshot testing for an extapp against a universal firmware emulator (set EXTAPP/EXTAPP_MODEL/TEST_LANG)
	@echo [EXTAPP-TEST-EMU-UI]
	$(EMU_TEST) xtask modular device-tests -p $(EXTAPP) -m $(EXTAPP_MODEL) -e --ui --lang $(TEST_LANG)

extapp_fmt: ## apply code style on all extapps
	@echo [EXTAPP-RUSTFMT]
	@xtask modular fmt

extapp_fmt_check: ## run code style check on all extapps
	@echo [EXTAPP-RUSTFMT]
	@xtask modular fmt-check

extapp_py_style: ## apply python style on an extapp's tests (set EXTAPP)
	@echo [EXTAPP-PYSTYLE]
	@xtask modular py-style -p $(EXTAPP)

extapp_py_style_check: ## run python style check on an extapp's tests (set EXTAPP)
	@echo [EXTAPP-PYSTYLE-CHECK]
	@xtask modular py-style-check -p $(EXTAPP)

extapp_translation_style: ## apply translation style on an extapp (set EXTAPP)
	@echo [EXTAPP-TRANSLATION-STYLE]
	@xtask modular translation-style -p $(EXTAPP)

extapp_translation_style_check: ## check translation style on an extapp (set EXTAPP)
	@echo [EXTAPP-TRANSLATION-STYLE-CHECK]
	@xtask modular translation-style-check -p $(EXTAPP)

extapp_clippy: ## run clippy on an extapp (set EXTAPP/EXTAPP_MODEL/EXTAPP_LANG)
	@echo [EXTAPP-CLIPPY]
	@xtask modular clippy -p $(EXTAPP) -m $(EXTAPP_MODEL) --lang $(EXTAPP_LANG)

extapp_vet: ## run cargo vet on all extapps' dependencies
	@echo [EXTAPP-VET]
	@cd sdk/apps ; cargo vet --locked

typecheck: pyright

pyright:
	python ./tools/pyright_tool.py

## code generation commands:

mocks: ## generate mock python headers from C modules
	./core/tools/build_mocks

mocks_check: ## check validity of mock python headers
	./core/tools/build_mocks --check
	flake8 core/mocks/generated

templates: icons ## rebuild coin lists from definitions in common
	make -C core templates

templates_check: ## check that coin lists are up to date
	make -C core templates_check

solana_templates: ## rebuild Solana instruction template file
	python tools/build_solana_templates.py

solana_templates_check: ## check that Solana instruction template file is up to date
	python tools/build_solana_templates.py --check

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

docs_summary_check: ## check if there are unlinked documentation files
	@echo [DOCS-SUMMARY-MARKDOWN-CHECK]
	python3 tools/check_docs_summary.py

vendorheader: ## generate vendor header
	./core/tools/generate_vendorheader.sh --quiet

vendorheader_check: ## check that vendor header is up to date
	./core/tools/generate_vendorheader.sh --quiet --check

bootloader_hashes: ## generate bootloader hashes
	bootloader_hashes

bootloader_hashes_check: ## check generated bootloader hashes
	bootloader_hashes --check

lsgen: ## generate linker scripts
	lsgen

lsgen_check: ## check generated linker scripts
	lsgen --check

tropic_config:
	./core/tools/generate_tropic_model_config.py
	./core/tools/generate_tropic_config_docs.py

tropic_config_check:
	./core/tools/generate_tropic_model_config.py --check
	./core/tools/generate_tropic_config_docs.py --check

hsm_keys:
	./core/tools/generate_hsm_keys.py

hsm_keys_check:
	./core/tools/generate_hsm_keys.py --check

prodtest_error_codes: ## generate prodtest error codes JSON
	python3 core/tools/prodtest_error_codes.py

prodtest_error_codes_check: ## check prodtest error codes JSON is up to date
	python3 core/tools/prodtest_error_codes.py --check

certs:
	./core/tools/generate_certificates.py

certs_check:
	./core/tools/generate_certificates.py --check

python_doc: ## generate trezorctl OPTIONS.rst
	make -C python doc

python_doc_check: ## check that trezorctl OPTIONS.rst is up to date
	make -C python doc_check

gen:  templates mocks icons protobuf vendorheader solana_templates bootloader_hashes lsgen tropic_config hsm_keys prodtest_error_codes certs python_doc ## regenerate auto-generated files from sources

gen_check: templates_check mocks_check icons_check protobuf_check vendorheader_check solana_templates_check bootloader_hashes_check lsgen_check tropic_config_check hsm_keys_check prodtest_error_codes_check certs_check python_doc_check ## check validity of auto-generated files

api:
	@echo [API-BINDINGS]
	xtask api-bindings

api_check:
	@echo [API-BINDINGS-CHECK]
	xtask api-bindings --check-only

uvlock_check: ## check that uv.lock is up to date
	@echo [UVLOCK-CHECK]
	uv lock --check
