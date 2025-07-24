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
#ifdef USE_OPTIGA
#include <sec/optiga_commands.h>
#endif
#include <sec/secret.h>
#include <sec/secret_keys.h>

#include "memzero.h"
#include "rand.h"
#include "secbool.h"
#include "secure_channel.h"

secbool generate_random_secret(uint8_t* secret, size_t length) {
  random_buffer(secret, length);

#ifdef USE_OPTIGA
  uint8_t optiga_secret[length];
  if (OPTIGA_SUCCESS != optiga_get_random(optiga_secret, length)) {
    return secfalse;
  }
  for (size_t i = 0; i < length; i++) {
    secret[i] ^= optiga_secret[i];
  }
  memzero(optiga_secret, sizeof(optiga_secret));
#endif

#ifdef USE_TROPIC
  // TODO: Generate randomness using tropic and xor it with `secret`.
#endif

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

  curve25519_key mcu_private = {0};
  if (secret_key_mcu_device_auth(mcu_private) != sectrue) {
    cli_error(cli, CLI_ERROR, "`secret_key_mcu_device_auth()` failed.");
    return;
  }
  curve25519_key mcu_public = {0};
  curve25519_scalarmult_basepoint(mcu_public, mcu_private);

  uint8_t output[sizeof(curve25519_key) + NOISE_TAG_SIZE] = {0};
  if (!secure_channel_encrypt(NULL, 0, mcu_public, sizeof(curve25519_key),
                              output + NOISE_TAG_SIZE)) {
    // `secure_channel_handshake_2()` might not have been called
    cli_error(cli, CLI_ERROR, "`secure_channel_encrypt()` failed.");
    goto cleanup;
  }

  cli_ok_hexdata(cli, output, sizeof(output));

cleanup:
  memzero(mcu_private, sizeof(mcu_private));
}

static void prodtest_secrets_certdev_write(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  size_t certificate_length = 0;
  uint8_t certificate[512] = {0};
  if (!cli_arg_hex(cli, "hex-data", certificate, sizeof(certificate),
                   &certificate_length)) {
    if (certificate_length == sizeof(certificate)) {
      cli_error(cli, CLI_ERROR, "Certificate too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }

  // TODO: Write the certificate to the flash.

  cli_ok(cli, "");
}

static void prodtest_secrets_certdev_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t certificate[512] = {0};
  size_t certificate_length = 0;

  // TODO: Read the certificate from the flash.

  cli_ok_hexdata(cli, certificate, certificate_length);
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
  .name = "secrets-get-mcu-device_key",
  .func = prodtest_secrets_get_mcu_device_key,
  .info = "Get MCU device key",
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
