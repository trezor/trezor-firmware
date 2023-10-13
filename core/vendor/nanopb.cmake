add_library(nanopb
    nanopb/pb_common.c
    nanopb/pb_decode.c
    nanopb/pb_encode.c
)

target_include_directories(trezor-storage PUBLIC nanopb)
