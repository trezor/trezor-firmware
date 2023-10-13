add_library(stm32cube-f4 
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_cortex.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash_ex.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_gpio.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_i2c.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_ltdc.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pcd.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pcd_ex.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pwr.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc_ex.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_sd.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_spi.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_sram.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_sdram.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_tim.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_tim_ex.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_fmc.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_sdmmc.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_usb.c
    micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma2d.c
)

target_include_directories(stm32cube-f4 PUBLIC micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Inc)
target_include_directories(stm32cube-f4 PUBLIC micropython/lib/stm32lib/CMSIS/STM32F4xx/Include)
target_include_directories(stm32cube-f4 PUBLIC micropython/lib/cmsis/inc)
target_include_directories(stm32cube-f4 PUBLIC ../embed/trezorhal/stm32f4) # kvuli stm32f4xx_hal_conf.h
