
.PHONY: vendor

BUILD_DIR = build-xtask/artifacts/latest

TREZOR_MODEL ?= T3W1
PYTEST_TIMEOUT ?= 500
TEST_LANG ?= "en"
XTASK_BUILD_OPTS ?=

ifeq ($(PRODUCTION),1)
ifeq ($(BOOTLOADER_DEVEL),1)
$(error PRODUCTION and BOOTLOADER_DEVEL cannot be set at the same time)
# remove this check if you know what you are doing and need to build this way
endif
endif

TESTPATH = $(CURDIR)/../tests

EMU = $(CURDIR)/emu.py
EMU_LOG_FILE ?= $(TESTPATH)/trezor.log
EMU_TEST_ARGS = --disable-animation --headless --output=$(EMU_LOG_FILE) --temporary-profile
EMU_TEST = $(EMU) $(EMU_TEST_ARGS) -c

JUNIT_XML ?= $(TESTPATH)/junit.xml
PYTEST = pytest --junitxml=$(JUNIT_XML)
TREZOR_FIDO2_UDP_PORT = 21326

MULTICORE ?= "auto"
RANDOM=$(shell python -c 'import random; print(random.randint(0, 1000000))')

# Please only add options used by CI, otherwise just run xtask directly.
XTASK_BUILD_OPTS += --model $(TREZOR_MODEL)
ifeq ($(ADDRESS_SANITIZER),1)
XTASK_BUILD_OPTS += --asan
endif
ifeq ($(BITCOIN_ONLY),1)
XTASK_BUILD_OPTS += --btc-only
endif
ifeq ($(BOOTLOADER_DEVEL),1)
XTASK_BUILD_OPTS += --bootloader-devel
endif
ifeq ($(N4W1),1)
XTASK_BUILD_OPTS += --n4w1
endif
ifeq ($(PRODUCTION),1)
XTASK_BUILD_OPTS += --production
endif
ifeq ($(PYOPT),1)
XTASK_BUILD_OPTS += --pyopt true
else ifeq ($(PYOPT),0)
XTASK_BUILD_OPTS += --pyopt false
XTASK_BUILD_OPTS += --disable-animation
endif
ifeq ($(TREZOR_MEMPERF),1)
XTASK_BUILD_OPTS += --mem-perf
endif
ifeq ($(UNSAFE_FW),1)
XTASK_BUILD_OPTS += --unsafe-fw
endif

ifeq ($(STORAGE_INSECURE_TESTING_MODE),1)
XTASK_BUILD_OPTS += --storage-insecure-testing-mode
XTASK_BUILD_OPTS += --disable-tropic true
XTASK_BUILD_OPTS += --disable-optiga
else
	ifeq ($(DISABLE_OPTIGA),1)
	XTASK_BUILD_OPTS += --disable-optiga
	endif
	ifeq ($(DISABLE_TROPIC),1)
	XTASK_BUILD_OPTS += --disable-tropic true
	else ifeq ($(DISABLE_TROPIC),0)
	XTASK_BUILD_OPTS += --disable-tropic false
	endif
endif

## help commands:

help: ## show this help
	@awk -f ../tools/help.awk $(MAKEFILE_LIST)

## dependencies commands:

vendor: ## update git submodules
	git submodule update --init --recursive --force

## emulator commands:

run: ## run unix port
	cd src ; ../$(BUILD_DIR)/firmware-emu

emu: ## run emulator
	$(EMU)

## test commands:

test: ## run unit tests
	cd tests ; ./run_tests.sh $(TESTOPTS)

test_rust: ## run rs unit tests
	false # NOT IMPLEMENTED
	# xtask test crypto
	# xtask test all

test_emu_sanity: ## make sure the emulator doesn't crash on startup
	timeout -v 10 $(EMU) --disable-animation --headless --temporary-profile --command true

test_emu: ## run selected device tests from python-trezor
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/device_tests $(TESTOPTS) --lang=$(TEST_LANG)

test_emu_multicore: ## run device tests using multiple cores
	$(PYTEST) -n $(MULTICORE) $(TESTPATH)/device_tests $(TESTOPTS) --timeout $(PYTEST_TIMEOUT) \
		--control-emulators --model=core --random-order-seed=$(RANDOM) \
		--lang=$(TEST_LANG)

test_emu_monero: ## run selected monero device tests from monero-agent
	cd tests ; $(EMU_TEST) ./run_tests_device_emu_monero.sh $(TESTOPTS)

test_emu_u2f: ## run selected u2f device tests from u2f-tests-hid
	$(EMU_TEST) --slip0014 $(TESTPATH)/fido_tests/u2f-tests-hid/HIDTest $(TREZOR_FIDO2_UDP_PORT) $(TESTOPTS)
	$(EMU_TEST) --slip0014 $(TESTPATH)/fido_tests/u2f-tests-hid/U2FTest $(TREZOR_FIDO2_UDP_PORT) $(TESTOPTS)

test_emu_fido2: ## run fido2 device tests
	cd $(TESTPATH)/fido_tests/fido2 ; \
		$(EMU_TEST) --slip0014 $(PYTEST) --maxfail=5 --sim tests/standard/ --vendor trezor $(TESTOPTS)

