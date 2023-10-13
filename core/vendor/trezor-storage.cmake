add_library(trezor-storage
    trezor-storage/norcow.c
    trezor-storage/storage.c
    trezor-storage/flash_common.c
)

target_include_directories(trezor-storage PUBLIC trezor-storage models)
target_link_libraries(trezor-storage trezor-lib)
