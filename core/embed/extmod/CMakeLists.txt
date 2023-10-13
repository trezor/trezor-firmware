add_library(extmod
    modtrezorconfig/modtrezorconfig.c
    modtrezorcrypto/crc.c
    modtrezorcrypto/modtrezorcrypto.c
    modtrezorcrypto/rand.c
    modtrezorio/modtrezorio.c
    modtrezorui/modtrezorui.c
    modtrezorutils/modtrezorutils.c
    modtrezorio/ff.c
    modtrezorio/ffunicode.c
    rustmods.c
    modutime.c
)

target_include_directories(extmod PRIVATE ../firmware ../rust ${CMAKE_SOURCE_DIR})

target_link_libraries(extmod micropython  trezor-hal trezor-lib trezor-crypto stm32cube-f4)


add_library(extmod2
    trezorobj.c
)

target_include_directories(extmod2 PRIVATE ../firmware ../rust ${CMAKE_SOURCE_DIR})

target_link_libraries(extmod2 micropython  trezor-hal trezor-lib trezor-crypto stm32cube-f4)

add_dependencies(extmod2 qstr)