test_emu_click: ## run click tests
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/click_tests $(TESTOPTS) --lang=$(TEST_LANG)

test_emu_click_ui: ## run click tests with UI testing
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/click_tests $(TESTOPTS) \
		--ui=test --ui-check-missing --do-master-diff --lang=$(TEST_LANG)

test_emu_click_ui_multicore: ## run click tests with UI testing using multiple cores
	$(PYTEST) -n $(MULTICORE) $(TESTPATH)/click_tests $(TESTOPTS) --timeout $(PYTEST_TIMEOUT) \
		--ui=test --ui-check-missing --do-master-diff --lang=$(TEST_LANG) \
		--control-emulators --model=core --random-order-seed=$(RANDOM)

test_emu_persistence: ## run persistence tests
	$(PYTEST) $(TESTPATH)/persistence_tests $(TESTOPTS) --lang=$(TEST_LANG)

test_emu_persistence_ui: ## run persistence tests with UI testing
	$(PYTEST) $(TESTPATH)/persistence_tests $(TESTOPTS) \
		--ui=test --ui-check-missing --do-master-diff --lang=$(TEST_LANG)

test_emu_ui: ## run ui integration tests
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/device_tests $(TESTOPTS) \
		--ui=test --ui-check-missing --do-master-diff \
		--lang=$(TEST_LANG)

test_emu_ui_multicore: ## run ui integration tests using multiple cores
	$(PYTEST) -n $(MULTICORE) $(TESTPATH)/device_tests $(TESTOPTS) --timeout $(PYTEST_TIMEOUT) \
		--ui=test --ui-check-missing --do-master-diff \
		--control-emulators --model=core --random-order-seed=$(RANDOM) \
		--lang=$(TEST_LANG)

test_emu_ui_record: ## record and hash screens for ui integration tests
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/device_tests $(TESTOPTS) \
		--ui=record --ui-check-missing --do-master-diff --lang=$(TEST_LANG)

test_emu_ui_record_multicore: ## quickly record all screens
	make test_emu_ui_multicore || echo "All errors are recorded in fixtures.json"
	../tests/update_fixtures.py local --remove-missing

pylint: ## run pylint on application sources and tests
	pylint -E $(shell find src tests -name *.py)

mypy: ## deprecated; use "make typecheck"
	@echo "mypy is deprecated; use 'make typecheck'"
	make typecheck

typecheck: pyright

pyright:
	python ../tools/pyright_tool.py

clippy:
	xtask clippy -e -m $(TREZOR_MODEL) bootloader
	xtask clippy -e -m $(TREZOR_MODEL) firmware

audit_rust: ## run cargo audit on rust dependencies
	cd embed ; cargo audit

## code generation:

templates: translations ## render Mako templates (for lists of coins, tokens, etc.)
	./tools/build_templates

templates_check: translations_check ## check that Mako-rendered files match their templates
	./tools/build_templates --check

translations: ## update translations
	python ./translations/order.py
	python ./translations/cli.py gen

translations_check: ## check that translations are up to date
	python ./translations/order.py --check
	python ./translations/cli.py gen --check
	# spits out error if the stored merkle root is not up to date
	python ./translations/cli.py merkle-root > /dev/null

translations_crowdin_push: translations  ## split translations and push to crowdin
	## prepare source files from joint `en.json` into split `en_<layout_type>.json`
	cd translations; python crowdin.py split
	cd translations; crowdin push sources

translations_crowdin_pull: ## pull translations from crowdin
	cd translations; crowdin pull --skip-untranslated-strings
	# prepare joint `<lang>.json` from split `<lang>_<layout_type>.json`
	cd translations; python crowdin.py merge

## build commands:

build: build_boardloader build_bootloader build_firmware build_prodtest build_unix ## build all

build_embed: build_boardloader build_bootloader build_firmware # build boardloader, bootloader, firmware

build_boardloader: ## build boardloader
	xtask build boardloader $(XTASK_BUILD_OPTS)

build_bootloader: ## build bootloader
	xtask build bootloader $(XTASK_BUILD_OPTS)

build_bootloader_ci: ## build CI device testing bootloader
	xtask build bootloader_ci $(XTASK_BUILD_OPTS)

build_bootloader_emu: ## build the unix bootloader emulator
	xtask build bootloader --emulator $(XTASK_BUILD_OPTS)

build_bootloader_emu_debug: ## build the unix bootloader emulator
	xtask build bootloader --debug true --emulator $(XTASK_BUILD_OPTS)

build_prodtest: ## build production test firmware
	xtask build prodtest $(XTASK_BUILD_OPTS)

build_prodtest_emu: ## build the unix prodtest emulator
	xtask build prodtest --emulator $(XTASK_BUILD_OPTS)

build_secmon: ## build security monitor image
	xtask build secmon $(XTASK_BUILD_OPTS)

build_firmware: ## build firmware with frozen modules
	xtask build firmware $(XTASK_BUILD_OPTS)

