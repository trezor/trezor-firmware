add_executable(firmware bl_check.c delay.c header.S main.c mphalport.c nlrthumb.c startup.S)

target_link_options(firmware PRIVATE -T ${CMAKE_SOURCE_DIR}/embed/firmware/memory_T.ld  -Wl,--print-memory-usage)

target_include_directories(firmware PRIVATE .)

target_link_libraries(firmware extmod2 stm32cube-f4 trezor-hal trezor-crypto trezor-storage models trezor_lib micropython extmod extmod2 frozen_mpy)




