#include "kernel.h"
#include <string.h>
#include "../rand.h"
#include "functions.h"
#include "internal.h"
#include "misc.h"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "beam/lib/secp256k1-zkp/src/field_impl.h"
#include "beam/lib/secp256k1-zkp/src/group_impl.h"
#include "beam/lib/secp256k1-zkp/src/scalar_impl.h"
#pragma GCC diagnostic pop

// sk0_J is a result of multiplication of derived key and generator J
void switch_commitment_get_sk1(const secp256k1_gej* commitment,
                               const secp256k1_gej* sk0_j,
                               secp256k1_scalar* scalar_out) {
  SHA256_CTX x;
  sha256_Init(&x);

  point_t commitment_point;
  export_gej_to_point((secp256k1_gej*)commitment, &commitment_point);

  point_t sk0_j_point;
  export_gej_to_point((secp256k1_gej*)sk0_j, &sk0_j_point);

  sha256_Update(&x, commitment_point.x, DIGEST_LENGTH);
  sha256_write_8(&x, commitment_point.y);
  sha256_Update(&x, sk0_j_point.x, DIGEST_LENGTH);
  sha256_write_8(&x, sk0_j_point.y);

  uint8_t scalar_res[32];
  sha256_Final(&x, scalar_res);
  scalar_import_nnz(scalar_out, scalar_res);
}

void switch_commitment(const uint8_t* asset_id, secp256k1_gej* h_gen) {
  if (asset_id && !(memis0(asset_id, 32))) {
    SHA256_CTX oracle;
    sha256_Init(&oracle);
    sha256_Update(&oracle, (const uint8_t*)"a-id", 5);
    sha256_Update(&oracle, asset_id, 32);

    point_t pt;
    pt.y = 0;

    do {
      sha256_Update(&oracle, (const uint8_t*)"a-gen", 6);

      SHA256_CTX new_oracle;
      memcpy(&new_oracle, &oracle, sizeof(SHA256_CTX));
      sha256_Final(&new_oracle, pt.x);

      sha256_Update(&oracle, pt.x, SHA256_DIGEST_LENGTH);
    } while (!point_import_nnz(h_gen, &pt));
  } else {
    secp256k1_gej_set_infinity(h_gen);
  }
}

void create_common_kidv_image(const HKdf_t* kdf, const key_idv_t* kidv,
                              secp256k1_gej* out_commitment) {
  uint8_t hash_id[DIGEST_LENGTH];
  generate_hash_id(kidv->id.idx, kidv->id.type, kidv->id.sub_idx, hash_id);

  secp256k1_scalar sk;
  derive_key(kdf->generator_secret, DIGEST_LENGTH, hash_id, DIGEST_LENGTH,
             &kdf->cofactor, &sk);

  // Multiply key by generator G
  generator_mul_scalar(out_commitment, get_context()->generator.G_pts, &sk);
}

void create_kidv_image(const HKdf_t* kdf, const key_idv_t* kidv,
                       secp256k1_gej* out_commitment, uint8_t create_coin_key) {
  if (create_coin_key) {
    secp256k1_scalar sk;
    // As we would have no asset id, we should have infinitiy (or NULL) h_gen
    switch_commitment_create(&sk, out_commitment, kdf, kidv, 1, NULL);
  } else {
    create_common_kidv_image(kdf, kidv, out_commitment);
  }
}

void switch_commitment_get_hash(const key_idv_t* kidv, uint8_t* hash_id) {
  const uint32_t scheme = kidv_get_scheme(kidv);
  if (scheme > KIDV_SCHEME_V0) {
    if (scheme == KIDV_SCHEME_BB21) {
      // BB2.1 workaround
      key_idv_t kidv2;
      memcpy(&kidv2, kidv, sizeof(key_id_t));
      kidv_set_subkey(&kidv2, kidv_get_subkey(kidv), KIDV_SCHEME_V0);
      generate_hash_id(kidv2.id.idx, kidv2.id.type, kidv2.id.sub_idx, hash_id);
    } else {
      // newer scheme - account for the Value.
      // Make it infeasible to tamper with value for unknown blinding factor
      SHA256_CTX x;
      sha256_Init(&x);
      sha256_Update(&x, (const uint8_t*)"kidv-1", 7);
      sha256_write_64(&x, kidv->id.idx);
      sha256_write_64(&x, kidv->id.type);
      sha256_write_64(&x, kidv->id.sub_idx);
      sha256_write_64(&x, kidv->value);
      sha256_Final(&x, hash_id);
    }
  } else {
    generate_hash_id(kidv->id.idx, kidv->id.type, kidv->id.sub_idx, hash_id);
  }
}

