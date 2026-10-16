# Host unit test for the pure power-manager core (managed/pm_core*.c and the
# charger leaf), linked against a fake fuel gauge and a fake charger.
#
#   make -C core/embed/io/power_manager/tests

EMBED := ../../..
CC ?= cc
CFLAGS ?= -std=gnu11 -O1 -g -Wall -Wextra -Wno-unused-parameter
CPPFLAGS := -DKERNEL_MODE -DTREZOR_EMULATOR \
  -I fake \
  -I $(EMBED)/rtl/inc \
  -I $(EMBED)/io/power_manager/inc \
  -I $(EMBED)/io/suspend/inc

SRCS := \
  ../managed/pm_core.c \
  ../managed/pm_core_states.c \
  ../managed/power_charging.c \
  pm_core_test.c

BUILD := build

.PHONY: all test clean
all: test

test: $(BUILD)/pm_core_test
	$(BUILD)/pm_core_test

$(BUILD)/pm_core_test: $(SRCS) ../managed/pm_core.h fake/trezor_bsp.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(CPPFLAGS) -o $@ $(SRCS) -lm

clean:
	rm -rf $(BUILD)
