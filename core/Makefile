.PHONY: vendor

JOBS = 4
MAKE = make -j $(JOBS)
SCONS = scons -Q -j $(JOBS)

BUILD_DIR             = build
BOARDLOADER_BUILD_DIR = $(BUILD_DIR)/boardloader
BOOTLOADER_BUILD_DIR  = $(BUILD_DIR)/bootloader
BOOTLOADER_CI_BUILD_DIR  = $(BUILD_DIR)/bootloader_ci
PRODTEST_BUILD_DIR    = $(BUILD_DIR)/prodtest
REFLASH_BUILD_DIR     = $(BUILD_DIR)/reflash
FIRMWARE_BUILD_DIR    = $(BUILD_DIR)/firmware
UNIX_BUILD_DIR        = $(BUILD_DIR)/unix
RUST_BUILD_DIR        = $(BUILD_DIR)/rust

UNAME_S := $(shell uname -s)
UNIX_PORT_OPTS ?=
CROSS_PORT_OPTS ?=

PRODUCTION ?= 0
PYOPT      ?= 1
BITCOIN_ONLY ?= 0
TREZOR_MODEL ?= T
TREZOR_MEMPERF ?= 0

OPENOCD_INTERFACE ?= stlink   # -or- ftdi/olimex-arm-usb-tiny-h
OPENOCD_TRANSPORT ?= hla_swd  # -or- jtag
OPENOCD = openocd -f interface/$(OPENOCD_INTERFACE).cfg -c "transport select $(OPENOCD_TRANSPORT)" -f target/stm32f4x.cfg
OPENOCD_T1 = openocd -f interface/$(OPENOCD_INTERFACE).cfg -c "transport select $(OPENOCD_TRANSPORT)" -f target/stm32f2x.cfg

BOARDLOADER_START   = 0x08000000
BOOTLOADER_START    = 0x08020000
FIRMWARE_P1_START   = 0x08040000
FIRMWARE_P2_START   = 0x08120000
PRODTEST_START      = 0x08040000
FIRMWARE_T1_START   = 0x08010000

BOARDLOADER_MAXSIZE = 49152
BOOTLOADER_MAXSIZE  = 131072
FIRMWARE_P1_MAXSIZE = 786432
FIRMWARE_P2_MAXSIZE = 917504
FIRMWARE_MAXSIZE    = 1703936

CFLAGS += -DSCM_REVISION='\"$(shell git rev-parse HEAD | sed 's:\(..\):\\x\1:g')\"'

TESTPATH = $(CURDIR)/../tests

EMU = $(CURDIR)/emu.py
EMU_LOG_FILE ?= $(TESTPATH)/trezor.log
EMU_TEST_ARGS = --disable-animation --headless --output=$(EMU_LOG_FILE) --temporary-profile
EMU_TEST = $(EMU) $(EMU_TEST_ARGS) -c

JUNIT_XML ?= $(TESTPATH)/junit.xml
PYTEST = pytest --junitxml=$(JUNIT_XML)
TREZOR_FIDO2_UDP_PORT = 21326

## help commands:

help: ## show this help
	@awk -f ../tools/help.awk $(MAKEFILE_LIST)

## dependencies commands:

vendor: ## update git submodules
	git submodule update --init --recursive --force

## emulator commands:

run: ## run unix port
	cd src ; ../$(UNIX_BUILD_DIR)/trezor-emu-core

emu: ## run emulator
	$(EMU)

## test commands:

test: ## run unit tests
	cd tests ; ./run_tests.sh $(TESTOPTS)

test_emu: ## run selected device tests from python-trezor
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/device_tests $(TESTOPTS)

test_emu_monero: ## run selected monero device tests from monero-agent
	cd tests ; $(EMU_TEST) ./run_tests_device_emu_monero.sh $(TESTOPTS)