void switch_commitment_create(secp256k1_scalar* sk, secp256k1_gej* commitment,
                              const HKdf_t* kdf, const key_idv_t* kidv,
                              uint8_t has_commitment,
                              const secp256k1_gej* h_gen) {
  uint8_t hash_id[DIGEST_LENGTH];
  switch_commitment_get_hash(kidv, hash_id);

  derive_key(kdf->generator_secret, DIGEST_LENGTH, hash_id, DIGEST_LENGTH,
             &kdf->cofactor, sk);

  // Multiply key by generator G
  generator_mul_scalar(commitment, get_context()->generator.G_pts, sk);
  tag_add_value(h_gen, kidv->value, commitment);

  // Multiply key by generator J
  secp256k1_gej key_j_mul_result;
  generator_mul_scalar(&key_j_mul_result, get_context()->generator.J_pts, sk);

  secp256k1_scalar sk1;
  switch_commitment_get_sk1(commitment, &key_j_mul_result, &sk1);
  secp256k1_scalar_add(sk, sk, &sk1);

  if (has_commitment) {
    secp256k1_gej sk1_g_mul_result;
    generator_mul_scalar(&sk1_g_mul_result, get_context()->generator.G_pts,
                         &sk1);
    secp256k1_gej_add_var(commitment, commitment, &sk1_g_mul_result, NULL);
  }
}

void peer_finalize_excess(secp256k1_scalar* peer_scalar, secp256k1_gej* kG,
                          secp256k1_scalar* k_offset) {
  secp256k1_scalar_add(k_offset, k_offset, peer_scalar);

  uint8_t random_scalar_data[DIGEST_LENGTH];
#ifdef BEAM_DEBUG
  test_set_buffer(random_scalar_data, DIGEST_LENGTH, 3);
#else
  random_buffer(random_scalar_data, DIGEST_LENGTH);
#endif
  secp256k1_scalar_set_b32(peer_scalar, random_scalar_data, NULL);
  secp256k1_scalar_add(k_offset, k_offset, peer_scalar);

  secp256k1_scalar_negate(peer_scalar, peer_scalar);

  secp256k1_gej peer_scalar_mul_g;
  generator_mul_scalar(&peer_scalar_mul_g, get_context()->generator.G_pts,
                       peer_scalar);
  secp256k1_gej_add_var(kG, kG, &peer_scalar_mul_g, NULL);
}

void peer_add_input(tx_inputs_vec_t* tx_inputs, secp256k1_scalar* peer_scalar,
                    uint64_t val, HKdf_t* kdf, const uint8_t* asset_id) {
  tx_input_t* input = malloc(sizeof(tx_input_t));
  tx_input_init(input);

  key_idv_t kidv;
  key_idv_init(&kidv);
  kidv.value = val;

  secp256k1_scalar k;
  secp256k1_gej h_gen;
  switch_commitment(asset_id, &h_gen);
  secp256k1_gej commitment_native;
  point_import_nnz(&commitment_native, &input->tx_element.commitment);
  switch_commitment_create(&k, &commitment_native, kdf, &kidv, 1, &h_gen);
  // Write result back to TxInput
  export_gej_to_point(&commitment_native, &input->tx_element.commitment);

  // Push TxInput to vec of inputs
  vec_push(tx_inputs, input);

  secp256k1_scalar_add(peer_scalar, peer_scalar, &k);
}

