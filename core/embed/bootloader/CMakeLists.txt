add_executable(bootloader bootui.c header.S main.c messages.c startup.s 
  ../trezorhal/stm32f4/util.s protob/messages.pb.c
  ../lib/fonts/font_tthoves_regular_21.c
  )

target_compile_definitions(bootloader PRIVATE TREZOR_FONT_NORMAL_ENABLE=Font_TTHoves_Regular_21)
target_compile_definitions(bootloader PRIVATE TREZOR_FONT_NORMAL_INCLUDE="font_tthoves_regular_21.h")

target_include_directories(bootloader PRIVATE protob)
target_include_directories(bootloader PRIVATE ../rust)

target_link_options(bootloader PRIVATE -T ${CMAKE_SOURCE_DIR}/embed/bootloader/memory.ld)

target_link_libraries(bootloader stm32cube-f4 trezor-hal)
target_link_libraries(bootloader trezor-crypto trezor-storage models nanopb trezor_lib)