test_emu_u2f: ## run selected u2f device tests from u2f-tests-hid
	$(EMU_TEST) --slip0014 $(TESTPATH)/fido_tests/u2f-tests-hid/HIDTest $(TREZOR_FIDO2_UDP_PORT) $(TESTOPTS)
	$(EMU_TEST) --slip0014 $(TESTPATH)/fido_tests/u2f-tests-hid/U2FTest $(TREZOR_FIDO2_UDP_PORT) $(TESTOPTS)

test_emu_fido2: ## run fido2 device tests
	cd $(TESTPATH)/fido_tests/fido2 ; \
		$(EMU_TEST) --slip0014 $(PYTEST) --maxfail=5 --sim tests/standard/ --vendor trezor $(TESTOPTS)

test_emu_click: ## run click tests
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/click_tests $(TESTOPTS)

test_emu_ui: ## run ui integration tests
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/device_tests --ui=test --ui-check-missing -m "not skip_ui" $(TESTOPTS)

test_emu_ui_record: ## record and hash screens for ui integration tests
	$(EMU_TEST) $(PYTEST) $(TESTPATH)/device_tests --ui=record --ui-check-missing -m "not skip_ui" $(TESTOPTS)

pylint: ## run pylint on application sources and tests
	pylint -E $(shell find src tests -name *.py)

mypy:
	mypy --config-file ../setup.cfg \
		src/main.py \
		src/apps/bitcoin \
		src/apps/cardano \
		src/apps/misc \
		src/apps/webauthn

## code generation:

templates: ## render Mako templates (for lists of coins, tokens, etc.)
	./tools/build_templates

templates_check: ## check that Mako-rendered files match their templates
	./tools/build_templates --check

## build commands:

build: build_boardloader build_bootloader build_firmware build_prodtest build_unix ## build all

build_embed: build_boardloader build_bootloader build_firmware # build boardloader, bootloader, firmware

build_boardloader: ## build boardloader
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" TREZOR_MODEL="$(TREZOR_MODEL)" $(BOARDLOADER_BUILD_DIR)/boardloader.bin

build_bootloader: ## build bootloader
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" TREZOR_MODEL="$(TREZOR_MODEL)" $(BOOTLOADER_BUILD_DIR)/bootloader.bin

build_bootloader_ci: ## build CI device testing bootloader
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" TREZOR_MODEL="$(TREZOR_MODEL)" $(BOOTLOADER_CI_BUILD_DIR)/bootloader.bin

build_prodtest: ## build production test firmware
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" TREZOR_MODEL="$(TREZOR_MODEL)" $(PRODTEST_BUILD_DIR)/prodtest.bin

build_reflash: ## build reflash firmware + reflash image
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" TREZOR_MODEL="$(TREZOR_MODEL)" $(REFLASH_BUILD_DIR)/reflash.bin
	dd if=build/boardloader/boardloader.bin of=$(REFLASH_BUILD_DIR)/sdimage.bin bs=1 seek=0
	dd if=build/bootloader/bootloader.bin of=$(REFLASH_BUILD_DIR)/sdimage.bin bs=1 seek=49152

build_firmware: templates build_cross ## build firmware with frozen modules
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" TREZOR_MODEL="$(TREZOR_MODEL)" PYOPT="$(PYOPT)" BITCOIN_ONLY="$(BITCOIN_ONLY)" $(FIRMWARE_BUILD_DIR)/firmware.bin

build_unix: templates ## build unix port
	$(SCONS) CFLAGS="$(CFLAGS)" $(UNIX_BUILD_DIR)/trezor-emu-core $(UNIX_PORT_OPTS) TREZOR_MODEL="$(TREZOR_MODEL)" BITCOIN_ONLY="$(BITCOIN_ONLY)"

build_unix_frozen: templates build_cross ## build unix port with frozen modules
	$(SCONS) CFLAGS="$(CFLAGS)" $(UNIX_BUILD_DIR)/trezor-emu-core $(UNIX_PORT_OPTS) TREZOR_MODEL="$(TREZOR_MODEL)" PYOPT="$(PYOPT)" BITCOIN_ONLY="$(BITCOIN_ONLY)" TREZOR_MEMPERF=$(TREZOR_MEMPERF) TREZOR_EMULATOR_FROZEN=1