void tx_output_create(tx_output_t* output, secp256k1_scalar* sk,
                      HKdf_t* coin_kdf, const key_idv_t* kidv, HKdf_t* tag_kdf,
                      uint8_t is_public) {
  secp256k1_gej h_gen;
  switch_commitment(output->asset_id, &h_gen);
  secp256k1_gej commitment_native;
  switch_commitment_create(sk, &commitment_native, coin_kdf, kidv, 1, &h_gen);
  // Write results - commitment_native - to TxOutput
  export_gej_to_point(&commitment_native, &output->tx_element.commitment);

  SHA256_CTX oracle;
  sha256_Init(&oracle);
  sha256_write_64(&oracle, output->incubation_height);

  // TODO
  rangeproof_creator_params_t crp;
  rangeproof_creator_params_init(&crp);
  crp.kidv = *kidv;
  tx_output_get_seed_kid(output, crp.seed, tag_kdf);

  if (is_public || output->is_coinbase) {
    output->public_proof->value = kidv->value;
    rangeproof_public_create(output->public_proof, sk, &crp, &oracle);
  } else {
    rangeproof_confidential_create(output->confidential_proof, sk, &crp,
                                   &oracle, &h_gen);
    // TODO
    // m_pConfidential.reset(new ECC::RangeProof::Confidential);
    // m_pConfidential->Create(sk, cp, oracle, &sc.m_hGen);
  }
}

void tx_output_get_seed_kid(const tx_output_t* output, uint8_t* seed,
                            HKdf_t* kdf) {
  get_seed_kid_from_commitment(&output->tx_element.commitment, seed, kdf);
}

void peer_add_output(tx_outputs_vec_t* tx_outputs,
                     secp256k1_scalar* peer_scalar, uint64_t val, HKdf_t* kdf,
                     const uint8_t* asset_id) {
  tx_output_t* output = malloc(sizeof(tx_output_t));
  tx_output_init(output);

  key_idv_t kidv;
  key_idv_init(&kidv);
  kidv.value = val;

  const uint8_t is_empty_asset_id =
      (asset_id == NULL) || memis0(asset_id, DIGEST_LENGTH);
  if (!is_empty_asset_id) memcpy(output->asset_id, asset_id, DIGEST_LENGTH);

  secp256k1_scalar k;
  const int is_public = 0;
  tx_output_create(output, &k, kdf, &kidv, kdf, is_public);

  // TODO: not sure if we need this on Trezor
  //// test recovery
  // Key::IDV kidv2;
  // verify_test(pOut->Recover(kdf, kidv2));
  // verify_test(kidv == kidv2);

  // Push TxOutput to vec of outputs
  vec_push(tx_outputs, output);

  secp256k1_scalar_negate(&k, &k);
  secp256k1_scalar_add(peer_scalar, peer_scalar, &k);
}

