#include "rangeproof.h"
#include "functions.h"
#include "memzero.h"
#include "misc.h"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "beam/lib/secp256k1-zkp/src/field_impl.h"
#include "beam/lib/secp256k1-zkp/src/group_impl.h"
#include "beam/lib/secp256k1-zkp/src/scalar_impl.h"
#pragma GCC diagnostic pop

int tag_is_custom(const secp256k1_gej *h_gen) {
  // secp256k1_gej_is_infinity == 0 means thath h_gen is zero
  return (h_gen != NULL) && (secp256k1_gej_is_infinity(h_gen) == 0);
}

void tag_add_value(const secp256k1_gej *h_gen, uint64_t value,
                   secp256k1_gej *out) {
  secp256k1_scalar value_scalar;
  secp256k1_scalar_set_u64(&value_scalar, value);
  secp256k1_gej mul_result;

  if (tag_is_custom(h_gen))
    gej_mul_scalar(h_gen, &value_scalar, &mul_result);
  else
    generator_mul_scalar(&mul_result, get_context()->generator.H_pts,
                         &value_scalar);

  secp256k1_gej_add_var(out, out, &mul_result, NULL);
}

void asset_tag_commit(const secp256k1_gej *h_gen, const secp256k1_scalar *sk,
                      uint64_t value, secp256k1_gej *out) {
  generator_mul_scalar(out, get_context()->generator.G_pts, sk);
  tag_add_value(h_gen, value, out);
}

void rangeproof_public_xcrypt_kid(packed_key_id_t *kid,
                                  const rangeproof_creator_params_t *cp,
                                  uint8_t *checksum) {
  nonce_generator_t nonce;
  nonce_generator_init(&nonce, (const uint8_t *)"beam-psig", 10);
  nonce_generator_write(&nonce, cp->seed, 32);
  nonce_generator_export_output_key(&nonce, NULL, 0, NULL);
  memxor((uint8_t *)kid, nonce.okm, sizeof(packed_key_id_t));
  nonce_generator_export_output_key(&nonce, NULL, 0, NULL);
  memcpy(checksum, nonce.okm, 32);
}

void rangeproof_public_get_msg(rangeproof_public_t *rp, uint8_t *hash32,
                               SHA256_CTX *oracle) {
  sha256_write_64(oracle, rp->value);
  sha256_Update(oracle, (const uint8_t *)&rp->recovery, sizeof(rp->recovery));
  sha256_oracle_create(oracle, hash32);
}

void rangeproof_public_create(rangeproof_public_t *out,
                              const secp256k1_scalar *sk,
                              const rangeproof_creator_params_t *cp,
                              SHA256_CTX *oracle) {
  out->value = cp->kidv.value;
  if (out->value >= _RANGEPROOF_AMOUNT_MINIMUM_VALUE) {
    memset(&out->recovery.kid, 0, sizeof(out->recovery.kid));
    memset(&out->recovery.checksum, 0, 32);
    assing_aligned(out->recovery.kid.idx, (uint8_t *)&cp->kidv.id.idx,
                   sizeof(out->recovery.kid.idx));
    assing_aligned(out->recovery.kid.type, (uint8_t *)&cp->kidv.id.type,
                   sizeof(out->recovery.kid.type));
    assing_aligned(out->recovery.kid.sub_idx, (uint8_t *)&cp->kidv.id.sub_idx,
                   sizeof(out->recovery.kid.sub_idx));

    rangeproof_public_xcrypt_kid(&(out->recovery.kid), cp,
                                 out->recovery.checksum);

    uint8_t hash_value[32];
    rangeproof_public_get_msg(out, hash_value, oracle);
    signature_sign(hash_value, sk, get_context()->generator.G_pts,
                   &out->signature);
  }
}

void rangeproof_creator_params_init(rangeproof_creator_params_t *crp) {
  memzero(crp->seed, DIGEST_LENGTH);
  key_idv_init(&crp->kidv);
}

void rangeproof_public_init(rangeproof_public_t *public) {
  signature_init(&public->signature);
 public
  ->value = 0;
  rangeproof_public_recovery_init(&public->recovery);
}

