/* SPHINCS+ variant: sha2-256s */
#define PARAMS sphincs-sha2-256s
#include "params.h"
#undef SPX_NAMESPACE
#define SPX_NAMESPACE(s) spx_sha2_256s_##s
#define crypto_sign_seed_keypair   spx_sha2_256s_seed_keypair
#define crypto_sign_keypair        spx_sha2_256s_keypair
#define crypto_sign_signature      spx_sha2_256s_sign
#define crypto_sign_verify         spx_sha2_256s_verify
#define crypto_sign_bytes          spx_sha2_256s_sig_bytes
#define crypto_sign_secretkeybytes spx_sha2_256s_sk_bytes
#define crypto_sign_publickeybytes spx_sha2_256s_pk_bytes
#define crypto_sign_seedbytes      spx_sha2_256s_seed_bytes
#define crypto_sign                spx_sha2_256s_crypto_sign
#define crypto_sign_open           spx_sha2_256s_crypto_sign_open
#define sha256_inc_init    spx_sha2_256s_sha256_inc_init
#define sha256_inc_blocks  spx_sha2_256s_sha256_inc_blocks
#define sha256_inc_finalize spx_sha2_256s_sha256_inc_finalize
#define sha256             spx_sha2_256s_sha256
#define sha512_inc_init    spx_sha2_256s_sha512_inc_init
#define sha512_inc_blocks  spx_sha2_256s_sha512_inc_blocks
#define sha512_inc_finalize spx_sha2_256s_sha512_inc_finalize
#define sha512             spx_sha2_256s_sha512
#define randombytes        spx_sha2_256s_randombytes
/* Use explicit vendor paths to avoid trezor-crypto name collisions */
#include "../../vendor/sphincsplus/ref/sign.c"
#include "../../vendor/sphincsplus/ref/address.c"
#include "../../vendor/sphincsplus/ref/merkle.c"
#include "../../vendor/sphincsplus/ref/wots.c"
#include "../../vendor/sphincsplus/ref/wotsx1.c"
#include "../../vendor/sphincsplus/ref/utils.c"
#include "../../vendor/sphincsplus/ref/utilsx1.c"
#include "../../vendor/sphincsplus/ref/fors.c"
#include "../../vendor/sphincsplus/ref/hash_sha2.c"
#include "../../vendor/sphincsplus/ref/thash_sha2_simple.c"
#include "../../vendor/sphincsplus/ref/sha2.c"
#include "randombytes_trezor.c"
