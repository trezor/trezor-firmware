#include "beam.h"
#include "functions.h"
#include "kernel.h"
#include "misc.h"
#include "rangeproof.h"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "beam/lib/secp256k1-zkp/src/field_impl.h"
#include "beam/lib/secp256k1-zkp/src/group_impl.h"
#include "beam/lib/secp256k1-zkp/src/scalar_impl.h"
#pragma GCC diagnostic pop

int test_tx_kernel(void) {
  tx_inputs_vec_t inputs;
  vec_init(&inputs);

  transaction_t transaction;
  transaction_init(&transaction);
  HKdf_t kdf;
  HKdf_init(&kdf);
  // DEBUG_PRINT("KDF: ", kdf.generator_secret, DIGEST_LENGTH);
  secp256k1_scalar peer_sk;
  secp256k1_scalar_clear(&peer_sk);

  // Test Add Input
  peer_add_input(&transaction.inputs, &peer_sk, 100, &kdf, NULL);
  peer_add_input(&transaction.inputs, &peer_sk, 3000, &kdf, NULL);
  peer_add_input(&transaction.inputs, &peer_sk, 2000, &kdf, NULL);

  peer_add_output(&transaction.outputs, &peer_sk, 100, &kdf,
                  NULL);  // REALLY NULL?!

  {
    SHA256_CTX rp_hash;
    uint8_t rp_digest[SHA256_DIGEST_LENGTH];
    sha256_Init(&rp_hash);
    sha256_Update(
        &rp_hash,
        (const uint8_t *)transaction.outputs.data[0]->confidential_proof,
        sizeof(rangeproof_confidential_t));
    sha256_Final(&rp_hash, rp_digest);
  }

  uint64_t fee1 = 100;
  tx_kernel_t kernel;
  kernel_init(&kernel);
  kernel.kernel.fee = fee1;
  secp256k1_gej kG;
  secp256k1_gej xG;
  secp256k1_gej_set_infinity(&kG);
  secp256k1_gej_set_infinity(&xG);
  secp256k1_scalar peer_nonce;
  secp256k1_scalar_clear(&peer_nonce);
  uint8_t kernel_hash_message[DIGEST_LENGTH];

  uint8_t preimage[DIGEST_LENGTH];
  // random_buffer(preimage, 32);
  test_set_buffer(preimage, DIGEST_LENGTH, 3);

  uint8_t hash_lock_preimage[DIGEST_LENGTH];
  SHA256_CTX x;
  sha256_Init(&x);
  sha256_Update(&x, preimage, DIGEST_LENGTH);
  sha256_Final(&x, hash_lock_preimage);

  cosign_kernel_part_1(
      &kernel, &kG, &xG, &peer_sk, &peer_nonce, 1, &transaction.offset,
      kernel_hash_message,
      // TODO: Valdo said we have no hash lock in kernels currently
      hash_lock_preimage);

  cosign_kernel_part_2(&kernel, &xG, &peer_sk, &peer_nonce, 1,
                       kernel_hash_message);

  return 0;
}
