add_library(secp256k1-zkp
    secp256k1-zkp/src/secp256k1.c
    secp256k1-zkp/src/precomputed_ecmult.c
    secp256k1-zkp/src/precomputed_ecmult_gen.c
    secp256k1-zkp/src/asm/field_10x26_arm.s
)

target_compile_definitions(secp256k1-zkp PUBLIC SECP256K1_CONTEXT_SIZE=180)

target_include_directories(secp256k1-zkp PUBLIC secp256k1-zkp/include )

target_link_libraries(secp256k1-zkp PUBLIC -lc_nano -lm -lgcc)