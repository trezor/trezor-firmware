#include "misc.h"
#include "functions.h"
#include "internal.h"
#include "memzero.h"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "beam/lib/secp256k1-zkp/src/field_impl.h"
#include "beam/lib/secp256k1-zkp/src/group_impl.h"
#include "beam/lib/secp256k1-zkp/src/scalar_impl.h"
#pragma GCC diagnostic pop

void test_set_buffer(void* p, uint32_t n, uint8_t value) {
  for (uint32_t i = 0; i < n; i++) ((uint8_t*)p)[i] = value;
}

void transaction_init(transaction_t* t) {
  secp256k1_scalar_clear(&t->offset);
  vec_init(&t->inputs);
  vec_init(&t->outputs);
  vec_init(&t->kernels);
}

void transaction_free(transaction_t* t) {
  vec_deinit_inner_ptrs(&t->inputs, tx_input_t);

  transaction_free_outputs(&t->outputs);

  // Delete inner nested kernels
  for (size_t i = 0; i < (size_t)t->kernels.length; ++i) {
    vec_deinit_inner_ptrs(&t->kernels.data[i]->nested_kernels, _tx_kernel_t);
  }
  // Delete kernels itself
  vec_deinit_inner_ptrs(&t->kernels, tx_kernel_t);
}

void transaction_free_outputs(tx_outputs_vec_t* outputs) {
  // Delete rangeproofs for each output
  for (size_t i = 0; i < (size_t)outputs->length; ++i) {
    tx_output_free(outputs->data[i]);
  }
  // Delete outputs
  vec_deinit_inner_ptrs(outputs, tx_output_t);
}

void signature_init(ecc_signature_t* signature) {
  secp256k1_scalar_clear(&signature->k);
  secp256k1_gej_set_infinity(&signature->nonce_pub);
}

void point_init(point_t* point) {
  memzero(point->x, DIGEST_LENGTH);
  point->y = 0;
}

void key_idv_init(key_idv_t* kidv) {
#ifdef BEAM_DEBUG
  test_set_buffer((uint8_t*)&kidv->id.idx, sizeof(kidv->id.idx), 0);
#else
  random_buffer((uint8_t*)&kidv->id.idx, sizeof(kidv->id.idx));
#endif
  kidv->id.sub_idx = 0;
  kidv->id.type = get_context()->key.Regular;
  kidv->value = 0;
}

void packed_key_id_init(packed_key_id_t* kid) {
  memset(kid->idx, 0, 8);
  memset(kid->type, 0, 4);
  memset(kid->sub_idx, 0, 4);
}

void tx_element_init(tx_element_t* tx_element) {
  point_init(&tx_element->commitment);
  tx_element->maturity_height = 0;
}

void tx_input_init(tx_input_t* input) {
  tx_element_init(&input->tx_element);
  input->_id = 0;
}

void tx_output_init(tx_output_t* output) {
  tx_element_init(&output->tx_element);
  // Regular output by default
  output->is_coinbase = 0;
  // TODO<Kirill> inspect if 0 as default value is good enough
  output->incubation_height = 0;
  memzero(output->asset_id, DIGEST_LENGTH);
  // rangeproof_public will be init later with calling rangeproof_public_create
  // same for the confidential one
  output->confidential_proof = malloc(sizeof(rangeproof_confidential_t));
  output->public_proof = malloc(sizeof(rangeproof_public_t));
  rangeproof_public_init(output->public_proof);
}

void tx_output_free(tx_output_t* output) {
  free(output->confidential_proof);
  free(output->public_proof);
}

void kernel_init(tx_kernel_t* kernel) {
  vec_init(&kernel->nested_kernels);
  signature_init(&kernel->kernel.signature);
  tx_element_init(&kernel->kernel.tx_element);

  kernel->kernel.fee = 0;
  kernel->kernel.min_height = 0;
  kernel->kernel.max_height = UINT64_MAX;
  kernel->kernel.asset_emission = 0;
  memzero(kernel->kernel.hash_lock_preimage, DIGEST_LENGTH);
}

void HKdf_init(HKdf_t* kdf) {
  secp256k1_scalar_set_int(&kdf->cofactor, 1);
  memzero(kdf->generator_secret, DIGEST_LENGTH);
}