void rangeproof_public_recovery_init(rangeproof_public_recovery_t *recovery) {
  memzero(recovery->checksum, DIGEST_LENGTH);
  packed_key_id_init(&recovery->kid);
}

void rangeproof_create_from_key_idv(const HKdf_t *kdf, uint8_t *out,
                                    const key_idv_t *kidv,
                                    const uint8_t *asset_id,
                                    uint8_t is_public) {
  secp256k1_gej h_gen;
  switch_commitment(asset_id, &h_gen);
  secp256k1_gej commitment_native;
  secp256k1_scalar sk;
  switch_commitment_create(&sk, &commitment_native, kdf, kidv, 1, &h_gen);
  // Write results - commitment_native - to point_t
  point_t commitment;
  export_gej_to_point(&commitment_native, &commitment);

  rangeproof_creator_params_t crp;
  crp.kidv.value = kidv->value;
  crp.kidv.id.idx = kidv->id.idx;
  crp.kidv.id.type = kidv->id.type;
  crp.kidv.id.sub_idx = kidv->id.sub_idx;
  get_seed_kid_from_commitment(&commitment, crp.seed, kdf);

  SHA256_CTX oracle;
  sha256_Init(&oracle);

  if (is_public) {
    rangeproof_public_t rp;
    rangeproof_public_create(&rp, &sk, &crp, &oracle);
    memcpy(out, (void *)&rp, sizeof(rp));
  } else {
    // prepare output
    uint64_t incubation = 0;
    sha256_write_64(&oracle, incubation);
    sha256_oracle_update_pt(&oracle, &commitment);

    rangeproof_confidential_t rp;
    rangeproof_confidential_packed_t rp_packed;
    rangeproof_confidential_create(&rp, &sk, &crp, &oracle, &h_gen);
    rangeproof_confidential_pack(&rp_packed, &rp);

    memcpy(out, (void *)&rp_packed, sizeof(rp_packed));
  }
}

void rangeproof_confidential_create(rangeproof_confidential_t *out,
                                    const secp256k1_scalar *sk,
                                    const rangeproof_creator_params_t *cp,
                                    SHA256_CTX *oracle,
                                    const secp256k1_gej *h_gen) {
  // single-pass - use both deterministic and random seed for key blinding.
  // For more safety - use the current oracle state

  SHA256_CTX copy_oracle;
  memcpy(&copy_oracle, oracle, sizeof(SHA256_CTX));
  uint8_t seed_sk[32];

#ifdef BEAM_DEBUG
  memset(seed_sk, 1, 32);
#else
  random_buffer(seed_sk, sizeof(seed_sk));
#endif

  sha256_oracle_update_sk(&copy_oracle, sk);
  sha256_Update(&copy_oracle, seed_sk, sizeof(seed_sk));
  sha256_write_64(&copy_oracle, cp->kidv.value);
  sha256_oracle_create(&copy_oracle, seed_sk);

  rangeproof_confidential_co_sign(out, seed_sk, sk, cp, oracle, SINGLE_PASS,
                                  NULL, h_gen);
}

