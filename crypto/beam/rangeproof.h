#ifndef _RANGEPROOF_H_
#define _RANGEPROOF_H_

#include "definitions.h"
#include "inner_product.h"
#include "internal.h"
#include "oracle.h"

#define _RANGEPROOF_AMOUNT_MINIMUM_VALUE 1

typedef struct {
  uint8_t seed[32];
  key_idv_t kidv;
} rangeproof_creator_params_t;

#pragma pack(push, 1)
typedef struct {
  uint8_t padding[32 - sizeof(packed_key_idv_t)];
  packed_key_idv_t v;
} rangeproof_creator_params_padded_t;

#pragma pack(pop)

#pragma pack(push, 1)
typedef struct {
  packed_key_id_t kid;
  uint8_t checksum[32];
} rangeproof_public_recovery_t;
#pragma pack(pop)

typedef struct {
  ecc_signature_t signature;
  uint64_t value;

  rangeproof_public_recovery_t recovery;
} rangeproof_public_t;

typedef struct {
  secp256k1_scalar x;
  secp256k1_scalar zz;
} multi_sig_t;

typedef struct {
  // Bulletproof scheme

  struct Part1 {
    point_t a;
    point_t s;
  } part1;

  // <- y,z

  struct Part2 {
    point_t t1;
    point_t t2;
  } part2;

  // <- x

  struct Part3 {
    secp256k1_scalar tauX;
  } part3;

  secp256k1_scalar mu;
  secp256k1_scalar tDot;
  inner_product_t p_tag;
} rangeproof_confidential_t;

typedef struct {
  struct {
    point_t a;
    point_t s;
  } part1;

  struct {
    point_t t1;
    point_t t2;
  } part2;

  struct {
    scalar_packed_t tauX;
  } part3;

  struct {
    point_t LR[INNER_PRODUCT_N_CYCLES][2];
    scalar_packed_t condensed[2];
  } p_tag;

  scalar_packed_t mu;
  scalar_packed_t tDot;
} rangeproof_confidential_packed_t;

typedef struct {
  secp256k1_scalar x, y, z;
  secp256k1_scalar y_inv, zz;
} rangeproof_confidential_challenge_set_t;

typedef struct {
  secp256k1_scalar tau1;
  secp256k1_scalar tau2;
} rangeproof_confidential_multi_sig_t;

typedef enum {
  SINGLE_PASS,  // regular, no multisig
  // STEP_1,
  STEP_2,
  FINALIZE,
} phase_t;

int tag_is_custom(const secp256k1_gej *h_gen);

void tag_add_value(const secp256k1_gej *h_gen, uint64_t value,
                   secp256k1_gej *out);

void asset_tag_commit(const secp256k1_gej *h_gen, const secp256k1_scalar *sk,
                      uint64_t value, secp256k1_gej *out);

void rangeproof_public_xcrypt_kid(packed_key_id_t *kid,
                                  const rangeproof_creator_params_t *cp,
                                  uint8_t *checksum);

void rangeproof_public_get_msg(rangeproof_public_t *rp, uint8_t *hash32,
                               SHA256_CTX *oracle);

void rangeproof_public_create(rangeproof_public_t *out,
                              const secp256k1_scalar *sk,
                              const rangeproof_creator_params_t *cp,
                              SHA256_CTX *oracle);

void rangeproof_creator_params_init(rangeproof_creator_params_t *crp);
void rangeproof_public_init(rangeproof_public_t *public);
void rangeproof_public_recovery_init(rangeproof_public_recovery_t *recovery);

void rangeproof_create_from_key_idv(const HKdf_t *kdf, uint8_t *out,
                                    const key_idv_t *kidv,
                                    const uint8_t *asset_id, uint8_t is_public);

void rangeproof_confidential_create(rangeproof_confidential_t *out,
                                    const secp256k1_scalar *sk,
                                    const rangeproof_creator_params_t *cp,
                                    SHA256_CTX *oracle,
                                    const secp256k1_gej *h_gen);

int rangeproof_confidential_co_sign(rangeproof_confidential_t *out,
                                    const uint8_t *seed_sk,
                                    const secp256k1_scalar *sk,
                                    const rangeproof_creator_params_t *cp,
                                    SHA256_CTX *oracle, phase_t phase,
                                    multi_sig_t *msig_out,
                                    const secp256k1_gej *h_gen);

void rangeproof_confidential_calc_a(point_t *res, const secp256k1_scalar *alpha,
                                    uint64_t value);

void rangeproof_confidential_challenge_set_init_1(
    rangeproof_confidential_challenge_set_t *cs, const struct Part1 *part1,
    SHA256_CTX *oracle);

void rangeproof_confidential_challenge_set_init_2(
    rangeproof_confidential_challenge_set_t *cs, const struct Part2 *part2,
    SHA256_CTX *oracle);

void rangeproof_confidential_multi_sig_init(
    rangeproof_confidential_multi_sig_t *msig, const uint8_t *seed_sk);

void rangeproof_confidential_multi_sig_add_info1(
    rangeproof_confidential_multi_sig_t *msig, secp256k1_gej *pt_t1,
    secp256k1_gej *pt_t2);

void rangeproof_confidential_multi_sig_add_info2(
    rangeproof_confidential_multi_sig_t *msig, secp256k1_scalar *taux,
    const secp256k1_scalar *sk,
    const rangeproof_confidential_challenge_set_t *cs);

void rangeproof_confidential_pack(rangeproof_confidential_packed_t *dest,
                                  rangeproof_confidential_t *src);

#endif  //_RANGEPROOF_H_
