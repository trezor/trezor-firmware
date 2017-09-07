.PHONY: vendor

JOBS = 4
MAKE = make -j $(JOBS)
SCONS = scons -Q -j $(JOBS)

BOARDLOADER_BUILD_DIR = build/boardloader
BOOTLOADER_BUILD_DIR  = build/bootloader
FIRMWARE_BUILD_DIR    = build/firmware

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
UNIX_PORT_OPTS ?= TREZOR_X86=0
else
UNIX_PORT_OPTS ?= TREZOR_X86=1
endif
CROSS_PORT_OPTS ?= MICROPY_FORCE_32BIT=1

ifeq ($(DISPLAY_ILI9341V), 1)
CFLAGS += -DDISPLAY_ILI9341V=1
CFLAGS += -DDISPLAY_ST7789V=0
endif

ifeq ($(DISPLAY_VSYNC), 0)
CFLAGS += -DDISPLAY_VSYNC=0
endif

## help commands:

help: ## show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36m  make %-20s\033[0m %s\n", $$1, $$2} /^##(.*)/ {printf "\033[33m%s\n", substr($$0, 4)}' $(MAKEFILE_LIST)

## dependencies commands:

vendor: ## update git submodules
	git submodule update --init

res: ## update resources
	./tools/res_collect

## emulator commands:

run: ## run unix port
	cd src ; ../build/unix/micropython

emu: ## run emulator
	./emu.sh

## test commands:

test: ## run unit tests
	cd tests ; ./run_tests.sh

testpy: ## run selected unit tests from python-trezor
	cd tests ; ./run_tests_device.sh

pylint: ## run pylint on application sources
	pylint -E $(shell find src -name *.py)

style: ## run code style check on application sources
	flake8 $(shell find src -name *.py)

## build commands:

build: build_boardloader build_bootloader build_firmware build_unix build_cross ## build all

build_boardloader: ## build boardloader
	$(SCONS) CFLAGS="$(CFLAGS)" build/boardloader/boardloader.bin

build_bootloader: ## build bootloader
	$(SCONS) CFLAGS="$(CFLAGS)" build/bootloader/bootloader.bin

build_firmware: res build_cross ## build firmware with frozen modules
	$(SCONS) CFLAGS="$(CFLAGS)" build/firmware/firmware.bin

build_unix: ## build unix port
	$(SCONS) build/unix/micropython $(UNIX_PORT_OPTS)

build_unix_noui: ## build unix port without UI support
	$(SCONS) build/unix/micropython $(UNIX_PORT_OPTS) TREZOR_NOUI=1

build_cross: ## build mpy-cross port
	$(MAKE) -C vendor/micropython/mpy-cross $(CROSS_PORT_OPTS)

## clean commands:

clean: clean_boardloader clean_bootloader clean_firmware clean_unix clean_cross ## clean all

clean_boardloader: ## clean boardloader build
	rm -rf build/boardloader

clean_bootloader: ## clean bootloader build
	rm -rf build/bootloader

clean_firmware: ## clean firmware build
	rm -rf build/firmware

clean_unix: ## clean unix build
	rm -rf build/unix

clean_cross: ## clean mpy-cross build
	$(MAKE) -C vendor/micropython/mpy-cross clean $(CROSS_PORT_OPTS)

## flash commands:

flash: flash_boardloader flash_bootloader flash_firmware ## flash everything using st-flash

flash_boardloader: ## flash boardloader using st-flash
	st-flash write $(BOARDLOADER_BUILD_DIR)/boardloader.bin 0x08000000

flash_bootloader: ## flash bootloader using st-flash
	st-flash write $(BOOTLOADER_BUILD_DIR)/bootloader.bin 0x08010000

flash_firmware: ## flash firmware using st-flash
	st-flash write $(FIRMWARE_BUILD_DIR)/firmware.bin 0x08020000

flash_combine: ## flash combined image using st-flash
	st-flash write $(FIRMWARE_BUILD_DIR)/combined.bin 0x08000000

## openocd debug commands:

openocd: ## start openocd which connects to the device
	openocd -f interface/stlink-v2.cfg -f target/stm32f4x.cfg

gdb: ## start remote gdb session which connects to the openocd
	arm-none-eabi-gdb $(FIRMWARE_BUILD_DIR)/firmware.elf -ex 'target remote localhost:3333'

## misc commands:

vendorheader: ## construct default vendor header
	./tools/build_vendorheader 'db995fe25169d141cab9bbba92baa01f9f2e1ece7df4cb2ac05190f37fcc1f9d:2152f8d19b791d24453242e15f2eab6cb7cffa7b6a5ed30097960e069881db12:22fc297792f0b6ffc0bfcfdb7edb0c0aa14e025a365ec0e342e86e3829cb74b6' 1 0.0 SatoshiLabs assets/satoshilabs_120.toif embed/firmware/vendorheader.bin
	./tools/binctl embed/firmware/vendorheader.bin -s 1 4141414141414141414141414141414141414141414141414141414141414141

binctl: ## print info about binary files
	./tools/binctl $(BOOTLOADER_BUILD_DIR)/bootloader.bin
	./tools/binctl embed/firmware/vendorheader.bin
	./tools/binctl $(FIRMWARE_BUILD_DIR)/firmware.bin

bloaty: ## run bloaty size profiler
	bloaty -d symbols -n 0 -s file $(FIRMWARE_BUILD_DIR)/firmware.elf | less
	bloaty -d compileunits -n 0 -s file $(FIRMWARE_BUILD_DIR)/firmware.elf | less

sizecheck: ## check sizes of binary files
	test 32768 -ge $(shell stat -c%s $(BOARDLOADER_BUILD_DIR)/boardloader.bin)
	test 65536 -ge $(shell stat -c%s $(BOOTLOADER_BUILD_DIR)/bootloader.bin)
	test 917504 -ge $(shell stat -c%s $(FIRMWARE_BUILD_DIR)/firmware.bin)

combine: ## combine boardloader + bootloader + firmware into one combined image
	./tools/combine_firmware \
		0x08000000 $(BOARDLOADER_BUILD_DIR)/boardloader.bin \
		0x08010000 $(BOOTLOADER_BUILD_DIR)/bootloader.bin \
		0x08020000 $(FIRMWARE_BUILD_DIR)/firmware.bin \
		> $(FIRMWARE_BUILD_DIR)/combined.bin \