int rangeproof_confidential_co_sign(rangeproof_confidential_t *out,
                                    const uint8_t *seed_sk,
                                    const secp256k1_scalar *sk,
                                    const rangeproof_creator_params_t *cp,
                                    SHA256_CTX *oracle, phase_t phase,
                                    multi_sig_t *msig_out,
                                    const secp256k1_gej *h_gen) {
  nonce_generator_t nonce;
  nonce_generator_init(&nonce, (const uint8_t *)"bulletproof", 12);
  nonce_generator_write(&nonce, cp->seed, 32);

  // A = G*alpha + vec(aL)*vec(G) + vec(aR)*vec(H)
  secp256k1_scalar alpha, ro;
  nonce_generator_export_scalar(&nonce, NULL, 0, &alpha);

  // embed extra params into alpha
  static_assert(sizeof(packed_key_idv_t) < 32);
  static_assert(sizeof(rangeproof_creator_params_padded_t) == 32);
  rangeproof_creator_params_padded_t pad;
  memset(pad.padding, 0, sizeof(pad.padding));
  assing_aligned(pad.v.id.idx, (uint8_t *)&cp->kidv.id.idx,
                 sizeof(pad.v.id.idx));
  assing_aligned(pad.v.id.type, (uint8_t *)&cp->kidv.id.type,
                 sizeof(pad.v.id.type));
  assing_aligned(pad.v.id.sub_idx, (uint8_t *)&cp->kidv.id.sub_idx,
                 sizeof(pad.v.id.sub_idx));
  assing_aligned(pad.v.value, (uint8_t *)&cp->kidv.value, sizeof(pad.v.value));

  int overflow;
  secp256k1_scalar_set_b32(&ro, (const uint8_t *)&pad, &overflow);
  if (scalar_import_nnz(&ro, (const uint8_t *)&pad)) {
    // if overflow - the params won't be recovered properly, there may be
    // ambiguity
  }

  secp256k1_scalar_add(&alpha, &alpha, &ro);

  rangeproof_confidential_calc_a(&out->part1.a, &alpha, cp->kidv.value);

  // S = G*ro + vec(sL)*vec(G) + vec(sR)*vec(H)
  nonce_generator_export_scalar(&nonce, NULL, 0, &ro);

  secp256k1_scalar p_s[2][INNER_PRODUCT_N_DIM];
  secp256k1_gej comm;
  {
    multi_mac_t mm;
    multi_mac_with_bufs_alloc(&mm, 1, INNER_PRODUCT_N_DIM * 2 + 1);
    mm.k_prepared[mm.n_prepared] = ro;
    mm.prepared[mm.n_prepared++] = (multi_mac_prepared_t *)get_generator_G();

    for (int j = 0; j < 2; j++)
      for (uint32_t i = 0; i < INNER_PRODUCT_N_DIM; i++) {
        nonce_generator_export_scalar(&nonce, NULL, 0, &p_s[j][i]);

        mm.k_prepared[mm.n_prepared] = p_s[j][i];
        mm.prepared[mm.n_prepared++] =
            (multi_mac_prepared_t *)get_generator_ipp(i, j, 0);
      }

    multi_mac_calculate(&mm, &comm);
    multi_mac_with_bufs_free(&mm);
    export_gej_to_point(&comm, &out->part1.s);
  }

  rangeproof_confidential_challenge_set_t cs;
  rangeproof_confidential_challenge_set_init_1(&cs, &out->part1, oracle);
  secp256k1_scalar t0, t1, t2;
  secp256k1_scalar_clear(&t0);
  secp256k1_scalar_clear(&t1);
  secp256k1_scalar_clear(&t2);
  secp256k1_scalar l0, r0, rx, one, two, yPwr, zz_twoPwr;
  secp256k1_scalar_set_int(&one, 1U);
  secp256k1_scalar_set_int(&two, 2U);

  memcpy(&yPwr, &one, sizeof(secp256k1_scalar));
  memcpy(&zz_twoPwr, &cs.zz, sizeof(secp256k1_scalar));

  for (uint32_t i = 0; i < INNER_PRODUCT_N_DIM; i++) {
    uint32_t bit = 1 & (cp->kidv.value >> i);

    secp256k1_scalar_negate(&l0, &cs.z);
    if (bit) {
      secp256k1_scalar_add(&l0, &l0, &one);
    }

    const secp256k1_scalar *lx = &p_s[0][i];
    memcpy(&r0, &cs.z, sizeof(secp256k1_scalar));
    if (!bit) {
      secp256k1_scalar minus_one;
      secp256k1_scalar_negate(&minus_one, &one);
      secp256k1_scalar_add(&r0, &r0, &minus_one);
    }

    secp256k1_scalar_mul(&r0, &r0, &yPwr);
    secp256k1_scalar_add(&r0, &r0, &zz_twoPwr);

    memcpy(&rx, &yPwr, sizeof(secp256k1_scalar));
    secp256k1_scalar_mul(&rx, &rx, &p_s[1][i]);

    secp256k1_scalar_mul(&zz_twoPwr, &zz_twoPwr, &two);
    secp256k1_scalar_mul(&yPwr, &yPwr, &cs.y);

    secp256k1_scalar tmp;

    secp256k1_scalar_mul(&tmp, &l0, &r0);
    secp256k1_scalar_add(&t0, &t0, &tmp);

    secp256k1_scalar_mul(&tmp, &l0, &rx);
    secp256k1_scalar_add(&t1, &t1, &tmp);

    secp256k1_scalar_mul(&tmp, lx, &r0);
    secp256k1_scalar_add(&t1, &t1, &tmp);

    secp256k1_scalar_mul(&tmp, lx, &rx);
    secp256k1_scalar_add(&t2, &t2, &tmp);
  }

  rangeproof_confidential_multi_sig_t msig;
  rangeproof_confidential_multi_sig_init(&msig, seed_sk);

  if (FINALIZE !=
      phase)  // otherwise part2 already contains the whole aggregate
  {
    secp256k1_gej comm2;
    rangeproof_confidential_multi_sig_add_info1(&msig, &comm, &comm2);

    if (tag_is_custom(h_gen)) {
      // since we need 2 multiplications - prepare it explicitly.
      multi_mac_casual_t mc;
      multi_mac_casual_init_new(&mc, h_gen);

      multi_mac_t mm2;
      multi_mac_reset(&mm2);
      mm2.casual = &mc;
      mm2.n_casual = 1;
      secp256k1_gej comm3;
      memcpy(&mc.k, &t1, sizeof(secp256k1_scalar));
      multi_mac_calculate(&mm2, &comm3);
      secp256k1_gej_add_var(&comm, &comm, &comm3, NULL);

      memcpy(&mc.k, &t2, sizeof(secp256k1_scalar));
      multi_mac_calculate(&mm2, &comm3);
      secp256k1_gej_add_var(&comm2, &comm2, &comm3, NULL);
    } else {
      secp256k1_gej tmp;
      generator_mul_scalar(&tmp, get_context()->generator.H_pts, &t1);
      secp256k1_gej_add_var(&comm, &comm, &tmp, NULL);

      generator_mul_scalar(&tmp, get_context()->generator.H_pts, &t2);
      secp256k1_gej_add_var(&comm2, &comm2, &tmp, NULL);
    }

    if (SINGLE_PASS != phase) {
      secp256k1_gej p;

      if (!point_import(&p, &out->part2.t1)) return 0;
      secp256k1_gej_add_var(&comm, &comm, &p, NULL);

      if (!point_import(&p, &out->part2.t2)) return 0;
      secp256k1_gej_add_var(&comm2, &comm2, &p, NULL);
    }

    export_gej_to_point(&comm, &out->part2.t1);
    export_gej_to_point(&comm2, &out->part2.t2);
  }

  rangeproof_confidential_challenge_set_init_2(&cs, &out->part2, oracle);

  if (msig_out) {
    memcpy(&msig_out->x, &cs.x, sizeof(secp256k1_scalar));
    memcpy(&msig_out->zz, &cs.zz, sizeof(secp256k1_scalar));
  }

  if (STEP_2 == phase) return 1;  // stop after T1,T2 calculated

  // m_TauX = tau2*x^2 + tau1*x + sk*z^2
  rangeproof_confidential_multi_sig_add_info2(&msig, &l0, sk, &cs);

  if (SINGLE_PASS != phase) secp256k1_scalar_add(&l0, &l0, &out->part3.tauX);

  memcpy(&out->part3.tauX, &l0, sizeof(secp256k1_scalar));

  // m_Mu = alpha + ro*x
  memcpy(&l0, &ro, sizeof(secp256k1_scalar));
  secp256k1_scalar_mul(&l0, &l0, &cs.x);
  secp256k1_scalar_add(&l0, &l0, &alpha);
  memcpy(&out->mu, &l0, sizeof(secp256k1_scalar));

  // m_tDot
  memcpy(&l0, &t0, sizeof(secp256k1_scalar));

  memcpy(&r0, &t1, sizeof(secp256k1_scalar));
  secp256k1_scalar_mul(&r0, &r0, &cs.x);
  secp256k1_scalar_add(&l0, &l0, &r0);

  memcpy(&r0, &t2, sizeof(secp256k1_scalar));
  secp256k1_scalar_mul(&r0, &r0, &cs.x);
  secp256k1_scalar_mul(&r0, &r0, &cs.x);
  secp256k1_scalar_add(&l0, &l0, &r0);

  memcpy(&out->tDot, &l0, sizeof(secp256k1_scalar));

  // construct vectors l,r, use buffers pS
  // P - m_Mu*G
  memcpy(&yPwr, &one, sizeof(secp256k1_scalar));
  memcpy(&zz_twoPwr, &cs.zz, sizeof(secp256k1_scalar));

  for (uint32_t i = 0; i < INNER_PRODUCT_N_DIM; i++) {
    uint32_t bit = 1 & (cp->kidv.value >> i);

    secp256k1_scalar_mul(&p_s[0][i], &p_s[0][i], &cs.x);

    secp256k1_scalar minus_cs_z;
    secp256k1_scalar_negate(&minus_cs_z, &cs.z);
    secp256k1_scalar_add(&p_s[0][i], &p_s[0][i], &minus_cs_z);

    if (bit) secp256k1_scalar_add(&p_s[0][i], &p_s[0][i], &one);

    secp256k1_scalar_mul(&p_s[1][i], &p_s[1][i], &cs.x);
    secp256k1_scalar_mul(&p_s[1][i], &p_s[1][i], &yPwr);

    memcpy(&r0, &cs.z, sizeof(secp256k1_scalar));
    if (!bit) {
      secp256k1_scalar minus_one;
      secp256k1_scalar_negate(&minus_one, &one);
      secp256k1_scalar_add(&r0, &r0, &minus_one);
    }

    secp256k1_scalar_mul(&r0, &r0, &yPwr);
    secp256k1_scalar_add(&r0, &r0, &zz_twoPwr);

    secp256k1_scalar_add(&p_s[1][i], &p_s[1][i], &r0);

    secp256k1_scalar_mul(&zz_twoPwr, &zz_twoPwr, &two);
    secp256k1_scalar_mul(&yPwr, &yPwr, &cs.y);
  }

  inner_product_modifier_t mod;
  inner_product_modifier_init(&mod);
  mod.multiplier[1] = &cs.y_inv;

  inner_product_create(&out->p_tag, oracle, NULL, &l0, p_s[0], p_s[1], &mod);

  return 1;
}