build_unix: ## build unix port
	xtask build firmware --emulator $(XTASK_BUILD_OPTS) --pyopt=false

build_unix_frozen: ## build unix port with frozen modules
	xtask build firmware --emulator --frozen $(XTASK_BUILD_OPTS)

build_unix_debug: ## build unix port
	xtask build firmware --emulator --asan --debug true $(XTASK_BUILD_OPTS)

## clean commands:

clean: ## clean all
	xtask clean

## flash commands:

flash: flash_boardloader flash_bootloader flash_firmware ## flash everything using OpenOCD

flash_boardloader: ## flash boardloader using OpenOCD
	xtask flash --model $(TREZOR_MODEL) boardloader

flash_bootloader: ## flash bootloader using OpenOCD
	xtask flash --model $(TREZOR_MODEL) bootloader

flash_bootloader_ci: ## flash CI bootloader using OpenOCD
	xtask flash --model $(TREZOR_MODEL) bootloader_ci

flash_prodtest: ## flash prodtest using OpenOCD
	xtask flash --model $(TREZOR_MODEL) prodtest

flash_firmware: ## flash firmware using OpenOCD
	xtask flash --model $(TREZOR_MODEL) firmware

flash_erase: ## erase all sectors in flash bank 0
	xtask flash-erase --model $(TREZOR_MODEL) all

flash_erase_bootloader: ## erase bootloader
	xtask flash-erase --model $(TREZOR_MODEL) bootloader

flash_erase_firmware: ## erase bootloader
	xtask flash-erase --model $(TREZOR_MODEL) firmware

flash_erase_storage: ## erase storage sectors from flash
	xtask flash-erase --model $(TREZOR_MODEL) storage

#flash_bootloader_jlink: $(BUILD_DIR)/bootloader.bin ## flash bootloader using JLink
#	JLinkExe -nogui 1 -commanderscript embed/projects/bootloader/bootloader_flash.jlink
#
#flash_bootloader_ci_jlink: $(BUILD_DIR)/bootloader.bin ## flash CI bootloader using JLink
#	JLinkExe -nogui 1 -commanderscript embed/projects/bootloader_ci/bootloader_flash.jlink
#
#flash_firmware_jlink: $(BUILD_DIR)/firmware.bin ## flash firmware using JLink. file names must end in .bin for JLink
#	cp -f $<.p1 $<.p1.bin
#	cp -f $<.p2 $<.p2.bin
#	## pad 2nd part so that FW integrity works after flash
#	## read&compare in flashing will avoid erasing unmodified sectors
#	truncate -s $(FIRMWARE_P2_MAXSIZE) $<.p2.bin
#	JLinkExe -nogui 1 -commanderscript embed/projects/firmware/firmware_flash.jlink

GDB = arm-none-eabi-gdb --nx -ex 'set remotetimeout unlimited' -ex 'set confirm off' -ex 'target remote 127.0.0.1:3333' -ex 'monitor reset halt'

gdb_boardloader: $(BUILD_DIR)/boardloader.elf ## start remote gdb session to openocd with boardloader symbols
	$(GDB) $<

gdb_bootloader: $(BUILD_DIR)/bootloader.elf ## start remote gdb session to openocd with bootloader symbols
	$(GDB) $<

gdb_prodtest: $(BUILD_DIR)/prodtest.elf ## start remote gdb session to openocd with prodtest symbols
	$(GDB) $<

gdb_firmware: $(BUILD_DIR)/firmware.elf ## start remote gdb session to openocd with firmware symbols
	$(GDB) $<

## misc commands:

bloaty: ## run bloaty size profiler
	bloaty -d symbols -n 0 -s file $(BUILD_DIR)/firmware.elf | less
	bloaty -d compileunits -n 0 -s file $(BUILD_DIR)/firmware.elf | less

combine: ## combine boardloader + bootloader + prodtest into one combined image
	xtask combine --model $(TREZOR_MODEL) prodtest

combine_fw: ## combine boardloader + bootloader + firmware into one combined image
	xtask combine --model $(TREZOR_MODEL) firmware

upload: ## upload firmware using trezorctl
	xtask upload firmware --model $(TREZOR_MODEL)

upload_prodtest: ## upload prodtest using trezorctl
	xtask upload prodtest --model $(TREZOR_MODEL)

# Skip the frozen-build rebuild when preprocessed `.i` files are already
# present (e.g. downloaded as a CI artifact); otherwise build first so local
# `make coverage` is self-contained.
COVERAGE_I_SENTINEL := $(BUILD_DIR)/mpy-files/trezor/utils.i
COVERAGE_BUILD_DEP  := $(if $(wildcard $(COVERAGE_I_SENTINEL)),,build_unix_frozen)

coverage: $(COVERAGE_BUILD_DEP) ## generate coverage report
	./tools/coverage-report
	./tools/coverage-annotate.py $(shell find . -name '.coverage*.json*') > htmlcov/hits.md

unused:  ## find unused micropython code
	vulture src src/_vulture_ignore.txt --exclude "messages.py,*/enums/*"


.PHONY: templates translations templates_check translations_check
