.PHONY: vendor

JOBS=4
MAKE=make -j $(JOBS)

BOOTLOADER_BUILD_DIR=micropython/bootloader/build
LOADER_BUILD_DIR=micropython/loader/build
FIRMWARE_BUILD_DIR=micropython/firmware/build

TREZORHAL_PORT_OPTS=FROZEN_MPY_DIR=src
UNIX_PORT_OPTS=MICROPY_FORCE_32BIT=1 MICROPY_PY_BTREE=0 MICROPY_PY_TERMIOS=0 MICROPY_PY_FFI=0 MICROPY_PY_USSL=0 MICROPY_SSL_AXTLS=0
CROSS_PORT_OPTS=MICROPY_FORCE_32BIT=1

help: ## show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36mmake %-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

vendor: ## update git submodules
	# git submodule update --init

res: ## update resources
	./tools/res_collect

build: build_firmware build_unix build_cross ## build firmware, unix and mpy-cross micropython ports

build_firmware: vendor res build_cross ## build firmware with frozen modules
	$(MAKE) -f Makefile.firmware $(TREZORHAL_PORT_OPTS)

build_firmware_debug: vendor res build_cross ## build firmware with frozen modules and debug symbols
	$(MAKE) -f Makefile.firmware $(TREZORHAL_PORT_OPTS) DEBUG=1

build_bootloader: vendor ## build bootloader
	mkdir -p $(BOOTLOADER_BUILD_DIR)/genhdr
	touch $(BOOTLOADER_BUILD_DIR)/genhdr/qstrdefs.generated.h
	$(MAKE) -f Makefile.bootloader $(TREZORHAL_PORT_OPTS)

build_loader: vendor ## build loader
	mkdir -p $(LOADER_BUILD_DIR)/genhdr
	touch $(LOADER_BUILD_DIR)/genhdr/qstrdefs.generated.h
	$(MAKE) -f Makefile.loader $(TREZORHAL_PORT_OPTS)

build_unix: vendor ## build unix port
	$(MAKE) -f ../../../micropython/unix/Makefile -C vendor/micropython/unix $(UNIX_PORT_OPTS)

build_unix_debug: vendor ## build unix port with debug symbols
	$(MAKE) -f ../../../micropython/unix/Makefile -C vendor/micropython/unix $(UNIX_PORT_OPTS) DEBUG=1

build_cross: vendor ## build mpy-cross port
	$(MAKE) -C vendor/micropython/mpy-cross $(CROSS_PORT_OPTS)

run: ## run unix port
	cd src ; ../vendor/micropython/unix/micropython

emu: ## run emulator
	./emu.sh

clean: clean_firmware clean_unix clean_cross ## clean all builds

clean_firmware: ## clean firmware build
	$(MAKE) -f Makefile.firmware clean $(TREZORHAL_PORT_OPTS)

clean_unix: ## clean unix build
	$(MAKE) -f ../../../micropython/unix/Makefile -C vendor/micropython/unix clean $(UNIX_PORT_OPTS)
	# workaround for relative paths containing ../.. in unix Makefile
	rm -rf vendor/micropython/micropython

clean_cross: ## clean mpy-cross build
	$(MAKE) -C vendor/micropython/mpy-cross clean $(CROSS_PORT_OPTS)

flash: ## flash firmware using st-flash
	st-flash write $(FIRMWARE_BUILD_DIR)/firmware.bin 0x8000000

flash_bootloader: ## flash bootloader using st-flash
	st-flash write $(BOOTLOADER_BUILD_DIR)/bootloader.bin 0x8000000

flash_loader: ## flash loader using st-flash
	st-flash write $(LOADER_BUILD_DIR)/loader.bin 0x8000000

flash_openocd: $(FIRMWARE_BUILD_DIR)/firmware.hex ## flash firmware using openocd
	openocd -f interface/stlink-v2.cfg -f target/stm32f4x.cfg \
		-c "init" \
		-c "reset init" \
		-c "stm32f4x mass_erase 0" \
		-c "flash write_image $(FIRMWARE_BUILD_DIR)/firmware.hex" \
		-c "reset" \
		-c "shutdown"

openocd: ## start openocd which connects to the device
	openocd -f interface/stlink-v2.cfg -f target/stm32f4x.cfg

gdb: ## start remote gdb session which connects to the openocd
	arm-none-eabi-gdb $(FIRMWARE_BUILD_DIR)/firmware.elf -ex 'target remote localhost:3333'

test: ## run unit tests
	cd tests ; ./run_tests.sh

testpy: ## run selected unit tests from python-trezor
	cd tests ; ./run_tests_python_trezor.sh
