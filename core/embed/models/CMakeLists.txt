add_library(models 
    model_T2T1_layout.c
)

target_include_directories(models PUBLIC .)

target_link_libraries(models trezor-hal)