void data_cmov_as(uint32_t *pDst, const uint32_t *pSrc, int nWords, int flag) {
  const uint32_t mask0 = flag + ~((uint32_t)0);
  const uint32_t mask1 = ~mask0;

  for (int n = 0; n < nWords; n++)
    pDst[n] = (pDst[n] & mask0) | (pSrc[n] & mask1);
}

void gej_cmov(secp256k1_gej *dst, const secp256k1_gej *src, int flag) {
  static_assert(sizeof(secp256k1_gej) % sizeof(uint32_t) == 0);
  data_cmov_as((uint32_t *)dst, (uint32_t *)src,
               sizeof(secp256k1_gej) / sizeof(uint32_t), flag);
}

void rangeproof_confidential_calc_a(point_t *res, const secp256k1_scalar *alpha,
                                    uint64_t value) {
  secp256k1_gej comm;
  generator_mul_scalar(&comm, get_context()->generator.G_pts, alpha);

  {
    secp256k1_gej ge_s;

    for (uint32_t i = 0; i < INNER_PRODUCT_N_DIM; i++) {
      uint32_t iBit = 1 & (value >> i);

      // protection against side-channel attacks
      gej_cmov(&ge_s, &get_generator_get1_minus()[i], 0 == iBit);
      gej_cmov(&ge_s,
               &((multi_mac_prepared_t *)get_generator_ipp(i, 0, 0))->pt[0],
               1 == iBit);

      secp256k1_gej_add_var(&comm, &comm, &ge_s, NULL);
    }
  }

  export_gej_to_point(&comm, res);
}

