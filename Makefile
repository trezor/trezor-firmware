.PHONY: vendor

JOBS=4
MAKE=make -j $(JOBS)
BOARD=TREZORV2

STMHAL_BUILD_DIR=vendor/micropython/stmhal/build-$(BOARD)

help: ## show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "\033[36mmake %-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

vendor: ## update git submodules
	git submodule update --init

res: ## update resources
	./tools/res_collect.py

build: build_stmhal build_unix build_cross ## build stmhal, unix and mpy-cross micropython ports

build_stmhal: vendor ## build stmhal port
	$(MAKE) -C vendor/micropython/stmhal BOARD=$(BOARD)

build_stmhal_debug: vendor ## build stmhal port with debug symbols
	$(MAKE) -C vendor/micropython/stmhal BOARD=$(BOARD) DEBUG=1

build_stmhal_frozen: vendor res build_cross ## build stmhal port with frozen modules (from /src)
	$(MAKE) -C vendor/micropython/stmhal BOARD=$(BOARD) FROZEN_MPY_DIR=../../../src

build_unix: vendor ## build unix port
	$(MAKE) -C vendor/micropython/unix MICROPY_FORCE_32BIT=1

build_unix_debug: vendor ## build unix port with debug symbols
	$(MAKE) -C vendor/micropython/unix MICROPY_FORCE_32BIT=1 DEBUG=1

build_unix_frozen: vendor res build_cross ## build unix port with frozen modules (from /src)
	$(MAKE) -C vendor/micropython/unix MICROPY_FORCE_32BIT=1 FROZEN_MPY_DIR=../../../src

build_cross: vendor ## build mpy-cross port
	$(MAKE) -C vendor/micropython/mpy-cross MICROPY_FORCE_32BIT=1

build_bootloader: vendor ## build bootloader
	$(MAKE) -C vendor/micropython/stmhal -f Makefile.bootloader BOARD=$(BOARD)

run: ## run unix port
	cd src ; ../vendor/micropython/unix/micropython

emu: ## run emulator
	./emu.sh

clean: clean_stmhal clean_unix clean_cross ## clean all builds

clean_stmhal: ## clean stmhal build
	$(MAKE) -C vendor/micropython/stmhal clean BOARD=$(BOARD)

clean_unix: ## clean unix build
	$(MAKE) -C vendor/micropython/unix clean

clean_cross: ## clean mpy-cross build
	$(MAKE) -C vendor/micropython/mpy-cross clean

test: ## run unit tests
	cd tests ; ./run_tests.sh

flash: ## flash firmware using st-flash
	st-flash write $(STMHAL_BUILD_DIR)/firmware0.bin 0x8000000
	sleep 0.1
	st-flash write $(STMHAL_BUILD_DIR)/firmware1.bin 0x8020000

flash_bl: vendor ## flash bootloader using st-flash
	st-flash write $(STMHAL_BUILD_DIR)/bootloader0.bin 0x8000000
	sleep 0.1
	st-flash write $(STMHAL_BUILD_DIR)/bootloader1.bin 0x8020000

openocd_flash: $(STMHAL_BUILD_DIR)/firmware.hex ## flash firmware using openocd
	openocd -f interface/stlink-v2.cfg -f target/stm32f4x.cfg \
		-c "init" \
		-c "reset init" \
		-c "stm32f4x mass_erase 0" \
		-c "flash write_image $(STMHAL_BUILD_DIR)/firmware.hex" \
		-c "reset" \
		-c "shutdown"

openocd_flash_bl: $(STMHAL_BUILD_DIR)/bootloader.hex ## flash bootloader using openocd
	openocd -f interface/stlink-v2.cfg -f target/stm32f4x.cfg \
		-c "init" \
		-c "reset init" \
		-c "stm32f4x mass_erase 0" \
		-c "flash write_image $(STMHAL_BUILD_DIR)/bootloader.hex" \
		-c "reset" \
		-c "shutdown"

openocd: ## start openocd which connects to the device
	openocd -f interface/stlink-v2.cfg -f target/stm32f4x.cfg

gdb: ## start remote gdb session which connects to the openocd
	arm-none-eabi-gdb $(STMHAL_BUILD_DIR)/firmware.elf -ex 'target remote localhost:3333'

gdb_bl: ## start remote gdb session which connects to the openocd
	arm-none-eabi-gdb $(STMHAL_BUILD_DIR)/bootloader.elf -ex 'target remote localhost:3333'

load: ## load contents of src into mass storage of trezor
	rm -rf /run/media/${USER}/PYBFLASH/*
	cp -a src/apps /run/media/${USER}/PYBFLASH/
	cp -a src/lib /run/media/${USER}/PYBFLASH/
	cp -a src/trezor /run/media/${USER}/PYBFLASH/
	cp -a src/*.py /run/media/${USER}/PYBFLASH/
	sync
