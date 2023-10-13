add_executable(boardloader main.c startup.s ../trezorhal/stm32f4/util.s) # !@ utils.s !!!! to je divne

target_link_options(boardloader PRIVATE -T ${CMAKE_SOURCE_DIR}/embed/boardloader/memory.ld)

target_link_libraries(boardloader stm32cube-f4)
target_link_libraries(boardloader trezor-hal)
target_link_libraries(boardloader trezor-crypto trezor-storage models)

