cmake_minimum_required(VERSION 3.13)
#cmake_policy(SET CMP0079 NEW)

project(trezor VERSION 1.0 LANGUAGES C CXX ASM)


set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_LINKER arm-none-abi-ld)


set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED True)

add_compile_definitions(STM32_HAL_H=<stm32f4xx.h>)
add_compile_definitions(STM32F427xx)
add_compile_definitions(USE_HAL_DRIVER)
add_compile_definitions(TREZOR_MODEL_T)
add_compile_definitions(UI_LAYOUT_TT)
add_compile_definitions(HW_MODEL=827601492)
add_compile_definitions(HW_REVISION=0)
add_compile_definitions(TREZOR_BOARD="boards/trezor_t.h")
add_compile_definitions(USE_DMA2D)
add_compile_definitions(PRODUCTION=0)
add_compile_definitions(BITCOIN_ONLY=0)
add_compile_definitions(BOOTLOADER_QA=0)
add_compile_definitions(USE_SVC_SHUTDOWN)
add_compile_definitions(RDI)


add_compile_definitions(USE_BIP32_CACHE=0)
add_compile_definitions(USE_KECCAK=1)
add_compile_definitions(USE_ETHEREUM=1)
add_compile_definitions(USE_MONERO=1)
add_compile_definitions(USE_CARDANO=1)
add_compile_definitions(USE_NEM=1)
add_compile_definitions(USE_EOS=1)

add_compile_definitions(AES_128)
add_compile_definitions(AES_192)

add_compile_definitions(SCM_REVISION="11")

add_compile_definitions(TREZOR_UI2)


add_compile_definitions(USE_ASM_ARM)
add_compile_definitions(USE_EXTERNAL_ASM)
add_compile_definitions(USE_EXTERNAL_DEFAULT_CALLBACKS)
add_compile_definitions(ECMULT_GEN_PREC_BITS=2)
add_compile_definitions(ECMULT_WINDOW_SIZE=8)
add_compile_definitions(ENABLE_MODULE_GENERATOR)
add_compile_definitions(ENABLE_MODULE_RECOVERY)
add_compile_definitions(ENABLE_MODULE_SCHNORRSIG)
add_compile_definitions(ENABLE_MODULE_EXTRAKEYS)
add_compile_definitions(FANCY_FATAL_ERROR)



add_compile_definitions(TREZOR_FONT_NORMAL_ENABLE=Font_TTHoves_Regular_21)
add_compile_definitions(TREZOR_FONT_NORMAL_INCLUDE="font_tthoves_regular_21.h")
add_compile_definitions(TREZOR_FONT_BOLD_ENABLE=Font_TTHoves_Bold_17)
add_compile_definitions(TREZOR_FONT_BOLD_INCLUDE="font_tthoves_bold_17.h")
add_compile_definitions(TREZOR_FONT_DEMIBOLD_ENABLE=Font_TTHoves_DemiBold_21)
add_compile_definitions(TREZOR_FONT_DEMIBOLD_INCLUDE="font_tthoves_demibold_21.h")
add_compile_definitions(TREZOR_FONT_MONO_ENABLE=Font_RobotoMono_Medium_20)
add_compile_definitions(TREZOR_FONT_MONO_INCLUDE="font_robotomono_medium_20.h")


set(Rust_CARGO_TARGET thumbv7em-none-eabihf)


Set(ENV{RUST_INCLUDES} "-I../trezorhal/stm32f4;-I../../vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Inc;
-I../../vendor/micropython/lib/stm32lib/CMSIS/STM32F4xx/Include;
-DSTM32_HAL_H=<stm32f4xx.h>")



add_compile_options(-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16 -mtune=cortex-m4)
add_compile_options(-Os -g3 -std=gnu11 -fno-common -fsingle-precision-constant 
  -fdata-sections -ffunction-sections -ffreestanding -fstack-protector-all)
#add_compile_options(-Wall -Werror -Wdouble-promotion -Wpointer-arith)
add_compile_options( -Wno-missing-braces -Wno-sequence-point)
add_compile_options(-ffreestanding -fstack-protector-all)


add_link_options(-nostdlib -Wl,--gc-sections -Wl,--warn-common)
add_link_options(-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16 -mtune=cortex-m4)

include_directories(embed/extmod/modtrezorconfig)
include_directories(${CMAKE_BINARY_DIR})

add_subdirectory(embed)
add_subdirectory(vendor)
add_subdirectory(src)
add_subdirectory(genhdr)