// AmountBig::Type is 128 bits = 16 bytes
int kernel_traverse(const tx_kernel_t* kernel, const tx_kernel_t* parent_kernel,
                    const uint8_t* hash_lock_preimage, uint8_t* hash_value,
                    uint64_t* fee, secp256k1_gej* excess) {
  if (parent_kernel) {
    // Nested kernel restrictions
    if ((kernel->kernel.min_height > parent_kernel->kernel.min_height) ||
        (kernel->kernel.max_height < parent_kernel->kernel.max_height)) {
      // Parent Height range must be contained in ours
      return 0;
    }
  }

  SHA256_CTX hp;
  sha256_Init(&hp);
  sha256_write_64(&hp, kernel->kernel.fee);
  sha256_write_64(&hp, kernel->kernel.min_height);
  sha256_write_64(&hp, kernel->kernel.max_height);
  sha256_Update(&hp, kernel->kernel.tx_element.commitment.x, DIGEST_LENGTH);
  sha256_write_8(&hp, kernel->kernel.tx_element.commitment.y);
  sha256_write_64(&hp, kernel->kernel.asset_emission);
  const uint8_t is_empty_kernel_hash_lock_preimage =
      memis0(kernel->kernel.hash_lock_preimage, DIGEST_LENGTH);
  const uint8_t is_non_empty_kernel_hash_lock_preimage =
      !is_empty_kernel_hash_lock_preimage;
  sha256_write_8(&hp, is_non_empty_kernel_hash_lock_preimage);

  if (is_non_empty_kernel_hash_lock_preimage) {
    if (!hash_lock_preimage) {
      SHA256_CTX hash_lock_ctx;
      sha256_Update(&hash_lock_ctx, kernel->kernel.hash_lock_preimage,
                    DIGEST_LENGTH);
      sha256_Final(&hash_lock_ctx, hash_value);

      // TODO: if this correct?
      // pLockImage = &hv;
      hash_lock_preimage = hash_value;
    }

    sha256_Update(&hp, hash_lock_preimage, DIGEST_LENGTH);
  }

  secp256k1_gej point_excess_nested;
  if (excess) secp256k1_gej_set_infinity(&point_excess_nested);

  const tx_kernel_t* zero_kernel = NULL;
  UNUSED(zero_kernel);
  for (size_t i = 0; i < (size_t)kernel->nested_kernels.length; ++i) {
    const uint8_t should_break = 0;
    sha256_write_8(&hp, should_break);

    // TODO: to implement. Do we really need this on Trezor?
    // const TxKernel& v = *(*it);
    // if (p0Krn && (*p0Krn > v))
    //    return false;
    // p0Krn = &v;

    // if (!v.Traverse(hv, pFee, pExcess ? &ptExcNested : NULL, this, NULL))
    //    return false;

    // hp << hv;
  }
  const uint8_t should_break = 1;
  sha256_write_8(&hp, should_break);
  sha256_Final(&hp, hash_value);

  if (excess) {
    secp256k1_gej pt;
    if (!point_import_nnz(&pt, &kernel->kernel.tx_element.commitment)) return 0;

    secp256k1_gej_neg(&point_excess_nested, &point_excess_nested);
    secp256k1_gej_add_var(&point_excess_nested, &point_excess_nested, &pt,
                          NULL);

    if (!signature_is_valid(hash_value, &kernel->kernel.signature,
                            &point_excess_nested,
                            get_context()->generator.G_pts))
      return 0;

    secp256k1_gej_add_var(excess, excess, &pt, NULL);

    // TODO: do we need support for the asset emission? Seems no
    // if (kernel_emission->kernel.asset_emission)
    //{
    // TODO: do we need this on the device?
    // if (!Rules::get().CA.Enabled)
    //    return false;
    //
    // Ban complex cases. Emission kernels must be simple
    // if (parent_kernel || kernel->nested_kernels.length != 0)
    //    return false;
    //}
  }
  if (fee) {
    *fee += kernel->kernel.fee;
  }

  return 1;
}

void kernel_get_hash(const tx_kernel_t* kernel,
                     const uint8_t* hash_lock_preimage, uint8_t* out) {
  kernel_traverse(kernel, NULL, hash_lock_preimage, out, NULL, NULL);
}

