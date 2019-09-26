#ifndef __BEAM_KERNEL__
#define __BEAM_KERNEL__

#include "definitions.h"
#include "rangeproof.h"

typedef struct {
  point_t commitment;
  uint64_t maturity_height;  // used in macroblocks only
} tx_element_t;

typedef struct {
  ecc_signature_t signature;  // For the whole body, including nested kernels
  uint64_t fee;  // can be 0 (for instance for coinbase transactions)
  uint64_t min_height;
  uint64_t max_height;
  int64_t asset_emission;  // in case it's non-zero - the kernel commitment is
                           // the AssetID

  uint8_t hash_lock_preimage[DIGEST_LENGTH];
  tx_element_t tx_element;
} _tx_kernel_t;
// Just an inner type to store nested TxKernels
typedef vec_t(_tx_kernel_t*) _nested_kernels_vec_t;

typedef struct {
  _tx_kernel_t kernel;

  _nested_kernels_vec_t nested_kernels;
} tx_kernel_t;
// Define a type for vector of TxKernels
typedef vec_t(tx_kernel_t*) tx_kernels_vec_t;

typedef struct {
  tx_element_t tx_element;
  uint64_t _id;  // used internally. Not serialized/transferred
} tx_input_t;
// Define a type for vector of TxInputs
typedef vec_t(tx_input_t*) tx_inputs_vec_t;

typedef struct {
  tx_element_t tx_element;
  uint32_t is_coinbase;             // 0 - regular output. 1 - coinbase
  uint64_t incubation_height;       // # of blocks before it's mature
  uint8_t asset_id[DIGEST_LENGTH];  // type of ECC:Hash::Value

  // one of the following *must* be specified

  rangeproof_confidential_t* confidential_proof;
  rangeproof_public_t* public_proof;
} tx_output_t;
// Define a type for vector of TxOutputs
typedef vec_t(tx_output_t*) tx_outputs_vec_t;

typedef struct {
  secp256k1_scalar offset;
  tx_inputs_vec_t inputs;
  tx_outputs_vec_t outputs;
  tx_kernels_vec_t kernels;
} transaction_t;

typedef struct {
  // Common kernel parameters
  uint64_t fee;
  uint64_t min_height;
  uint64_t max_height;

  // Aggregated data
  point_t kernel_commitment;
  point_t kernel_nonce;

  // Nonce slot used
  uint32_t nonce_slot;

  // Additional explicit blinding factor that should be added
  secp256k1_scalar offset;
} transaction_data_t;

uint8_t is_valid_nonce_slot(uint32_t nonce_slot);
void ecc_tag_add_value(const secp256k1_gej* h_gen, uint64_t value,
                       secp256k1_gej* out);
void create_kidv_image(const HKdf_t* kdf, const key_idv_t* key_idv,
                       secp256k1_gej* out_commitment, uint8_t create_coin_key);
void switch_commitment(const uint8_t* asset_id, secp256k1_gej* h_gen);
void switch_commitment_get_hash(const key_idv_t* kidv, uint8_t* hash_id);
void switch_commitment_create(secp256k1_scalar* sk, secp256k1_gej* commitment,
                              const HKdf_t* kdf, const key_idv_t* kidv,
                              uint8_t has_commitment,
                              const secp256k1_gej* h_gen);
void switch_commitment_get_sk1(const secp256k1_gej* commitment,
                               const secp256k1_gej* sk0_j,
                               secp256k1_scalar* scalar_out);
void peer_finalize_excess(secp256k1_scalar* peer_scalar, secp256k1_gej* kG,
                          secp256k1_scalar* k_offset);
void peer_add_input(tx_inputs_vec_t* tx_inputs, secp256k1_scalar* peer_scalar,
                    uint64_t val, HKdf_t* kdf, const uint8_t* asset_id);
void peer_add_output(tx_outputs_vec_t* tx_outputs,
                     secp256k1_scalar* peer_scalar, uint64_t val, HKdf_t* kdf,
                     const uint8_t* asset_id);
void tx_output_get_seed_kid(const tx_output_t* output, uint8_t* seed,
                            HKdf_t* kdf);
void tx_output_create(tx_output_t* output, secp256k1_scalar* sk,
                      HKdf_t* coin_kdf, const key_idv_t* kidv, HKdf_t* tag_kdf,
                      uint8_t is_public);
void create_tx_kernel(tx_kernels_vec_t* trg_kernels,
                      tx_kernels_vec_t* nested_kernels, uint64_t fee,
                      uint8_t should_emit_custom_tag);
int kernel_traverse(const tx_kernel_t* kernel, const tx_kernel_t* parent_kernel,
                    const uint8_t* hash_lock_preimage, uint8_t* hash_value,
                    uint64_t* fee, secp256k1_gej* excess);
void kernel_get_hash(const tx_kernel_t* kernel,
                     const uint8_t* hash_lock_preimage, uint8_t* out);
void cosign_kernel_part_1(tx_kernel_t* kernel, secp256k1_gej* kG,
                          secp256k1_gej* xG, secp256k1_scalar* peer_scalars,
                          secp256k1_scalar* peer_nonces, size_t num_peers,
                          secp256k1_scalar* transaction_offset,
                          uint8_t* kernel_hash_message,
                          const uint8_t* hash_lock_preimage);
void cosign_kernel_part_2(tx_kernel_t* kernel, secp256k1_gej* xG,
                          secp256k1_scalar* peer_scalars,
                          secp256k1_scalar* peer_nonces, size_t num_peers,
                          uint8_t* kernel_hash_message);
uint8_t sign_transaction_part_1(int64_t* value_transferred,
                                secp256k1_scalar* sk_total,
                                const kidv_vec_t* inputs,
                                const kidv_vec_t* outputs,
                                const transaction_data_t* tx_data,
                                const HKdf_t* kdf);
uint8_t sign_transaction_part_2(secp256k1_scalar* res,
                                const transaction_data_t* tx_data,
                                const secp256k1_scalar* nonce,
                                const secp256k1_scalar* sk_total);

#endif  // __BEAM_KERNEL__