int bigint_cmp(const uint8_t* pSrc0, uint32_t nSrc0, const uint8_t* pSrc1,
               uint32_t nSrc1) {
  if (nSrc0 > nSrc1) {
    uint32_t diff = nSrc0 - nSrc1;
    if (!memis0(pSrc0, diff)) return 1;

    pSrc0 += diff;
    nSrc0 = nSrc1;
  } else if (nSrc0 < nSrc1) {
    uint32_t diff = nSrc1 - nSrc0;
    if (!memis0(pSrc1, diff)) return -1;

    pSrc1 += diff;
  }

  return memcmp(pSrc0, pSrc1, nSrc0);
}

int point_cmp(const point_t* lhs, const point_t* rhs) {
  if (lhs->y < rhs->y) return -1;
  if (lhs->y > rhs->y) return 1;

  return bigint_cmp(lhs->x, DIGEST_LENGTH, rhs->x, DIGEST_LENGTH);
}

int tx_element_cmp(const tx_element_t* lhs, const tx_element_t* rhs) {
  CMP_MEMBER(lhs->maturity_height, rhs->maturity_height)
  return point_cmp(&lhs->commitment, &rhs->commitment);
}

int signature_cmp(const ecc_signature_t* lhs, const ecc_signature_t* rhs) {
  point_t lhs_nonce_pub_point;
  export_gej_to_point((secp256k1_gej*)&lhs->nonce_pub, &lhs_nonce_pub_point);
  point_t rhs_nonce_pub_point;
  export_gej_to_point((secp256k1_gej*)&rhs->nonce_pub, &rhs_nonce_pub_point);

  CMP_SIMPLE(lhs_nonce_pub_point.y, rhs_nonce_pub_point.y)

  return memcmp(lhs_nonce_pub_point.x, rhs_nonce_pub_point.x, DIGEST_LENGTH);
}

int kernel_cmp(const tx_kernel_t* lhs, const tx_kernel_t* rhs) {
  // Compare tx_element
  CMP_BY_FUN(&lhs->kernel.tx_element, &rhs->kernel.tx_element, tx_element_cmp)
  // Compare signature
  CMP_BY_FUN(&lhs->kernel.signature, &rhs->kernel.signature, signature_cmp)

  CMP_MEMBER(lhs->kernel.fee, rhs->kernel.fee)
  CMP_MEMBER(lhs->kernel.min_height, rhs->kernel.min_height)
  CMP_MEMBER(lhs->kernel.max_height, rhs->kernel.max_height)
  CMP_MEMBER(lhs->kernel.asset_emission, rhs->kernel.asset_emission)

  // TODO: implement comparison of nested kernels
  // auto it0 = m_vNested.begin();
  // auto it1 = v.m_vNested.begin();

  // for ( ; m_vNested.end() != it0; it0++, it1++)
  //{
  //    if (v.m_vNested.end() == it1)
  //        return 1;

  //    int n = (*it0)->cmp(*(*it1));
  //    if (n)
  //        return n;
  //}

  // if (v.m_vNested.end() != it1)
  //    return -1;

  return bigint_cmp(lhs->kernel.hash_lock_preimage, DIGEST_LENGTH,
                    rhs->kernel.hash_lock_preimage, DIGEST_LENGTH);
}

void get_seed_kid_from_commitment(const point_t* commitment, uint8_t* seed,
                                  const HKdf_t* kdf) {
  SHA256_CTX hp;
  sha256_Init(&hp);
  sha256_Update(&hp, commitment->x, DIGEST_LENGTH);
  sha256_write_8(&hp, commitment->y);
  sha256_Final(&hp, seed);

  secp256k1_scalar sk;
  derive_pkey(kdf->generator_secret, DIGEST_LENGTH, seed, DIGEST_LENGTH, &sk);

  uint8_t sk_data[DIGEST_LENGTH];
  secp256k1_scalar_get_b32(sk_data, &sk);

  SHA256_CTX hp2;
  sha256_Init(&hp2);
  sha256_Update(&hp2, sk_data, DIGEST_LENGTH);
  sha256_Final(&hp2, seed);
}
