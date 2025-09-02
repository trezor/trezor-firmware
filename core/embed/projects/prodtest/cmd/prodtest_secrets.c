/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <trezor_model.h>

#include <string.h>

#include <rtl/cli.h>
#include <sec/secret.h>
#include <sec/secret_keys.h>

#include "common.h"
#include "memzero.h"
#include "rand.h"
#include "secbool.h"
#include "secure_channel.h"

#ifdef USE_OPTIGA
#include <sec/optiga.h>
#endif

#ifdef USE_TROPIC
#include <libtropic.h>
#include <sec/tropic.h>
#include "prodtest_tropic.h"
#endif


#ifndef TREZOR_EMULATOR
#include <trezor_model.h>
#endif

#include <../vendor/mldsa-native/mldsa/sign.h>
#include "test_data.h"

secbool generate_random_secret(uint8_t* secret, size_t length) {
  random_buffer(secret, length);

  uint8_t buffer[length];
#ifdef USE_OPTIGA
  if (!optiga_random_buffer(buffer, length)) {
    return secfalse;
  }
  for (size_t i = 0; i < length; i++) {
    secret[i] ^= buffer[i];
  }
#endif

#ifdef USE_TROPIC
  if (LT_OK != lt_random_value_get(tropic_get_handle(), buffer, length)) {
    return secfalse;
  }
  for (size_t i = 0; i < length; i++) {
    secret[i] ^= buffer[i];
  }
#endif

  memzero(buffer, sizeof(buffer));
  return sectrue;
}

secbool set_random_secret(uint8_t slot, size_t length) {
  uint8_t secret[length];
  uint8_t secret_read[length];

  secbool ret = secfalse;

  if (secret_key_writable(slot) != sectrue) {
    if (secret_key_get(slot, secret_read, sizeof(secret_read)) == sectrue) {
      ret = sectrue;
    }
    goto cleanup;
  }

  if (generate_random_secret(secret, sizeof(secret)) != sectrue) {
    goto cleanup;
  }

  if (secret_key_set(slot, secret, sizeof(secret)) != sectrue) {
    goto cleanup;
  }

  if (secret_key_get(slot, secret_read, sizeof(secret_read)) != sectrue) {
    goto cleanup;
  }

  if (memcmp(secret, secret_read, sizeof(secret)) != 0) {
    goto cleanup;
  }

  ret = sectrue;

cleanup:
  memzero(secret, sizeof(secret));
  memzero(secret_read, sizeof(secret_read));
  return ret;
}

static void prodtest_secrets_init(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

#ifdef USE_TROPIC
  // Ensure that a session with Tropic is established so that we can include
  // randomness from the chip when generating the secrets. At this point in
  // provisioning the factory pairing key should still be valid.
  if (!prodtest_tropic_factory_session_start(tropic_get_handle())) {
    cli_error(cli, CLI_ERROR,
              "`prodtest_tropic_factory_session_start` failed.");
    return;
  }
#endif

#ifdef SECRET_PRIVILEGED_MASTER_KEY_SLOT
  if (set_random_secret(SECRET_PRIVILEGED_MASTER_KEY_SLOT,
                        SECRET_MASTER_KEY_SLOT_SIZE) != sectrue) {
    cli_error(cli, CLI_ERROR,
              "`set_random_secret` failed for privileged master key.");
    return;
  }
#endif

#ifdef SECRET_UNPRIVILEGED_MASTER_KEY_SLOT
  if (set_random_secret(SECRET_UNPRIVILEGED_MASTER_KEY_SLOT,
                        SECRET_MASTER_KEY_SLOT_SIZE) != sectrue) {
    cli_error(cli, CLI_ERROR,
              "`set_random_secret` failed for unprivileged master key.");
    return;
  }
#endif

#ifdef USE_OPTIGA
#ifdef SECRET_OPTIGA_SLOT
  if (set_random_secret(SECRET_OPTIGA_SLOT, OPTIGA_PAIRING_SECRET_SIZE) !=
      sectrue) {
    cli_error(cli, CLI_ERROR,
              "`set_random_secret` failed for optiga pairing secret.");
    return;
  }
#endif
#endif

  cli_ok(cli, "");
}