void rangeproof_confidential_challenge_set_init_1(
    rangeproof_confidential_challenge_set_t *cs, const struct Part1 *part1,
    SHA256_CTX *oracle) {
  sha256_oracle_update_pt(oracle, &part1->a);
  sha256_oracle_update_pt(oracle, &part1->s);

  scalar_create_nnz(oracle, &cs->y);
  scalar_create_nnz(oracle, &cs->z);

  secp256k1_scalar_inverse(&cs->y_inv, &cs->y);
  memcpy(&cs->zz, &cs->z, sizeof(secp256k1_scalar));
  secp256k1_scalar_mul(&cs->zz, &cs->zz, &cs->z);
}

void rangeproof_confidential_challenge_set_init_2(
    rangeproof_confidential_challenge_set_t *cs, const struct Part2 *part2,
    SHA256_CTX *oracle) {
  sha256_oracle_update_pt(oracle, &part2->t1);
  sha256_oracle_update_pt(oracle, &part2->t2);

  scalar_create_nnz(oracle, &cs->x);
}

void rangeproof_confidential_multi_sig_init(
    rangeproof_confidential_multi_sig_t *msig, const uint8_t *seed_sk) {
  nonce_generator_t nonce;
  nonce_generator_init(&nonce, (const uint8_t *)"bp-key", 7);
  nonce_generator_write(&nonce, seed_sk, 32);
  nonce_generator_export_scalar(&nonce, NULL, 0, &msig->tau1);
  nonce_generator_export_scalar(&nonce, NULL, 0, &msig->tau2);
}