build_unix_debug: templates ## build unix port
	$(SCONS) --max-drift=1 CFLAGS="$(CFLAGS)" $(UNIX_BUILD_DIR)/trezor-emu-core $(UNIX_PORT_OPTS) TREZOR_MODEL="$(TREZOR_MODEL)" TREZOR_EMULATOR_ASAN=1 TREZOR_EMULATOR_DEBUGGABLE=1

build_cross: ## build mpy-cross port
	$(MAKE) -C vendor/micropython/mpy-cross $(CROSS_PORT_OPTS)

## clean commands:

clean: clean_boardloader clean_bootloader clean_bootloader_ci clean_prodtest clean_reflash clean_firmware clean_unix clean_cross ## clean all
	rm -f ".sconsign.dblite"

clean_boardloader: ## clean boardloader build
	rm -rf $(BOARDLOADER_BUILD_DIR)

clean_bootloader: ## clean bootloader build
	rm -rf $(BOOTLOADER_BUILD_DIR)

clean_bootloader_ci: ## clean bootloader_ci build
	rm -rf $(BOOTLOADER_CI_BUILD_DIR)

clean_prodtest: ## clean prodtest build
	rm -rf $(PRODTEST_BUILD_DIR)

clean_reflash: ## clean reflash build
	rm -rf $(REFLASH_BUILD_DIR)

clean_firmware: ## clean firmware build
	rm -rf $(FIRMWARE_BUILD_DIR) $(RUST_BUILD_DIR)

clean_unix: ## clean unix build
	rm -rf $(UNIX_BUILD_DIR) $(RUST_BUILD_DIR)

clean_cross: ## clean mpy-cross build
	$(MAKE) -C vendor/micropython/mpy-cross clean $(CROSS_PORT_OPTS)

## flash commands:

flash: flash_boardloader flash_bootloader flash_firmware ## flash everything using OpenOCD

flash_boardloader: $(BOARDLOADER_BUILD_DIR)/boardloader.bin ## flash boardloader using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOARDLOADER_START); exit"

flash_bootloader: $(BOOTLOADER_BUILD_DIR)/bootloader.bin ## flash bootloader using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOOTLOADER_START); exit"

flash_bootloader_ci: $(BOOTLOADER_CI_BUILD_DIR)/bootloader.bin ## flash CI bootloader using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOOTLOADER_START); exit"

flash_prodtest: $(PRODTEST_BUILD_DIR)/prodtest.bin ## flash prodtest using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(PRODTEST_START); exit"

flash_firmware: $(FIRMWARE_BUILD_DIR)/firmware.bin ## flash firmware using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $<.p1 $(FIRMWARE_P1_START); flash write_image erase $<.p2 $(FIRMWARE_P2_START); exit"

flash_firmware_t1: $(FIRMWARE_BUILD_DIR)/firmware.bin ## flash T1 core port on T1 using OpenOCD
	$(OPENOCD_T1) -c "init; reset halt; flash write_image erase $< $(FIRMWARE_T1_START); exit"

flash_combine: $(PRODTEST_BUILD_DIR)/combined.bin ## flash combined using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOARDLOADER_START); exit"

flash_erase: ## erase all sectors in flash bank 0
	$(OPENOCD) -c "init; reset halt; flash info 0; flash erase_sector 0 0 last; flash erase_check 0; exit"

flash_read_storage: ## read storage sectors from flash
	$(OPENOCD) -c "init; flash read_bank 0 storage1.data 0x10000 65536; flash read_bank 0 storage2.data 0x110000 65536; exit"

flash_erase_storage: ## erase storage sectors from flash
	$(OPENOCD) -c "init; flash erase_sector 0 4 4; flash erase_sector 0 16 16; exit"

flash_bootloader_jlink: $(BOOTLOADER_BUILD_DIR)/bootloader.bin ## flash bootloader using JLink
	JLinkExe -nogui -commanderscript embed/bootloader/bootloader_flash.jlink

