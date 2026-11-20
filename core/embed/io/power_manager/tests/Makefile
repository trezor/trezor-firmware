# Host unit tests of the alkaline fuel gauge driver
# (fuel_gauge/alkaline/battery.c) on GoogleTest. The HAL GPIO driver and the
# system timer are replaced by the gMock mocks in mock/.
#
#   make test     build and run the tests
#   make clean
#
# GoogleTest is taken from GTEST_DIR, built with CMake into its build/
# subdirectory (cmake -B build && cmake --build build).
# Pass SANITIZE= to build without the address/undefined-behavior sanitizers.

CORE  := ../../../..
EMBED := $(CORE)/embed
PM    := ..
FG    := $(PM)/fuel_gauge/alkaline
B     := build
BIN   := $(B)/test_battery

GTEST_DIR ?= $(CORE)/tests/googletest
GTEST_LIB := $(GTEST_DIR)/build/lib
GTEST_LIBS := $(GTEST_LIB)/libgmock_main.a $(GTEST_LIB)/libgmock.a \
              $(GTEST_LIB)/libgtest.a

CC       ?= gcc
CXX      ?= g++
OPT      ?= -O1
SANITIZE ?= -fsanitize=address,undefined,float-cast-overflow

DEFS := -DKERNEL_MODE -DTREZOR_EMULATOR -DUSE_FUEL_GAUGE_ALKALINE

# mock/ comes first: it overrides <trezor_bsp.h>
INCS := -Imock \
        -I$(EMBED)/rtl/inc \
        -I$(EMBED)/sys/time/inc \
        -I$(EMBED)/sys/irq/inc \
        -I$(PM)/fuel_gauge \
        -I$(FG)

GTEST_INCS := -isystem $(GTEST_DIR)/googletest/include \
              -isystem $(GTEST_DIR)/googlemock/include

COMMON_FLAGS := -g $(OPT) -fno-omit-frame-pointer -Wall \
                -Wno-unused-parameter $(SANITIZE) $(DEFS) $(INCS) -MMD -MP
CFLAGS   := -std=gnu11 $(COMMON_FLAGS)
CXXFLAGS := -std=gnu++17 $(COMMON_FLAGS) $(GTEST_INCS) \
            -DTEST_VECTORS_DIR='"$(CURDIR)/vectors"'

# Code under test. battery.c is compiled through battery_test_access.c.
SRCS_C := \
	battery_test_access.c \
	$(FG)/fuel_gauge.c \
	$(FG)/dummy_load.c \
	$(FG)/battery_model/src/soc_ocv_data.c \
	$(FG)/battery_model/src/soc_ocv_lut.c \
	$(FG)/battery_model/src/soc_ocv_temp.c

# Mocks and tests
SRCS_CXX := \
	mock/mock_hal_gpio.cc \
	mock/mock_systimer.cc \
	test_battery.cc

# Objects mirror the source paths below $(B), with ../ replaced by up/
obj = $(addprefix $(B)/,$(addsuffix .o,$(subst ../,up/,$(1))))
OBJS := $(call obj,$(SRCS_C)) $(call obj,$(SRCS_CXX))

.PHONY: test clean

test: $(BIN)
	$(BIN)

$(BIN): $(OBJS) $(GTEST_LIBS)
	$(CXX) $(SANITIZE) $(OBJS) $(GTEST_LIBS) -pthread -lm -o $@

define compile_rule
$(call obj,$(1)): $(1)
	@mkdir -p $$(dir $$@)
	$(2) -c $$< -o $$@
endef

$(foreach src,$(SRCS_C),$(eval $(call compile_rule,$(src),$$(CC) $$(CFLAGS))))
$(foreach src,$(SRCS_CXX),$(eval $(call compile_rule,$(src),$$(CXX) $$(CXXFLAGS))))

$(GTEST_LIBS):
	$(error GoogleTest not found in $(GTEST_DIR), set GTEST_DIR)

clean:
	rm -rf $(B)

-include $(OBJS:.o=.d)