void rangeproof_confidential_multi_sig_add_info1(
    rangeproof_confidential_multi_sig_t *msig, secp256k1_gej *pt_t1,
    secp256k1_gej *pt_t2) {
  generator_mul_scalar(pt_t1, get_context()->generator.G_pts, &msig->tau1);
  generator_mul_scalar(pt_t2, get_context()->generator.G_pts, &msig->tau2);
}

void rangeproof_confidential_multi_sig_add_info2(
    rangeproof_confidential_multi_sig_t *msig, secp256k1_scalar *taux,
    const secp256k1_scalar *sk,
    const rangeproof_confidential_challenge_set_t *cs) {
  // taux = tau2*x^2 + tau1*x + sk*z^2
  memcpy(taux, &msig->tau2, sizeof(secp256k1_scalar));
  secp256k1_scalar_mul(taux, taux, &cs->x);
  secp256k1_scalar_mul(taux, taux, &cs->x);

  secp256k1_scalar t1;
  memcpy(&t1, &msig->tau1, sizeof(secp256k1_scalar));
  secp256k1_scalar_mul(&t1, &t1, &cs->x);
  secp256k1_scalar_add(taux, taux, &t1);

  memcpy(&t1, &cs->zz, sizeof(secp256k1_scalar));
  secp256k1_scalar_mul(&t1, &t1, sk);
  secp256k1_scalar_add(taux, taux, &t1);
}

void rangeproof_confidential_pack(rangeproof_confidential_packed_t *dest,
                                  rangeproof_confidential_t *src) {
  memcpy(&dest->part1, &src->part1, sizeof(dest->part1));
  memcpy(&dest->part2, &src->part2, sizeof(dest->part2));
  secp256k1_scalar_get_b32(dest->part3.tauX, &src->part3.tauX);

  memcpy(dest->p_tag.LR, src->p_tag.LR, sizeof(dest->p_tag.LR));
  const size_t condensed_count =
      sizeof(dest->p_tag.condensed) / sizeof(scalar_packed_t);
  for (size_t i = 0; i < condensed_count; i++)
    secp256k1_scalar_get_b32(dest->p_tag.condensed[i],
                             &src->p_tag.condensed[i]);

  secp256k1_scalar_get_b32(dest->mu, &src->mu);
  secp256k1_scalar_get_b32(dest->tDot, &src->tDot);
}