// 1st pass. Public excesses and Nonces are summed.
void cosign_kernel_part_1(tx_kernel_t* kernel, secp256k1_gej* kG,
                          secp256k1_gej* xG, secp256k1_scalar* peer_scalars,
                          secp256k1_scalar* peer_nonces, size_t num_peers,
                          secp256k1_scalar* transaction_offset,
                          uint8_t* kernel_hash_message,
                          const uint8_t* hash_lock_preimage) {
  for (size_t i = 0; i < num_peers; ++i) {
    peer_finalize_excess(&peer_scalars[i], kG, transaction_offset);

    // Nonces are initialized as a random buffer
    uint8_t random_scalar_data[DIGEST_LENGTH];
#ifdef BEAM_DEBUG
    test_set_buffer(random_scalar_data, DIGEST_LENGTH, 3);
#else
    random_buffer(random_scalar_data, DIGEST_LENGTH);
#endif
    secp256k1_scalar_set_b32(&peer_nonces[i], random_scalar_data, NULL);
    secp256k1_gej nonce_mul_g;
    generator_mul_scalar(&nonce_mul_g, get_context()->generator.G_pts,
                         &peer_nonces[i]);
    secp256k1_gej_add_var(xG, xG, &nonce_mul_g, NULL);
  }

  for (size_t i = 0; i < (size_t)kernel->nested_kernels.length; ++i) {
    secp256k1_gej nested_point;
    point_import_nnz(&nested_point,
                     &kernel->nested_kernels.data[i]->tx_element.commitment);
    // TODO: import
    // verify_test(ptNested.Import(krn.m_vNested[i]->m_Commitment));
    secp256k1_gej_add_var(kG, kG, &nested_point, NULL);
  }

  export_gej_to_point(kG, &kernel->kernel.tx_element.commitment);

  kernel_get_hash(kernel, hash_lock_preimage, kernel_hash_message);
}

// 2nd pass. Signing. Total excess is the signature public key.
void cosign_kernel_part_2(tx_kernel_t* kernel, secp256k1_gej* xG,
                          secp256k1_scalar* peer_scalars,
                          secp256k1_scalar* peer_nonces, size_t num_peers,
                          uint8_t* kernel_hash_message) {
  secp256k1_scalar k_sig;
  secp256k1_scalar_set_int(&k_sig, 0);

  for (size_t i = 0; i < num_peers; ++i) {
    ecc_signature_t sig;
    sig.nonce_pub = *xG;

    secp256k1_scalar multisig_nonce = peer_nonces[i];

    secp256k1_scalar k;
    signature_sign_partial(&multisig_nonce, &sig.nonce_pub, kernel_hash_message,
                           &peer_scalars[i], &k);
    secp256k1_scalar_add(&k_sig, &k_sig, &k);
    // Signed, prepare for next tx
    secp256k1_scalar_set_int(&peer_scalars[i], 0);
  }

  kernel->kernel.signature.nonce_pub = *xG;
  kernel->kernel.signature.k = k_sig;
}

void create_tx_kernel(tx_kernels_vec_t* trg_kernels,
                      tx_kernels_vec_t* nested_kernels, uint64_t fee,
                      uint8_t should_emit_custom_tag) {
  tx_kernel_t* kernel = malloc(sizeof(tx_kernel_t));
  kernel->kernel.fee = fee;
  // TODO<Kirill A>: be careful to move data out of the vector
  memmove(kernel->nested_kernels.data, nested_kernels->data,
          nested_kernels->length * sizeof(tx_kernel_t));

  uint8_t preimage[DIGEST_LENGTH];
#ifdef BEAM_DEBUG
  test_set_buffer(preimage, DIGEST_LENGTH, 3);
#else
  random_buffer(preimage, 32);
#endif

  uint8_t lock_image[DIGEST_LENGTH];
  SHA256_CTX x;
  sha256_Init(&x);
  sha256_Update(&x, preimage, DIGEST_LENGTH);
  sha256_Final(&x, lock_image);

  if (should_emit_custom_tag) {
    uint8_t sk_asset_data[DIGEST_LENGTH];
    random_buffer(sk_asset_data, DIGEST_LENGTH);
    secp256k1_scalar sk_asset;
    scalar_import_nnz(&sk_asset, sk_asset_data);

    uint8_t aid[DIGEST_LENGTH];
    sk_to_pk(&sk_asset, get_context()->generator.G_pts, aid);

    uint64_t val_asset = 4431;

    // TODO<Kirill A>: do wee need this at all on Trezor?
    // if (beam::Rules::get().CA.Deposit)
    //    m_pPeers[0].AddInput(m_Trans, valAsset, m_Kdf); // input
    //    being-deposited

    // m_pPeers[0].AddOutput(m_Trans, valAsset, m_Kdf, &aid); // output UTXO to
    // consume the created asset

    tx_kernel_t* kernel_emission = malloc(sizeof(tx_kernel_t));
    kernel_emission->kernel.asset_emission = val_asset;
    // TODO<Kirill A>: Why do we need these 2 following lines?!
    memcpy(kernel_emission->kernel.tx_element.commitment.x, aid, DIGEST_LENGTH);
    kernel_emission->kernel.tx_element.commitment.y = 0;

    secp256k1_gej commitment_native;
    generator_mul_scalar(&commitment_native, get_context()->generator.G_pts,
                         &sk_asset);
    export_gej_to_point(&commitment_native,
                        &kernel_emission->kernel.tx_element.commitment);

    vec_push(trg_kernels, kernel_emission);
    secp256k1_scalar_negate(&sk_asset, &sk_asset);

    // m_pPeers[0].m_k += skAsset;
  }

  // CoSignKernel(*pKrn, hvLockImage);

  // Point::Native exc;
  // TODO<Kirill A>
  secp256k1_gej exc;
  UNUSED(exc);
  // AmountBig::Type is 128 bits = 16 bytes
  // beam::AmountBig::Type fee2;
  // TODO<Kirill A>
  uint8_t fee2[16];
  UNUSED(fee2);
  // verify_test(!pKrn->IsValid(fee2, exc)); // should not pass validation
  // unless correct hash preimage is specified

  //// finish HL: add hash preimage
  // pKrn->m_pHashLock->m_Preimage = hlPreimage;
  memcpy(kernel->kernel.hash_lock_preimage, preimage, DIGEST_LENGTH);
  // verify_test(pKrn->IsValid(fee2, exc));

  vec_push(trg_kernels, kernel);
}