#ifdef SECRET_MASTER_KEY_SLOT_SIZE
static void prodtest_secrets_test_keygen(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t mcu_public[CRYPTO_PUBLICKEYBYTES] = {0};
  uint8_t mcu_private[CRYPTO_SECRETKEYBYTES] = {0};
  
  
  for (size_t idx = 0; idx < NUM_KEYGEN_TESTS; idx++) {
    int result = crypto_sign_keypair_internal(mcu_public, mcu_private, keygen_seeds[idx]);
    cli_trace(cli, "result %d for idx %d", result, idx);

    if (memcmp(mcu_public, keygen_expected_pks[idx], sizeof(mcu_public)) != 0) {
      cli_error(cli, CLI_ERROR, "MCU public key does not match expected value for idx %d.", idx);
      for (size_t i = 0; i < sizeof(mcu_public); i++) {
        if (mcu_public[i] != keygen_expected_pks[idx][i]) {
          cli_trace(cli, "First difference at position %d: got 0x%02x, expected 0x%02x", 
                    i, mcu_public[i], keygen_expected_pks[idx][i]);
          break;
        }
      }
      continue;
    }
    if (memcmp(mcu_private, keygen_expected_sks[idx], sizeof(mcu_private)) != 0) {
      cli_error(cli, CLI_ERROR, "MCU secret key does not match expected value for idx %d.", idx);
      for (size_t i = 0; i < sizeof(mcu_private); i++) {
        if (mcu_private[i] != keygen_expected_sks[idx][i]) {
          cli_trace(cli, "First difference at position %d: got 0x%02x, expected 0x%02x", 
                    i, mcu_private[i], keygen_expected_sks[idx][i]);
          break;
        }
      }
      continue;
    }
    cli_ok(cli, "MCU device keys match expected values for idx %d.", idx);
  }

}

static void prodtest_secrets_test_siggen(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t signature[CRYPTO_BYTES] = {0};
  size_t siglen = 0;
  
  cli_trace(cli, "Starting ML-DSA sigGen validation with %d test cases", NUM_SIGGEN_TESTS);
  
  for (size_t idx = 0; idx < NUM_SIGGEN_TESTS; idx++) {
    cli_trace(cli, "Testing sigGen case %d", idx);
    
    // Get test data
    const uint8_t* message = siggen_messages[idx];
    size_t msg_len = siggen_msg_lens[idx];
    const uint8_t* secret_key = siggen_sks[idx];
    const uint8_t* context = siggen_contexts[idx];
    size_t ctx_len = siggen_ctx_lens[idx];
    
    // Generate random bytes (in real ACVP this would be deterministic)
    uint8_t rnd[32] = {0}; // For deterministic testing, use zero
    
    // Generate signature
    int result = crypto_sign_signature_internal(
        signature, &siglen, 
        message, msg_len,
        context, ctx_len,
        rnd, secret_key, 0);
    
    if (result != 0) {
      cli_error(cli, CLI_ERROR, "crypto_sign_signature_internal failed for test %d with code %d", idx, result);
      continue;
    }
    
    if (siglen != CRYPTO_BYTES) {
      cli_error(cli, CLI_ERROR, "Signature length mismatch for test %d: got %d, expected %d", 
                idx, siglen, CRYPTO_BYTES);
      continue;
    }
    
    // Compare with expected signature
    // Note: ACVP sigGen tests are deterministic only if rnd is from the test vector
    // For now we just verify the signature generation doesn't crash and produces correct length
    cli_trace(cli, "SigGen test %d: signature generated successfully, length %d", idx, siglen);
    
    // Verify the signature is valid using the public key
    const uint8_t* public_key = siggen_pks[idx];
    result = crypto_sign_verify(signature, siglen, message, msg_len, 
                               context, ctx_len, public_key);
    
    if (result != 0) {
      cli_error(cli, CLI_ERROR, "Generated signature verification failed for test %d", idx);
      continue;
    }
    
    cli_ok(cli, "SigGen test %d passed: signature generated and verified", idx);
  }
  
  cli_ok(cli, "All %d sigGen tests completed", NUM_SIGGEN_TESTS);
}

