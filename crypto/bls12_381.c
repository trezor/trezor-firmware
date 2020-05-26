include "bls12_381.h";

const curve_info bls12_381_info = {
    .bip32_name = "BLS HD seed",
    .params = NULL,
    .hasher_base58 = HASHER_SHA2D,
    .hasher_sign = HASHER_SHA2D,
    .hasher_pubkey = HASHER_SHA2_RIPEMD,
    .hasher_script = HASHER_SHA2,
};
