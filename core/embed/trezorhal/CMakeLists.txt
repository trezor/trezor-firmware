add_library(trezor-hal
    stm32f4/board_capabilities.c
    stm32f4/common.c
    stm32f4/flash.c
    stm32f4/lowlevel.c
    stm32f4/mpu.c
    stm32f4/platform.c
    stm32f4/systick.c
    stm32f4/random_delays.c
    stm32f4/rng.c
    stm32f4/vectortable.s
    stm32f4/util.s
    stm32f4/displays/st7789v.c
    stm32f4/backlight_pwm.c
    stm32f4/displays/panels/tf15411a.c
    stm32f4/displays/panels/154a.c
    stm32f4/displays/panels/lx154a2411.c
    stm32f4/displays/panels/lx154a2422.c
    stm32f4/i2c.c
    stm32f4/touch/ft6x36.c
    stm32f4/sdcard.c
    stm32f4/sbu.c
    stm32f4/usb.c
    stm32f4/usbd_conf.c
    stm32f4/usbd_core.c
    stm32f4/usbd_ctlreq.c
    stm32f4/usbd_ioreq.c
    stm32f4/dma2d.c
)

target_include_directories(trezor-hal PUBLIC .)
target_include_directories(trezor-hal PRIVATE stm32f4)

target_include_directories(trezor-hal PRIVATE ../rust)

target_link_libraries(trezor-hal stm32cube-f4 trezor-lib trezor-storage models)