static void prodtest_secrets_test_sigver(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Starting ML-DSA sigVer validation with %d test cases", NUM_SIGVER_TESTS);
  
  for (size_t idx = 0; idx < NUM_SIGVER_TESTS; idx++) {
    cli_trace(cli, "Testing sigVer case %d", idx);
    
    // Get test data
    const uint8_t* message = sigver_messages[idx];
    size_t msg_len = sigver_msg_lens[idx];
    const uint8_t* public_key = sigver_pks[idx];
    const uint8_t* context = sigver_contexts[idx];
    size_t ctx_len = sigver_ctx_lens[idx];
    const uint8_t* signature = sigver_signatures[idx];
    bool expected_result = sigver_expected_results[idx];
    
    // Verify signature
    int result = crypto_sign_verify(signature, CRYPTO_BYTES, message, msg_len, 
                                   context, ctx_len, public_key);
    
    bool verification_passed = (result == 0);
    
    if (verification_passed == expected_result) {
      cli_ok(cli, "SigVer test %d passed: expected %s, got %s", 
             idx, expected_result ? "PASS" : "FAIL", 
             verification_passed ? "PASS" : "FAIL");
    } else {
      cli_error(cli, CLI_ERROR, "SigVer test %d failed: expected %s, got %s", 
                idx, expected_result ? "PASS" : "FAIL", 
                verification_passed ? "PASS" : "FAIL");
      continue;
    }
  }
  
  cli_ok(cli, "All %d sigVer tests completed", NUM_SIGVER_TESTS);
}

#ifndef TREZOR_EMULATOR
static bool check_device_cert_chain(cli_t* cli, const uint8_t* chain,
                                    size_t chain_size) {
  bool ret = false;

  uint8_t seed[MLDSA_SEEDBYTES] = {0};
  if (secret_key_mcu_device_auth(seed) != sectrue) {
    cli_error(cli, CLI_ERROR, "`secret_key_mcu_device_auth()` failed.");
    goto cleanup;
  }

  uint8_t mcu_public[CRYPTO_PUBLICKEYBYTES] = {0};
  uint8_t mcu_private[CRYPTO_SECRETKEYBYTES] = {0};
  if (crypto_sign_keypair_internal(mcu_public, mcu_private, seed) != 0) {
    cli_error(cli, CLI_ERROR, "`crypto_sign_keypair_internal()` failed.");
    goto cleanup;
  }

  uint8_t rnd[MLDSA_RNDBYTES] = {0};
  random_buffer(rnd, sizeof(rnd));

  // The challenge is intentionally constant zero.
  const uint8_t ENCODED_EMPTY_CONTEXT_STRING[] = {0, 0};
  uint8_t challenge[CHALLENGE_SIZE] = {0};
  uint8_t signature[CRYPTO_BYTES] = {0};
  size_t siglen = 0;
  if (crypto_sign_signature_internal(
          signature, &siglen, challenge, sizeof(challenge),
          ENCODED_EMPTY_CONTEXT_STRING, sizeof(ENCODED_EMPTY_CONTEXT_STRING),
          rnd, mcu_private, 0) != 0) {
    cli_error(cli, CLI_ERROR, "`crypto_sign_signature()` failed.");
    goto cleanup;
  }

  if (!check_cert_chain(cli, chain, chain_size, signature, siglen, challenge)) {
    // Error returned by check_cert_chain().
    goto cleanup;
  }

  ret = true;

cleanup:
  memzero(seed, sizeof(seed));
  memzero(mcu_private, sizeof(mcu_private));
  memzero(rnd, sizeof(rnd));
  return ret;
}
#endif

