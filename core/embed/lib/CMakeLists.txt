add_library(trezor-lib
    mini_printf.c
    unit_variant.c
    buffers.c
    colors.c
    display.c
    fonts/fonts.c
    fonts/font_bitmap.c
    image.c
    fonts/font_tthoves_regular_21.c
    fonts/font_tthoves_bold_17.c
    fonts/font_tthoves_demibold_21.c
    fonts/font_robotomono_medium_20.c
    touch.c
)

target_include_directories(trezor-lib PUBLIC .)

target_link_libraries(trezor-lib stm32cube-f4 trezor-crypto trezor-storage models)