// Add the blinding factor and value of a specific TXO
void summarize_once(secp256k1_scalar* res, int64_t* d_val_out,
                    const key_idv_t* kidv, const HKdf_t* kdf) {
  int64_t d_val = *d_val_out;

  secp256k1_scalar sk;
  secp256k1_gej commitment_native;
  switch_commitment_create(&sk, &commitment_native, kdf, kidv, 1, NULL);
  // Write results - commitment_native - to TxOutput
  // export_gej_to_point(&commitment_native, &output->tx_element.commitment);

  secp256k1_scalar_add(res, res, &sk);
  d_val += kidv->value;

  *d_val_out = d_val;
}

// Summarize. Summarizes blinding factors and values of several in/out TXOs
void summarize_bf_and_values(secp256k1_scalar* res, int64_t* d_val_out,
                             const kidv_vec_t* inputs,
                             const kidv_vec_t* outputs, const HKdf_t* kdf) {
  int64_t d_val = *d_val_out;

  secp256k1_scalar_negate(res, res);
  d_val = -d_val;

  for (uint32_t i = 0; i < (uint32_t)outputs->length; ++i)
    summarize_once(res, &d_val, &outputs->data[i], kdf);

  secp256k1_scalar_negate(res, res);
  d_val = -d_val;

  for (uint32_t i = 0; i < (uint32_t)inputs->length; ++i)
    summarize_once(res, &d_val, &inputs->data[i], kdf);

  *d_val_out = d_val;
}

void summarize_commitment(secp256k1_gej* res, const kidv_vec_t* inputs,
                          const kidv_vec_t* outputs, const HKdf_t* kdf) {
  secp256k1_scalar sk;
  secp256k1_scalar_clear(&sk);
  int64_t d_val = 0;
  summarize_bf_and_values(&sk, &d_val, inputs, outputs, kdf);

  generator_mul_scalar(res, get_context()->generator.G_pts, &sk);

  if (d_val < 0) {
    secp256k1_gej_neg(res, res);

    // res += Context::get().H * Amount(-dVal);
    secp256k1_scalar sk1;
    secp256k1_scalar_set_u64(&sk1, (uint64_t)d_val * -1);
    secp256k1_scalar_negate(&sk1, &sk1);
    secp256k1_gej sk1_h_mul_result;
    generator_mul_scalar(&sk1_h_mul_result, get_context()->generator.H_pts,
                         &sk1);
    secp256k1_gej_add_var(res, res, &sk1_h_mul_result, NULL);

    secp256k1_gej_neg(res, res);
  } else {
    // res += Context::get().H * Amount(dVal);
    secp256k1_scalar sk1;
    secp256k1_scalar_set_u64(&sk1, (uint64_t)d_val);
    secp256k1_gej sk1_h_mul_result;
    generator_mul_scalar(&sk1_h_mul_result, get_context()->generator.H_pts,
                         &sk1);
    secp256k1_gej_add_var(res, res, &sk1_h_mul_result, NULL);
  }
}

