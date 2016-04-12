STMHAL_BUILD_DIR=vendor/micropython/stmhal/build-TREZORV2

help: ## show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36mmake %-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

update: ## update git submodules
	git submodule update

build: update build_stmhal build_unix ## build both stmhal and unix micropython ports

build_stmhal: ## build stmhal port
	make -C vendor/micropython/stmhal

build_unix: ## build unix port
	make -C vendor/micropython/unix

run_unix: ## run unix port
	cd src ; ../vendor/micropython/unix/micropython

clean: clean_stmhal clean_unix ## clean all builds

clean_stmhal: ## clean stmhal build
	make -C vendor/micropython/stmhal clean

clean_unix: ## clean unix build
	make -C vendor/micropython/unix clean

test: ## run unit tests
	cd src/tests ; ./run_tests.sh

flash: ## flash firmware using st-flash
	st-flash write $(STMHAL_BUILD_DIR)/firmware0.bin 0x8000000
	sleep 0.1
	st-flash write $(STMHAL_BUILD_DIR)/firmware1.bin 0x8020000

openocd: ## start openocd which connects to the device
	openocd -f interface/stlink-v2.cfg -f target/stm32f4x_stlink.cfg

gdb: ## start remote gdb session which connects to the openocd
	gdb $(STMHAL_BUILD_DIR)/firmware.elf -ex 'target remote localhost:3333'

load: ## load contents of src into mass storage of trezor
	rm -rf /run/media/${USER}/PYBFLASH/*
	cp -a src/* /run/media/${USER}/PYBFLASH/
	sync
