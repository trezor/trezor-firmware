.PHONY: vendor

JOBS = 4
MAKE = make -j $(JOBS)
SCONS = scons -Q -j $(JOBS)

BUILD_DIR             = build
BOARDLOADER_BUILD_DIR = $(BUILD_DIR)/boardloader
BOOTLOADER_BUILD_DIR  = $(BUILD_DIR)/bootloader
PRODTEST_BUILD_DIR    = $(BUILD_DIR)/prodtest
REFLASH_BUILD_DIR     = $(BUILD_DIR)/reflash
FIRMWARE_BUILD_DIR    = $(BUILD_DIR)/firmware
UNIX_BUILD_DIR        = $(BUILD_DIR)/unix

UNAME_S := $(shell uname -s)
UNIX_PORT_OPTS ?=
CROSS_PORT_OPTS ?=

ifeq ($(DISPLAY_ILI9341V), 1)
CFLAGS += -DDISPLAY_ILI9341V=1
CFLAGS += -DDISPLAY_ST7789V=0
endif

PRODUCTION ?= 0

STLINK_VER ?= v2
OPENOCD = openocd -f interface/stlink-$(STLINK_VER).cfg -c "transport select hla_swd" -f target/stm32f4x.cfg

BOARDLOADER_START   = 0x08000000
BOOTLOADER_START    = 0x08020000
FIRMWARE_P1_START   = 0x08040000
FIRMWARE_P2_START   = 0x08120000
PRODTEST_START      = 0x08040000

BOARDLOADER_MAXSIZE = 49152
BOOTLOADER_MAXSIZE  = 131072
FIRMWARE_P1_MAXSIZE = 786432
FIRMWARE_P2_MAXSIZE = 917504
FIRMWARE_MAXSIZE    = 1703936

GITREV=$(shell git describe --always --dirty)
CFLAGS += -DGITREV=$(GITREV)

## help commands:

help: ## show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36m  make %-20s\033[0m %s\n", $$1, $$2} /^##(.*)/ {printf "\033[33m%s\n", substr($$0, 4)}' $(MAKEFILE_LIST)

## dependencies commands:

vendor: ## update git submodules
	git submodule update --init --recursive --force

res: ## update resources
	./tools/res_collect

## emulator commands:

run: ## run unix port
	cd src ; ../$(UNIX_BUILD_DIR)/micropython

emu: ## run emulator
	./emu.sh

## test commands:

test: ## run unit tests
	cd tests ; ./run_tests.sh $(TESTOPTS)

test_emu: ## run selected device tests from python-trezor
	cd tests ; ./run_tests_device_emu.sh $(TESTOPTS)

pylint: ## run pylint on application sources and tests
	pylint -E $(shell find src tests -name *.py)

## style commands:

style: ## run code style check on application sources and tests
	flake8 $(shell find src -name *.py)
	isort --check-only $(shell find src -name *.py ! -path 'src/trezor/messages/*')
	black --check $(shell find src -name *.py ! -path 'src/trezor/messages/*')

isort:
	isort $(shell find src -name *.py ! -path 'src/trezor/messages/*')

black:
	black $(shell find src -name *.py ! -path 'src/trezor/messages/*')

cstyle: ## run code style check on low-level C code
	./tools/clang-format-check $(shell find embed -type f -name *.[ch])

## build commands:

build: build_boardloader build_bootloader build_firmware build_prodtest build_unix ## build all

build_boardloader: ## build boardloader
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" $(BOARDLOADER_BUILD_DIR)/boardloader.bin

build_bootloader: ## build bootloader
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" $(BOOTLOADER_BUILD_DIR)/bootloader.bin

build_prodtest: ## build production test firmware
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" $(PRODTEST_BUILD_DIR)/prodtest.bin

build_reflash: ## build reflash firmware + reflash image
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" $(REFLASH_BUILD_DIR)/reflash.bin
	dd if=build/boardloader/boardloader.bin of=$(REFLASH_BUILD_DIR)/sdimage.bin bs=1 seek=0
	dd if=build/bootloader/bootloader.bin of=$(REFLASH_BUILD_DIR)/sdimage.bin bs=1 seek=49152

build_firmware: res build_cross ## build firmware with frozen modules
	$(SCONS) CFLAGS="$(CFLAGS)" PRODUCTION="$(PRODUCTION)" $(FIRMWARE_BUILD_DIR)/firmware.bin

build_unix: res ## build unix port
	$(SCONS) CFLAGS="$(CFLAGS)" $(UNIX_BUILD_DIR)/micropython $(UNIX_PORT_OPTS)

build_unix_noui: res ## build unix port without UI support
	$(SCONS) CFLAGS="$(CFLAGS)" $(UNIX_BUILD_DIR)/micropython $(UNIX_PORT_OPTS) TREZOR_NOUI=1

build_cross: ## build mpy-cross port
	$(MAKE) -C vendor/micropython/mpy-cross $(CROSS_PORT_OPTS)

## clean commands:

clean: clean_boardloader clean_bootloader clean_prodtest clean_firmware clean_unix clean_cross ## clean all

clean_boardloader: ## clean boardloader build
	rm -rf $(BOARDLOADER_BUILD_DIR)

clean_bootloader: ## clean bootloader build
	rm -rf $(BOOTLOADER_BUILD_DIR)

clean_prodtest: ## clean prodtest build
	rm -rf $(PRODTEST_BUILD_DIR)

clean_reflash: ## clean reflash build
	rm -rf $(REFLASH_BUILD_DIR)

clean_firmware: ## clean firmware build
	rm -rf $(FIRMWARE_BUILD_DIR)

clean_unix: ## clean unix build
	rm -rf $(UNIX_BUILD_DIR)

clean_cross: ## clean mpy-cross build
	$(MAKE) -C vendor/micropython/mpy-cross clean $(CROSS_PORT_OPTS)

## flash commands:

flash: flash_boardloader flash_bootloader flash_firmware ## flash everything using OpenOCD

flash_boardloader: $(BOARDLOADER_BUILD_DIR)/boardloader.bin ## flash boardloader using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOARDLOADER_START); exit"

flash_bootloader: $(BOOTLOADER_BUILD_DIR)/bootloader.bin ## flash bootloader using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOOTLOADER_START); exit"

flash_prodtest: $(PRODTEST_BUILD_DIR)/prodtest.bin ## flash prodtest using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(PRODTEST_START); exit"

flash_firmware: $(FIRMWARE_BUILD_DIR)/firmware.bin ## flash firmware using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $<.p1 $(FIRMWARE_P1_START); flash write_image erase $<.p2 $(FIRMWARE_P2_START); exit"

flash_combine: $(PRODTEST_BUILD_DIR)/combined.bin ## flash combined using OpenOCD
	$(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOARDLOADER_START); exit"

flash_erase: ## erase all sectors in flash bank 0
	$(OPENOCD) -c "init; reset halt; flash info 0; flash erase_sector 0 0 last; flash erase_check 0; exit"

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
	./tools/binctl $(BOOTLOADER_BUILD_DIR)/bootloader.bin
	./tools/binctl $(FIRMWARE_BUILD_DIR)/firmware.bin

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
		> $(PRODTEST_BUILD_DIR)/combined.bin \

upload: ## upload firmware using trezorctl
	trezorctl firmware_update -f $(FIRMWARE_BUILD_DIR)/firmware.bin

upload_prodtest: ## upload prodtest using trezorctl
	trezorctl firmware_update -f $(PRODTEST_BUILD_DIR)/prodtest.bin
