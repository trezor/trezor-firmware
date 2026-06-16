/* SPHINCS+ variant: shake-192f */
#define __SHA3_H__
#define PARAMS sphincs-shake-192f
#include "params.h"
#undef SPX_NAMESPACE
#define SPX_NAMESPACE(s) spx_shake_192f_##s
#define crypto_sign_seed_keypair   spx_shake_192f_seed_keypair
#define crypto_sign_keypair        spx_shake_192f_keypair
#define crypto_sign_signature      spx_shake_192f_sign
#define crypto_sign_verify         spx_shake_192f_verify
#define crypto_sign_bytes          spx_shake_192f_sig_bytes
#define crypto_sign_secretkeybytes spx_shake_192f_sk_bytes
#define crypto_sign_publickeybytes spx_shake_192f_pk_bytes
#define crypto_sign_seedbytes      spx_shake_192f_seed_bytes
#define crypto_sign                spx_shake_192f_crypto_sign
#define crypto_sign_open           spx_shake_192f_crypto_sign_open
/* Namespace ALL fips202 public functions */
#define sha3_256               spx_shake_192f_sha3_256
#define sha3_512               spx_shake_192f_sha3_512
#define shake128               spx_shake_192f_shake128
#define shake256               spx_shake_192f_shake256
#define shake128_inc_init      spx_shake_192f_shake128_inc_init
#define shake128_inc_absorb    spx_shake_192f_shake128_inc_absorb
#define shake128_inc_finalize  spx_shake_192f_shake128_inc_finalize
#define shake128_inc_squeeze   spx_shake_192f_shake128_inc_squeeze
#define shake256_inc_init      spx_shake_192f_shake256_inc_init
#define shake256_inc_absorb    spx_shake_192f_shake256_inc_absorb
#define shake256_inc_finalize  spx_shake_192f_shake256_inc_finalize
#define shake256_inc_squeeze   spx_shake_192f_shake256_inc_squeeze
#define shake128_absorb        spx_shake_192f_shake128_absorb
#define shake128_squeezeblocks spx_shake_192f_shake128_squeezeblocks
#define shake256_absorb        spx_shake_192f_shake256_absorb
#define shake256_squeezeblocks spx_shake_192f_shake256_squeezeblocks
#define randombytes            spx_shake_192f_randombytes
#include "../../vendor/sphincsplus/ref/sign.c"
#include "../../vendor/sphincsplus/ref/address.c"
#include "../../vendor/sphincsplus/ref/merkle.c"
#include "../../vendor/sphincsplus/ref/wots.c"
#include "../../vendor/sphincsplus/ref/wotsx1.c"
#include "../../vendor/sphincsplus/ref/utils.c"
#include "../../vendor/sphincsplus/ref/utilsx1.c"
#include "../../vendor/sphincsplus/ref/fors.c"
#include "../../vendor/sphincsplus/ref/hash_shake.c"
#include "../../vendor/sphincsplus/ref/thash_shake_simple.c"
#include "../../vendor/sphincsplus/ref/fips202.c"
#include "randombytes_trezor.c"
