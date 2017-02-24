# include default settings
include ../py/mkenv.mk

# qstr definitions target, used in py.mk
QSTR_DEFS = qstrdefsport.h

# directory containing scripts to be frozen as bytecode
FROZEN_MPY_DIR ?= modules

# enable external modules, used in py.mk
MICROPY_PY_TREZORCONFIG = 1
MICROPY_PY_TREZORCRYPTO = 1
MICROPY_PY_TREZORDEBUG = 1
MICROPY_PY_TREZORMSG = 1
MICROPY_PY_TREZORUI = 1
MICROPY_PY_TREZORUTILS = 1

# include py core make definitions
include ../py/py.mk

CROSS_COMPILE = arm-none-eabi-

INC += -I.
INC += -I..
INC += -I../stmhal
INC += -I../stmhal/cmsis
INC += -I../stmhal/hal/f4/inc
INC += -I../stmhal/usbdev/core/inc
INC += -I../stmhal/usbdev/class/inc
INC += -I../lib/cmsis/inc
INC += -I../lib/mp-readline
INC += -I$(BUILD)

ifeq ($(DEBUG), 1)
COPT = -O0 -ggdb
else
COPT = -Os -DNDEBUG
endif

CFLAGS += $(INC) $(COPT) $(CFLAGS_MOD) $(CFLAGS_EXTRA)
CFLAGS += -std=gnu99 -nostdlib -Wall -Werror -Wdouble-promotion -Wpointer-arith
CFLAGS += -mthumb -mtune=cortex-m4 -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard -fsingle-precision-constant

CFLAGS += -DSTM32F405xx -DMCU_SERIES_F4
CFLAGS += -DSTM32_HAL_H='<stm32f4xx_hal.h>'

LIBS = $(shell $(CC) $(CFLAGS) -print-libgcc-file-name)

LDFLAGS = -nostdlib -T trezorv2.ld -Map=$@.map --cref

# remove uncalled code from the final image
CFLAGS += -fdata-sections -ffunction-sections
LDFLAGS += --gc-sections

SRC_LIB = $(addprefix lib/,\
	libc/string0.c \
	libm/math.c \
	libm/thumb_vfp_sqrtf.c \
	libm/asinfacosf.c \
	libm/atanf.c \
	libm/atan2f.c \
	libm/fmodf.c \
	libm/roundf.c \
	libm/log1pf.c \
	libm/acoshf.c \
	libm/asinhf.c \
	libm/atanhf.c \
	libm/kf_rem_pio2.c \
	libm/kf_sin.c \
	libm/kf_cos.c \
	libm/kf_tan.c \
	libm/ef_rem_pio2.c \
	libm/erf_lgamma.c \
	libm/sf_sin.c \
	libm/sf_cos.c \
	libm/sf_tan.c \
	libm/sf_frexp.c \
	libm/sf_modf.c \
	libm/sf_ldexp.c \
	libm/sf_erf.c \
	libm/wf_lgamma.c \
	libm/wf_tgamma.c \
	libc/string0.c \
	mp-readline/readline.c \
	utils/stdout_helpers.c \
	utils/pyexec.c \
	)

SRC_HAL = $(addprefix stmhal/hal/f4/src/stm32f4xx_,\
	hal.c \
	hal_adc.c \
	hal_adc_ex.c \
	hal_can.c \
	hal_cortex.c \
	hal_dac.c \
	hal_dac_ex.c \
	hal_dma.c \
	hal_flash.c \
	hal_flash_ex.c \
	hal_gpio.c \
	hal_i2c.c \
	hal_pcd.c \
	hal_pcd_ex.c \
	hal_pwr.c \
	hal_pwr_ex.c \
	hal_rcc.c \
	hal_rcc_ex.c \
	hal_rng.c \
	hal_rtc.c \
	hal_rtc_ex.c \
	hal_sd.c \
	hal_spi.c \
	hal_sram.c \
	hal_tim.c \
	hal_tim_ex.c \
	hal_uart.c \
	ll_fsmc.c \
	ll_sdmmc.c \
	ll_usb.c \
	)

SRC_USBDEV = $(addprefix stmhal/usbdev/,\
	core/src/usbd_core.c \
	core/src/usbd_ctlreq.c \
	core/src/usbd_ioreq.c \
	class/src/usbd_cdc_msc_hid.c \
	class/src/usbd_msc_bot.c \
	class/src/usbd_msc_scsi.c \
	class/src/usbd_msc_data.c \
	)

SRC_C = \
	main.c \
	stm32_it.c \
	modutime.c \
	lib/utils/stdout_helpers.c \
	lib/utils/pyexec.c \
	lib/libc/string0.c \
	lib/mp-readline/readline.c \
	stmhal/pendsv.c \
	stmhal/systick.c \
	stmhal/gccollect.c \
	stmhal/system_stm32.c \
	stmhal/usbd_conf.c \
	stmhal/usbd_desc.c \
	stmhal/usbd_cdc_interface.c \
	stmhal/usbd_hid_interface.c \
	$(BUILD)/frozen_mpy.c

SRC_QSTR += modutime.c

SRC_O = \
	stmhal/startup_stm32.o \
	stmhal/gchelper.o \

OBJ = \
	$(PY_O) \
	$(addprefix $(BUILD)/, $(SRC_O)) \
	$(addprefix $(BUILD)/, $(SRC_C:.c=.o)) \
	$(addprefix $(BUILD)/, $(SRC_LIB:.c=.o)) \
	$(addprefix $(BUILD)/, $(SRC_HAL:.c=.o)) \
	$(addprefix $(BUILD)/, $(SRC_USBDEV:.c=.o)) \
	$(addprefix $(BUILD)/, $(SRC_MOD:.c=.o))

all: $(BUILD)/firmware.bin

$(BUILD)/firmware.elf: $(OBJ)
	$(ECHO) "LINK $@"
	$(Q)$(LD) $(LDFLAGS) -o $@ $^ $(LIBS)
	$(Q)$(SIZE) $@

$(BUILD)/firmware.bin: $(BUILD)/firmware.elf
	$(Q)$(OBJCOPY) -O binary -j .flash -j .data $^ $(BUILD)/firmware.bin

include ../py/mkrules.mk
