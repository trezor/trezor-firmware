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
#include <sec/rng_strong.h>
#include <sec/secret.h>
#include <sec/secret_keys.h>

#include "common.h"
#include "memzero.h"
#include "secbool.h"
#include "secure_channel.h"

#ifdef USE_OPTIGA
#include <sec/optiga.h>
#include "prodtest_optiga.h"
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

  if (!rng_fill_buffer_strong(secret, sizeof(secret))) {
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

#ifdef SECRET_LOCK_SLOT_OFFSET
  // Make sure that the secrets sector isn't locked so that we don't overwrite
  // the MCU's nRF pairing secret.
  if (secfalse != secret_is_locked()) {
    cli_error(cli, CLI_ERROR, "Secret sector is already locked");
    return;
  }
#endif

#ifdef USE_OPTIGA
  // Make sure that Optiga isn't locked so that we don't overwrite the MCU's
  // pairing secrets.
  optiga_locked_status optiga_status = get_optiga_locked_status(cli);

  if (optiga_status == OPTIGA_LOCKED_TRUE) {
    cli_error(cli, CLI_ERROR, "Optiga is already locked");
    return;
  }

  if (optiga_status != OPTIGA_LOCKED_FALSE) {
    // Error reported by get_optiga_locked_status().
    return;
  }
#endif

#ifdef USE_TROPIC
  // Make sure that Tropic pairing hasn't started so that we don't overwrite the
  // MCU's pairing secrets.
  curve25519_key tropic_public = {0};
  if (secret_key_tropic_public(tropic_public) == sectrue) {
    cli_error(cli, CLI_ERROR, "Tropic pairing has already started.");
    return;
  }

  // Ensure that a session with Tropic is established so that we can include
  // randomness from the chip when generating the secrets. At this point in
  // provisioning the factory pairing key should still be valid.
  if (tropic_custom_session_start(TROPIC_FACTORY_PAIRING_KEY_SLOT) != LT_OK) {
    cli_error(cli, CLI_ERROR, "`tropic_custom_session_start()` failed.");
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
static void prodtest_secrets_get_mcu_device_key(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

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

  uint8_t output[sizeof(mcu_public) + NOISE_TAG_SIZE] = {0};
  if (!secure_channel_encrypt(mcu_public, sizeof(mcu_public), NULL, 0,
                              output)) {
    // `secure_channel_handshake_2()` might not have been called
    cli_error(cli, CLI_ERROR, "`secure_channel_encrypt()` failed.");
    goto cleanup;
  }

  cli_ok_hexdata(cli, output, sizeof(output));

cleanup:
  memzero(seed, sizeof(seed));
  memzero(mcu_private, sizeof(mcu_private));
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
  rng_fill_buffer(rnd, sizeof(rnd));

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

  secbool result =
      secret_write(prefixed_certificate, SECRET_MCU_DEVICE_CERT_OFFSET,
                   sizeof(prefixed_certificate));

  if (sectrue != result) {
    cli_error(cli, CLI_ERROR, "secret_write() failed.");
    return;
  }

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
  .name = "secrets-get-mcu-device-key",
  .func = prodtest_secrets_get_mcu_device_key,
  .info = "Get MCU device attestation public key",
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