uint8_t is_valid_nonce_slot(uint32_t nonce_slot) {
  if (nonce_slot == MASTER_NONCE_SLOT || nonce_slot > MAX_NONCE_SLOT) {
    return 0;
  }

  return 1;
}

uint8_t sign_transaction_part_1(int64_t* value_transferred,
                                secp256k1_scalar* sk_total,
                                const kidv_vec_t* inputs,
                                const kidv_vec_t* outputs,
                                const transaction_data_t* tx_data,
                                const HKdf_t* kdf) {
  if (!is_valid_nonce_slot(tx_data->nonce_slot)) return 0;

  secp256k1_scalar offset;
  secp256k1_scalar_negate(&offset, &tx_data->offset);
  memcpy(sk_total, &offset, sizeof(secp256k1_scalar));
  int64_t d_val = 0;

  // calculate the overall blinding factor, and the sum being sent/transferred
  summarize_bf_and_values(sk_total, &d_val, inputs, outputs, kdf);

  *value_transferred = d_val;

  return 1;
}

uint8_t sign_transaction_part_2(secp256k1_scalar* res,
                                const transaction_data_t* tx_data,
                                const secp256k1_scalar* nonce,
                                const secp256k1_scalar* sk_total) {
  if (!is_valid_nonce_slot(tx_data->nonce_slot)) return 0;

  // Calculate the Kernel ID
  tx_kernel_t krn;
  kernel_init(&krn);
  krn.kernel.min_height = tx_data->min_height;
  krn.kernel.max_height = tx_data->max_height;
  krn.kernel.fee = tx_data->fee;
  memcpy(&krn.kernel.tx_element.commitment, &tx_data->kernel_commitment,
         sizeof(point_t));
  point_import_nnz(&krn.kernel.signature.nonce_pub, &tx_data->kernel_nonce);

  // TODO: get exact size of the hash
  uint8_t kernel_hash_value[DIGEST_LENGTH];
  kernel_get_hash(&krn, NULL, kernel_hash_value);

  uint8_t sk_data[DIGEST_LENGTH];
  secp256k1_scalar_get_b32(sk_data, sk_total);

#ifdef BEAM_TREZOR_DEBUG
  DEBUG_PRINT("Sk total: ", sk_data, DIGEST_LENGTH);
  printf(
      "Kernel:\n\tFee: %ld\n\tMin_height: %ld; Max_height: "
      "%ld\n\tAsset_emission: %ld\n",
      krn.kernel.fee, krn.kernel.min_height, krn.kernel.max_height,
      krn.kernel.asset_emission);
  DEBUG_PRINT("Kernel nonce_pub.x: ", tx_data->kernel_nonce.x, DIGEST_LENGTH);
  printf("\tKernel nonce_pub.y: %d\n", tx_data->kernel_nonce.y);
  DEBUG_PRINT("Kernel commitment.x: ", krn.kernel.tx_element.commitment.x,
              DIGEST_LENGTH);
  printf("\tKernel commitment.y: %d\n", krn.kernel.tx_element.commitment.y);
  DEBUG_PRINT("Kernel hash: ", kernel_hash_value, DIGEST_LENGTH);
#endif

  // Create partial signature

  ecc_signature_t sig;
  point_import_nnz(&sig.nonce_pub, &tx_data->kernel_nonce);

  signature_sign_partial(nonce, &sig.nonce_pub, kernel_hash_value, sk_total,
                         res);

  return 1;
}