flash_bootloader_ci_jlink: $(BOOTLOADER_CI_BUILD_DIR)/bootloader.bin ## flash CI bootloader using JLink
	JLinkExe -nogui -commanderscript embed/bootloader_ci/bootloader_flash.jlink

flash_firmware_jlink: $(FIRMWARE_BUILD_DIR)/firmware.bin ## flash firmware using JLink. file names must end in .bin for JLink
	cp -f $<.p1 $<.p1.bin
	cp -f $<.p2 $<.p2.bin
	JLinkExe -nogui -commanderscript embed/firmware/firmware_flash.jlink

flash_firmware_t1_jlink: $(FIRMWARE_BUILD_DIR)/firmware.bin ## flash T1 core port via JLink
	JLinkExe -nogui -commanderscript embed/firmware/firmware_flash_t1.jlink

## openocd debug commands:

openocd: ## start openocd which connects to the device
	$(OPENOCD)

openocd_reset: ## cause a system reset using OpenOCD
	$(OPENOCD) -c "init; reset; exit"

GDB = arm-none-eabi-gdb --nx -ex 'set remotetimeout unlimited' -ex 'set confirm off' -ex 'target remote 127.0.0.1:3333' -ex 'monitor reset halt'

gdb_boardloader: $(BOARDLOADER_BUILD_DIR)/boardloader.elf ## start remote gdb session to openocd with boardloader symbols
	$(GDB) $<

gdb_bootloader: $(BOOTLOADER_BUILD_DIR)/bootloader.elf ## start remote gdb session to openocd with bootloader symbols
	$(GDB) $<

gdb_prodtest: $(PRODTEST_BUILD_DIR)/prodtest.elf ## start remote gdb session to openocd with prodtest symbols
	$(GDB) $<

gdb_firmware: $(FIRMWARE_BUILD_DIR)/firmware.elf ## start remote gdb session to openocd with firmware symbols
	$(GDB) $<

## misc commands:

binctl: ## print info about binary files
	./tools/headertool.py $(BOOTLOADER_BUILD_DIR)/bootloader.bin
	./tools/headertool.py $(FIRMWARE_BUILD_DIR)/firmware.bin

bloaty: ## run bloaty size profiler
	bloaty -d symbols -n 0 -s file $(FIRMWARE_BUILD_DIR)/firmware.elf | less
	bloaty -d compileunits -n 0 -s file $(FIRMWARE_BUILD_DIR)/firmware.elf | less

sizecheck: ## check sizes of binary files
	test $(BOARDLOADER_MAXSIZE) -ge $(shell wc -c < $(BOARDLOADER_BUILD_DIR)/boardloader.bin)
	test $(BOOTLOADER_MAXSIZE) -ge $(shell wc -c < $(BOOTLOADER_BUILD_DIR)/bootloader.bin)
	test $(FIRMWARE_P1_MAXSIZE) -ge $(shell wc -c < $(FIRMWARE_BUILD_DIR)/firmware.bin.p1)
	test $(FIRMWARE_P2_MAXSIZE) -ge $(shell wc -c < $(FIRMWARE_BUILD_DIR)/firmware.bin.p2)
	test $(FIRMWARE_MAXSIZE) -ge $(shell wc -c < $(FIRMWARE_BUILD_DIR)/firmware.bin)

combine: ## combine boardloader + bootloader + prodtest into one combined image
	./tools/combine_firmware \
		$(BOARDLOADER_START) $(BOARDLOADER_BUILD_DIR)/boardloader.bin \
		$(BOOTLOADER_START) $(BOOTLOADER_BUILD_DIR)/bootloader.bin \
		$(PRODTEST_START) $(PRODTEST_BUILD_DIR)/prodtest.bin \
		> $(PRODTEST_BUILD_DIR)/combined.bin

upload: ## upload firmware using trezorctl
	trezorctl firmware_update -f $(FIRMWARE_BUILD_DIR)/firmware.bin

upload_prodtest: ## upload prodtest using trezorctl
	trezorctl firmware_update -f $(PRODTEST_BUILD_DIR)/prodtest.bin

coverage:  # generate coverage report
	./tools/coverage-report