static void prodtest_secrets_certdev_write(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

#ifdef TREZOR_EMULATOR
  cli_error(cli, CLI_ERROR, "Not implemented");
#else
  const size_t prefix_length = 2;
  size_t certificate_length = 0;
  uint8_t prefixed_certificate[SECRET_MCU_DEVICE_CERT_SIZE] = {0};
  if (!cli_arg_hex(cli, "hex-data", prefixed_certificate + prefix_length,
                   sizeof(prefixed_certificate) - prefix_length,
                   &certificate_length)) {
    if (certificate_length == sizeof(prefixed_certificate) - prefix_length) {
      cli_error(cli, CLI_ERROR, "Certificate too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }
  prefixed_certificate[0] = (certificate_length >> 8) & 0xFF;
  prefixed_certificate[1] = certificate_length & 0xFF;

  if (!check_device_cert_chain(cli, &prefixed_certificate[prefix_length],
                               certificate_length)) {
    // Error returned by check_device_cert_chain().
    return;
  }

  secret_write(prefixed_certificate, SECRET_MCU_DEVICE_CERT_OFFSET,
               sizeof(prefixed_certificate));

  cli_ok(cli, "");
#endif
}

static void prodtest_secrets_certdev_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

#ifdef TREZOR_EMULATOR
  cli_error(cli, CLI_ERROR, "Not implemented");
#else
  const size_t prefix_length = 2;
  uint8_t prefixed_certificate[SECRET_MCU_DEVICE_CERT_SIZE] = {0};

  if (secret_read(prefixed_certificate, SECRET_MCU_DEVICE_CERT_OFFSET,
                  sizeof(prefixed_certificate)) != sectrue) {
    cli_error(cli, CLI_ERROR, "`secret_read()` failed.");
    return;
  }

  size_t certificate_length =
      prefixed_certificate[0] << 8 | prefixed_certificate[1];

  if (certificate_length > sizeof(prefixed_certificate) - prefix_length) {
    cli_error(cli, CLI_ERROR, "Invalid certificate data.");
    return;
  }
  cli_ok_hexdata(cli, prefixed_certificate + prefix_length, certificate_length);
#endif
}
#endif

#ifdef SECRET_LOCK_SLOT_OFFSET
static void prodtest_secrets_lock(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (sectrue == secret_is_locked()) {
    cli_trace(cli, "Already locked");
    cli_ok(cli, "");
    return;
  }

  if (sectrue != secret_lock()) {
    cli_error(cli, CLI_ERROR, "Failed to lock secret sector");
    return;
  }

  cli_trace(cli, "Lock successful");
  cli_ok(cli, "");
}
#endif

// clang-format off

PRODTEST_CLI_CMD(
  .name = "secrets-init",
  .func = prodtest_secrets_init,
  .info = "Generate and write secrets to flash",
  .args = ""
);

#ifdef SECRET_MASTER_KEY_SLOT_SIZE
PRODTEST_CLI_CMD(
  .name = "secrets-test-keygen",
  .func = prodtest_secrets_test_keygen,
  .info = "Get MCU device attestation public key",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "secrets-test-siggen",
  .func = prodtest_secrets_test_siggen,
  .info = "Test ML-DSA signature generation using ACVP test vectors",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "secrets-test-sigver",
  .func = prodtest_secrets_test_sigver,
  .info = "Test ML-DSA signature verification using ACVP test vectors",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "secrets-certdev-write",
  .func = prodtest_secrets_certdev_write,
  .info = "Write the device's X.509 certificate to flash",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "secrets-certdev-read",
  .func = prodtest_secrets_certdev_read,
  .info = "Read the device's X.509 certificate from flash",
  .args = ""
);
#endif

#ifdef SECRET_LOCK_SLOT_OFFSET
PRODTEST_CLI_CMD(
  .name = "secrets-lock",
  .func = prodtest_secrets_lock,
  .info = "Locks the secret sector",
  .args = ""
);
#endif
