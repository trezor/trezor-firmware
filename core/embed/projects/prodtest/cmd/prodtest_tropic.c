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

#ifdef USE_TROPIC
#include "prodtest_tropic.h"

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sec/tropic.h>
#include <sys/rng.h>
#include <sys/systick.h>

#include <sec/secret.h>
#include <sec/secret_keys.h>

#include "bignum.h"
#include "ecdsa.h"
#include "memzero.h"
#include "nist256p1.h"

#include "common.h"
#include "fw_CPU.h"
#include "fw_SPECT.h"
#include "libtropic.h"
#include "libtropic_l2.h"

#include <sec/tropic.h>
#include <sec/tropic_configs.h>

#include "secure_channel.h"

typedef enum {
  TROPIC_HANDSHAKE_STATE_0,  // Handshake has not been initiated yet
  TROPIC_HANDSHAKE_STATE_1,  // Handshake completed (after calling
                             // `tropic-handshake`), `tropic-send-command` can
                             // be called
} tropic_handshake_state_t;

static tropic_handshake_state_t g_tropic_handshake_state =
    TROPIC_HANDSHAKE_STATE_0;

// TODO: Update this link to correspond with the latest chip revision when it
// becomes available.
// https://github.com/tropicsquare/tropic01/blob/da459d18db7aea107419035b9cdf316d89a73445/doc/api/tropic01_user_api_v1.1.2.pdf

// Total number of MAC-and-destroy slots.
#define TROPIC_MAC_AND_DESTROY_SLOT_TOTAL \
  (2 * TROPIC_MAC_AND_DESTROY_SLOT_COUNT)

// Number of monotonic counters.
#define TROPIC_MCOUNTER_COUNT (TR01_MCOUNTER_INDEX_15 + 1)
// For unprivileged sessions, counter initialization is restricted to counters
// 4-15. Mirrors `CFG_UAP_MCOUNTER_INIT`.
#define TROPIC_FIRST_UNPRIVILEGED_MCOUNTER 4

// R-memory range used by the writable-slot test. Starts right after the
// certificate slots (0-5) and Tropic config distribution version slots (6, 7),
// which must not be overwritten.
#define TROPIC_RMEM_TEST_FIRST 8
#define TROPIC_RMEM_TEST_LAST TR01_R_MEM_DATA_SLOT_MAX
#define TROPIC_RMEM_TEST_COUNT \
  (TROPIC_RMEM_TEST_LAST - TROPIC_RMEM_TEST_FIRST + 1)
// For unprivileged sessions, R-memory writes are restricted to slots 256-511.
// Mirrors `CFG_UAP_R_MEM_DATA_WRITE`,
#define TROPIC_RMEM_UNPRIVILEGED_FIRST 256
// Amount of data written and read back per R-memory slot in the test.
#define TROPIC_RMEM_TEST_DATA_SIZE 64

// First ECC key slot that is not provisioned (device key is slot 0, FIDO key is
// slot 1).
#define TROPIC_ECC_TEST_FIRST TR01_ECC_SLOT_2

static void prodtest_tropic_get_riscv_fw_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_handle_t* tropic_handle = tropic_get_handle();

  uint8_t version[TR01_L2_GET_INFO_RISCV_FW_SIZE] = {0};
  lt_ret_t ret = lt_get_info_riscv_fw_ver(tropic_handle, version);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_RISCV_FW_VERSION,
              "lt_get_info_riscv_fw_ver() failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  // Respond with an OK message and version
  cli_ok_hexdata(cli, &version, sizeof(version));
}

static void prodtest_tropic_get_spect_fw_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_handle_t* tropic_handle = tropic_get_handle();

  uint8_t version[TR01_L2_GET_INFO_SPECT_FW_SIZE];
  lt_ret_t ret = lt_get_info_spect_fw_ver(tropic_handle, version);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_SPECT_FW_VERSION,
              "lt_get_info_spect_fw_ver() failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  // Respond with an OK message and version
  cli_ok_hexdata(cli, &version, sizeof(version));
}

static void prodtest_tropic_get_chip_id(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_handle_t* tropic_handle = tropic_get_handle();

  lt_chip_id_t chip_id;
  lt_ret_t ret = lt_get_info_chip_id(tropic_handle, &chip_id);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CHIP_ID,
              "lt_get_info_chip_id() failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  cli_trace(cli, "Silicon revision: %c%c%c%c", chip_id.silicon_rev[0],
            chip_id.silicon_rev[1], chip_id.silicon_rev[2],
            chip_id.silicon_rev[3]);

  // Respond with an OK message and chip ID
  cli_ok_hexdata(cli, &chip_id, sizeof(chip_id));
}

static void prodtest_tropic_certtropic_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  const uint8_t* tropic_cert_chain = NULL;
  size_t tropic_cert_chain_length = 0;
  if (!tropic_get_cert_chain_ptr(cli, &tropic_cert_chain,
                                 &tropic_cert_chain_length)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CERT_READ,
              "`tropic_get_cert_chain_ptr()` failed");
    return;
  }

  cli_ok_hexdata(cli, tropic_cert_chain, tropic_cert_chain_length);
}

static void prodtest_tropic_lock_check(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_locked_status status = get_tropic_locked_status(cli);
  switch (status) {
    case TROPIC_LOCKED_TRUE:
      cli_trace(cli, "Tropic is locked.");
      cli_ok(cli, "YES");
      break;
    case TROPIC_LOCKED_FALSE:
      cli_trace(cli, "Tropic is not locked.");
      cli_ok(cli, "NO");
      break;
    default:
      // Error reported by get_tropic_locked_status.
      break;
  }
}

tropic_locked_status get_tropic_locked_status(cli_t* cli) {
  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  lt_handle_t* tropic_handle = tropic_get_handle();
  lt_ret_t ret = LT_FAIL;

  curve25519_key tropic_public = {0};
  if (secret_key_tropic_public(tropic_public) != sectrue) {
    cli_trace(cli, "The Tropic pairing process was not initiated.");
    return TROPIC_LOCKED_FALSE;
  }

  ret = tropic_custom_session_start(cli, TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    if (ret == LT_L2_HSK_ERR) {
      cli_trace(cli,
                "The Tropic pairing process was initiated but probably failed "
                "midway.");
      return TROPIC_LOCKED_FALSE;
    } else {
      cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_CHECK_SESSION,
                "`tropic_custom_session_start()` failed with error '%s'",
                lt_ret_verbose(ret));
      return TROPIC_LOCKED_ERROR;
    }
  }

  tropic_expected_config_t config = {0};
  if (!tropic_get_expected_tropic_config_from_distribution_version(
          tropic_prodtest_config_distribution_version, &config)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_CHECK_EXPECTED_CONFIG,
              "Prodtest expected configuration not found.");
    return TROPIC_LOCKED_ERROR;
  }

  lt_config_t configuration_read = {0};
  ret = lt_read_whole_R_config_retry(tropic_handle, &configuration_read);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_CHECK_R_CONFIG_READ,
              "`lt_read_whole_R_config_retry()` failed with error '%s'",
              lt_ret_verbose(ret));
    return TROPIC_LOCKED_ERROR;
  }

  if (memcmp(config.max_r_config, (uint8_t*)&configuration_read,
             sizeof(*config.max_r_config)) != 0) {
    cli_trace(cli,
              "The reversible configuration read does not match the expected "
              "reversible configuration.");
    return TROPIC_LOCKED_FALSE;
  }

  ret = lt_read_whole_I_config_retry(tropic_handle, &configuration_read);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_CHECK_I_CONFIG_READ,
              "`lt_read_whole_I_config_retry()` failed with error '%s'",
              lt_ret_verbose(ret));
    return TROPIC_LOCKED_ERROR;
  }

  if (memcmp(config.i_config, (uint8_t*)&configuration_read,
             sizeof(*config.i_config)) != 0) {
    cli_trace(cli,
              "The irreversible configuration read does not match the expected "
              "irreversible configuration.");
    return TROPIC_LOCKED_FALSE;
  }

  uint8_t distribution_version_bytes[sizeof(
      tropic_prodtest_config_distribution_version)] = {0};
  uint16_t distribution_version_read_length = 0;
  ret = lt_r_mem_data_read(
      tropic_handle, TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT,
      distribution_version_bytes, sizeof(distribution_version_bytes),
      &distribution_version_read_length);
  if (ret == LT_L3_R_MEM_DATA_READ_SLOT_EMPTY) {
    cli_trace(cli, "The distribution version slot is empty.");
    return TROPIC_LOCKED_FALSE;
  } else if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_CHECK_DISTR_VERSION_READ,
              "`lt_r_mem_data_read()` failed with error '%s'",
              lt_ret_verbose(ret));
    return TROPIC_LOCKED_ERROR;
  }

  if (distribution_version_read_length != sizeof(distribution_version_bytes) ||
      read_be(distribution_version_bytes) !=
          tropic_prodtest_config_distribution_version) {
    cli_trace(cli,
              "The distribution version read does not match the expected "
              "distribution version.");
    return TROPIC_LOCKED_FALSE;
  }

  ret = lt_r_mem_data_read(
      tropic_handle, TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT,
      distribution_version_bytes, sizeof(distribution_version_bytes),
      &distribution_version_read_length);

  switch (ret) {
    case LT_L3_R_MEM_DATA_READ_SLOT_EMPTY:
      break;  // the backup slot is expected to be empty
    case LT_OK:
      cli_trace(cli, "The backup distribution version slot is not empty.");
      return TROPIC_LOCKED_FALSE;
    default:
      cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_CHECK_BACKUP_DISTR_VERSION_READ,
                "`lt_r_mem_data_read()` failed with error '%s'",
                lt_ret_verbose(ret));
      return TROPIC_LOCKED_ERROR;
  }

  return TROPIC_LOCKED_TRUE;
}

static lt_ret_t pairing_key_write(cli_t* cli, lt_handle_t* handle,
                                  lt_pkey_index_t slot,
                                  const ed25519_secret_key public_key) {
  // If this function returns `LT_OK`, it is ensured that the pairing key
  // `public_key` is written in the slot `slot`.
  lt_ret_t ret = lt_pairing_key_write(handle, public_key, slot);
  if (ret == LT_L3_FAIL) {
    cli_trace(cli, "Pairing key has already been written.");
  } else if (ret != LT_OK) {
    cli_trace(cli, "`lt_pairing_key_write()` failed with error '%s'",
              lt_ret_verbose(ret));
    return ret;
  }

  curve25519_key public_key_read = {0};
  ret = lt_pairing_key_read(handle, public_key_read, slot);
  if (ret != LT_OK) {
    cli_trace(cli, "`lt_pairing_key_read()` failed with error '%s'",
              lt_ret_verbose(ret));
    return ret;
  }
  if (memcmp(public_key, public_key_read, sizeof(ed25519_public_key)) != 0) {
    cli_trace(cli, "Public key does not match the expected value.");
    return LT_FAIL;
  }

  return LT_OK;
}

static bool tropic_is_paired(cli_t* cli) {
  static bool is_paired = false;
  if (is_paired) {
    return true;
  }

  lt_handle_t* tropic_handle = tropic_get_handle();
  lt_ret_t ret = LT_FAIL;

  // Try to establish a session using the unprivileged key pair.
  ret = tropic_custom_session_start(cli, TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_trace(
        cli,
        "`tropic_custom_session_start()` for unprivileged key failed with "
        "error '%s'",
        lt_ret_verbose(ret));
    goto cleanup;
  }

  // Try to establish a session using the privileged key pair.
  ret = tropic_custom_session_start(cli, TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_trace(cli,
              "`tropic_custom_session_start()` for privileged key failed "
              "with error '%s'",
              lt_ret_verbose(ret));
    goto cleanup;
  }

  // Read the factory pairing key to ensure it is invalidated.
  curve25519_key public_read = {0};
  ret = lt_pairing_key_read(tropic_handle, public_read,
                            TROPIC_FACTORY_PAIRING_KEY_SLOT);
  if (ret != LT_L3_SLOT_INVALID) {
    cli_trace(cli,
              "`lt_pairing_key_read()` for factory pairing key failed with "
              "error '%s'",
              lt_ret_verbose(ret));
    goto cleanup;
  }

  // Read the fourth pairing key to ensure it is empty.
  ret = lt_pairing_key_read(tropic_handle, public_read,
                            TR01_PAIRING_KEY_SLOT_INDEX_3);
  if (ret != LT_L3_SLOT_EMPTY) {
    cli_trace(cli,
              "`lt_pairing_key_read()` for pairing key slot 3 failed with "
              "error '%s'",
              lt_ret_verbose(ret));
    goto cleanup;
  }

  is_paired = true;

cleanup:
  return is_paired;
}

static void prodtest_tropic_pair(cli_t* cli) {
  // If this function successfully completes, it is ensured that:
  //  * The public tropic key is written to MCU's flash.
  //  * The factory pairing key in tropic's `TR01_PAIRING_KEY_SLOT_INDEX_0` is
  //  invalidated.
  //  * The unprivileged pairing key is written to tropic's
  //  `TR01_PAIRING_KEY_SLOT_INDEX_1`.
  //  * The privileged pairing key is written to tropic's
  //  `TR01_PAIRING_KEY_SLOT_INDEX_2`.
  //  * The pairing key in tropic's `TR01_PAIRING_KEY_SLOT_INDEX_3` is empty.
  // This function is:
  //   * idempotent (it can be called multiple times without changing the state
  //   of the device),
  //   * irreversible (it cannot be undone),
  //   * self-recovering (if the device is powered off during execution, it can
  //   be called again to continue from where it left off).

  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    goto cleanup;
  }

  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  lt_handle_t* tropic_handle = tropic_get_handle();

  // Retrieve the unprivileged pairing key pair.
  // NOTE: This ensures that secrets-init has already been called before any
  // other steps take place. Otherwise, if we wrote Tropic's public key to the
  // MCU's flash before completing secrets-init, we would run into a deadlock.
  curve25519_key unprivileged_private = {0};
  if (secret_key_tropic_pairing_unprivileged(unprivileged_private) != sectrue) {
    cli_error(cli, PRODTEST_ERR_TROPIC_PAIR_PUBKEY_UNPRIV,
              "`secret_key_tropic_pairing_unprivileged()` failed.");
    goto cleanup;
  }
  curve25519_key unprivileged_public = {0};
  curve25519_scalarmult_basepoint(unprivileged_public, unprivileged_private);

  // Retrieve the privileged pairing key pair.
  curve25519_key privileged_private = {0};
  if (secret_key_tropic_pairing_privileged(privileged_private) != sectrue) {
    cli_error(cli, PRODTEST_ERR_TROPIC_PAIR_PUBKEY_PRIV,
              "`secret_key_tropic_pairing_privileged()` failed.");
    goto cleanup;
  }
  curve25519_key privileged_public = {0};
  curve25519_scalarmult_basepoint(privileged_public, privileged_private);

  // Get the Tropic01 public pairing key from the chip's certificate.
  curve25519_key tropic_public = {0};
  if (!tropic_get_pubkey(cli, tropic_public)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_PAIR_GET_PUBKEY,
              "`tropic_get_tropic_pubkey()` failed");
    goto cleanup;
  }

  // Retrieve the tropic public key and write it to MCU's flash if it has not
  // been written yet.
  curve25519_key tropic_public_flash = {0};
  if (secret_key_tropic_public(tropic_public_flash) != sectrue) {
#ifdef SECRET_TROPIC_TROPIC_PUBKEY_SLOT
    // This is skipped in the prodtest emulator.
    if (secret_key_set(SECRET_TROPIC_TROPIC_PUBKEY_SLOT, tropic_public,
                       sizeof(curve25519_key)) != sectrue) {
      cli_error(cli, PRODTEST_ERR_TROPIC_PAIR_STORE_SET,
                "`secret_key_set()` failed for tropic public key.");
      goto cleanup;
    }
#endif
    if (secret_key_tropic_public(tropic_public_flash) != sectrue) {
      cli_error(cli, PRODTEST_ERR_TROPIC_PAIR_STORE_SK,
                "`secret_key_tropic_public()` failed.");
      goto cleanup;
    }
  }
  if (memcmp(tropic_public, tropic_public_flash, sizeof(curve25519_key)) != 0) {
    cli_error(cli, PRODTEST_ERR_TROPIC_PAIR_STORE_MISMATCH,
              "Tropic public key does not match the expected value.");
    goto cleanup;
  }

  if (tropic_custom_session_start(cli, TROPIC_FACTORY_PAIRING_KEY_SLOT) ==
      LT_OK) {
    // Write the privileged pairing key to the tropic's pairing key slot if it
    // has not been written yet.
    lt_ret_t ret = pairing_key_write(cli, tropic_handle,
                                     TROPIC_PRIVILEGED_PAIRING_KEY_SLOT,
                                     privileged_public);
    // If the pairing key has already been written, `pairing_key_write()`
    // returns `LT_OK`.
    if (ret != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_PAIR_KEY_WRITE_PRIV,
                "`pairing_key_write()` failed for privileged pairing key with "
                "error '%s'",
                lt_ret_verbose(ret));
      goto cleanup;
    }

    // Write the unprivileged pairing key to the tropic's pairing key slot if it
    // has not been written yet.
    ret = pairing_key_write(cli, tropic_handle,
                            TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT,
                            unprivileged_public);
    // If the pairing key has already been written, `pairing_key_write()`
    // returns `LT_OK`.
    if (ret != LT_OK) {
      cli_error(
          cli, PRODTEST_ERR_TROPIC_PAIR_KEY_WRITE_UNPRIV,
          "`pairing_key_write()` failed for unprivileged pairing key with "
          "error '%s'",
          lt_ret_verbose(ret));
      goto cleanup;
    }

    // Invalidate the factory pairing key if it has not been invalidated yet.
    ret = lt_pairing_key_invalidate(tropic_handle,
                                    TROPIC_FACTORY_PAIRING_KEY_SLOT);
    // If the factory has already been invalidated,
    // `lt_pairing_key_invalidate()` returns `LT_OK`.
    if (ret != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_PAIR_CERT_SIGN,
                "`lt_pairing_key_invalidate()` failed for factory pairing key "
                "with error '%s'",
                lt_ret_verbose(ret));
      goto cleanup;
    }
  }

  if (!tropic_is_paired(cli)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_PAIR_IS_PAIRED_FAILED,
              "`tropic_is_paired()` failed.");
    goto cleanup;
  }

  cli_ok(cli, "");

cleanup:
  memzero(privileged_private, sizeof(privileged_private));
  memzero(unprivileged_private, sizeof(unprivileged_private));
  return;
}

static void prodtest_tropic_get_access_credential(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  curve25519_key unprivileged_private = {0};
  if (secret_key_tropic_pairing_unprivileged(unprivileged_private) != sectrue) {
    cli_error(cli, PRODTEST_ERR_TROPIC_ACCESS_CRED_PUBKEY,
              "`secret_key_tropic_pairing_unprivileged()` failed.");
    goto cleanup;
  }

  curve25519_key tropic_public = {0};
  if (!tropic_get_pubkey(cli, tropic_public)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_ACCESS_CRED_GET_PUBKEY,
              "`tropic_get_tropic_pubkey()` failed");
    goto cleanup;
  }

  uint8_t output[sizeof(unprivileged_private) + NOISE_TAG_SIZE] = {0};
  if (!secure_channel_encrypt((uint8_t*)unprivileged_private,
                              sizeof(unprivileged_private), tropic_public,
                              sizeof(curve25519_key), output)) {
    // `secure_channel_handshake_2()` might not have been called
    cli_error(cli, PRODTEST_ERR_TROPIC_ACCESS_CRED_ENCRYPT,
              "`secure_channel_encrypt()` failed.");
    goto cleanup;
  }

  cli_ok_hexdata(cli, output, sizeof(output));

cleanup:
  memzero(unprivileged_private, sizeof(unprivileged_private));
}

static void prodtest_tropic_get_fido_masking_key(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t fido_masking_key[ECDSA_PRIVATE_KEY_SIZE] = {0};
  if (!secret_key_tropic_masking(fido_masking_key)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_FIDO_KEY_MASKING,
              "`secret_key_tropic_masking()` failed.");
    goto cleanup;
  }

  uint8_t output[sizeof(fido_masking_key) + NOISE_TAG_SIZE] = {0};
  if (!secure_channel_encrypt(fido_masking_key, sizeof(fido_masking_key), NULL,
                              0, output)) {
    // `secure_channel_handshake_2()` might not have been called
    cli_error(cli, PRODTEST_ERR_TROPIC_FIDO_KEY_ENCRYPT,
              "`secure_channel_encrypt()` failed.");
    goto cleanup;
  }

  cli_ok_hexdata(cli, output, sizeof(output));

cleanup:
  memzero(fido_masking_key, sizeof(fido_masking_key));
}

static lt_ret_t l2_get_req_len(const uint8_t* buffer, size_t buffer_length,
                               size_t* req_length) {
  if (!buffer || !req_length) {
    return LT_PARAM_ERR;
  }

  if (buffer_length < 2) {
    return LT_PARAM_ERR;
  }

  size_t length = buffer[1] + 2;

  if (length > buffer_length) {
    return LT_PARAM_ERR;
  }

  *req_length = length;

  return LT_OK;
}

static lt_ret_t l2_get_rsp_len(const uint8_t* buffer, size_t buffer_length,
                               size_t* rsp_length) {
  if (!buffer || !rsp_length) {
    return LT_PARAM_ERR;
  }

  if (buffer_length < 3) {
    return LT_PARAM_ERR;
  }

  size_t length = buffer[2] + 3;

  if (length > buffer_length) {
    return LT_PARAM_ERR;
  }

  *rsp_length = length;

  return LT_OK;
}

static void prodtest_tropic_handshake(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (!tropic_is_paired(cli)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_NOT_PAIRED,
              "`tropic-pair` must be called first.");
    return;
  }

  uint8_t input[35] = {0};  // 35 is the expected size of the handshake request
  size_t input_length = 0;
  if (!cli_arg_hex(cli, "hex-data", input, sizeof(input), &input_length)) {
    if (input_length == sizeof(input)) {
      cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_INPUT_LONG,
                "Input too long.");
    } else {
      cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_HEX_DECODE,
                "Hexadecimal decoding error.");
    }
    return;
  }
  if (input_length != sizeof(input)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_INPUT_LEN,
              "Unexpected input length. Expecting %d bytes.",
              (int)sizeof(input));
    return;
  }

  lt_ret_t ret = LT_FAIL;
  lt_l2_state_t l2_state = tropic_get_handle()->l2;

  size_t request_length = 0;
  ret = l2_get_req_len(input, sizeof(input), &request_length);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_REQ_LEN,
              "`get_req_len()` failed with error '%s'.", lt_ret_verbose(ret));
    return;
  }

  if (input_length != request_length) {
    cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_REQ_DAMAGED,
              "Request was damaged or truncated.");
    return;
  }

  memcpy(&l2_state.buff, input, request_length);

  ret = tropic_session_invalidate();
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_SEND,
              "`tropic_session_invalidate()` failed with error '%s'.",
              lt_ret_verbose(ret));
    return;
  }

  ret = lt_l2_send(&l2_state);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_L2_SEND,
              "`lt_l2_send()` failed with error '%s'.", lt_ret_verbose(ret));
    return;
  }

  ret = lt_l2_receive(&l2_state);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_L2_RECEIVE,
              "`lt_l2_receive()` failed with error '%s'.", lt_ret_verbose(ret));
    return;
  }

  size_t response_length = 0;
  ret = l2_get_rsp_len(l2_state.buff, sizeof(l2_state.buff), &response_length);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_RSP_LEN,
              "`get_rsp_len()` failed with error '%s'.", lt_ret_verbose(ret));
    return;
  }

  if (response_length !=
      51) {  // 51 is the expected size of the handshake response
    cli_error(cli, PRODTEST_ERR_TROPIC_HANDSHAKE_RSP_DAMAGED,
              "Unexpected response length. Expecting 51 bytes, got %d bytes.",
              (int)response_length);
    return;
  }

  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_1;

  cli_ok_hexdata(cli, &l2_state.buff, response_length);
}

static lt_ret_t l3_get_frame_len(const uint8_t* input, size_t input_length,
                                 size_t* cmd_length) {
  if (!input || !cmd_length) {
    return LT_PARAM_ERR;
  }

  if (input_length < 2) {
    return LT_PARAM_ERR;
  }

  size_t length = input[0] + (input[1] << 8) + 2 + 16;

  if (length > input_length) {
    return LT_PARAM_ERR;
  }

  *cmd_length = length;

  return LT_OK;
}

static void prodtest_tropic_send_command(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t input[TR01_L2_MAX_FRAME_SIZE] = {0};
  size_t input_length = 0;
  if (!cli_arg_hex(cli, "hex-data", input, sizeof(input), &input_length)) {
    if (input_length == sizeof(input)) {
      cli_error(cli, PRODTEST_ERR_TROPIC_CMD_INPUT_LONG, "Input too long.");
    } else {
      cli_error(cli, PRODTEST_ERR_TROPIC_CMD_HEX_DECODE,
                "Hexadecimal decoding error.");
    }
    return;
  }

  if (g_tropic_handshake_state != TROPIC_HANDSHAKE_STATE_1) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CMD_NO_HANDSHAKE,
              "You have to call `tropic-handshake` first.");
    return;
  }

  lt_ret_t ret = LT_FAIL;
  lt_l2_state_t l2_state = tropic_get_handle()->l2;

  size_t command_length = 0;
  ret = l3_get_frame_len(input, sizeof(input), &command_length);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CMD_L3_LEN_REQ,
              "`l3_get_cmd_len()` failed with error '%s'.",
              lt_ret_verbose(ret));
    return;
  }

  if (input_length != command_length) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CMD_REQ_DAMAGED,
              "Request was damaged or truncated.");
    return;
  }

  ret = lt_l2_send_encrypted_cmd(&l2_state, (uint8_t*)input, input_length);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CMD_SEND,
              "`lt_l2_send_encrypted_cmd()` failed with error '%s'.",
              lt_ret_verbose(ret));
    return;
  }

  uint8_t output[TR01_L2_MAX_FRAME_SIZE] = {0};
  ret = lt_l2_recv_encrypted_res(&l2_state, output, sizeof(output));
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CMD_RECEIVE,
              "`lt_l2_recv_encrypted_res()` failed with error '%s'.",
              lt_ret_verbose(ret));
    return;
  }

  size_t output_length = 0;
  ret = l3_get_frame_len(output, sizeof(output), &output_length);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CMD_L3_LEN_RSP,
              "`l3_get_cmd_len()` failed with error '%s'.",
              lt_ret_verbose(ret));
    return;
  }

  cli_ok_hexdata(cli, output, output_length);
}

// Brings the non-provisioned slots into a clean state in case a test fails to
// clean them up.
static bool tropic_tests_cleanup(cli_t* cli, lt_handle_t* h,
                                 bool unprivileged) {
  if (unprivileged) {
    cli_trace(cli,
              "Privileged session unavailable; cleaning only the unprivileged "
              "slot ranges.");
  }

  // R-memory data slots that were tested and can be erased.
  uint16_t rmem_first =
      unprivileged ? TROPIC_RMEM_UNPRIVILEGED_FIRST : TROPIC_RMEM_TEST_FIRST;
  for (uint16_t slot = rmem_first; slot <= TROPIC_RMEM_TEST_LAST; slot++) {
    uint8_t data[TROPIC_RMEM_TEST_DATA_SIZE] = {0};
    uint16_t read_size = 0;
    lt_ret_t res = lt_r_mem_data_read(h, slot, data, sizeof(data), &read_size);
    if (res == LT_L3_R_MEM_DATA_READ_SLOT_EMPTY) {
      continue;  // Expected: already empty.
    }
    cli_trace(cli, "WARNING: data slot %d was not empty (read '%s'); erasing.",
              slot, lt_ret_verbose(res));
    res = lt_r_mem_data_erase(h, slot);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TESTS_CLEANUP_RMEM,
                "Failed to erase data slot %d: '%s'", slot,
                lt_ret_verbose(res));
      return false;
    }
    res = lt_r_mem_data_read(h, slot, data, sizeof(data), &read_size);
    if (res != LT_L3_R_MEM_DATA_READ_SLOT_EMPTY) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TESTS_CLEANUP_RMEM,
                "Data slot %d still not empty after erase ('%s').", slot,
                lt_ret_verbose(res));
      return false;
    }
  }

  // ECC key slots above the device and FIDO keys.
  for (lt_ecc_slot_t slot = TROPIC_ECC_TEST_FIRST; slot <= TR01_ECC_SLOT_31;
       slot++) {
    uint8_t pubkey[64] = {0};
    lt_ecc_curve_type_t curve = 0;
    lt_ecc_key_origin_t origin = 0;
    lt_ret_t res =
        lt_ecc_key_read(h, slot, pubkey, sizeof(pubkey), &curve, &origin);
    if (res == LT_L3_INVALID_KEY) {
      continue;  // Expected: already empty.
    }
    cli_trace(cli, "WARNING: ECC slot %d was not empty (read '%s'); erasing.",
              slot, lt_ret_verbose(res));
    res = lt_ecc_key_erase(h, slot);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TESTS_CLEANUP_ECC,
                "Failed to erase ECC slot %d: '%s'", slot, lt_ret_verbose(res));
      return false;
    }
    res = lt_ecc_key_read(h, slot, pubkey, sizeof(pubkey), &curve, &origin);
    if (res != LT_L3_INVALID_KEY) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TESTS_CLEANUP_ECC,
                "ECC slot %d still not empty after erase ('%s').", slot,
                lt_ret_verbose(res));
      return false;
    }
  }

  // Monotonic counters cannot be de-initialized, so at least ensure that the
  // ones we can reinitialize are set to the maximum value if they were touched.
  lt_mcounter_index_t counter_first =
      unprivileged ? TROPIC_FIRST_UNPRIVILEGED_MCOUNTER : 0;
  for (lt_mcounter_index_t idx = counter_first; idx < TROPIC_MCOUNTER_COUNT;
       idx++) {
    uint32_t value = 0;
    lt_ret_t res = lt_mcounter_get(h, idx, &value);
    if (res == LT_L3_COUNTER_INVALID ||
        (res == LT_OK && value == TR01_MCOUNTER_VALUE_MAX)) {
      continue;  // Uninitialized or already at maximum.
    }
    res = lt_mcounter_init(h, idx, TR01_MCOUNTER_VALUE_MAX);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TESTS_CLEANUP_COUNTER,
                "Failed to reset counter %d to max: '%s'", idx,
                lt_ret_verbose(res));
      return false;
    }
    res = lt_mcounter_get(h, idx, &value);
    if (res != LT_OK || value != TR01_MCOUNTER_VALUE_MAX) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TESTS_CLEANUP_COUNTER,
                "Counter %d not at max after reset (value %u, '%s').", idx,
                (unsigned)value, lt_ret_verbose(res));
      return false;
    }
  }

  return true;
}

static void prodtest_tropic_lock(cli_t* cli) {
  // This function is:
  //   * idempotent (it can be called multiple times without changing the state
  //   of the device),
  //   * irreversible (it cannot be undone),
  //   * self-recovering (if the device is powered off during execution, it can
  //   be called again to continue from where it left off).

  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!tropic_is_paired(cli)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_NOT_PAIRED,
              "`tropic-pair` must be called first.");
    return;
  }

  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;
  lt_ret_t ret = LT_FAIL;

  ret = tropic_custom_session_start(cli, TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_INIT,
              "`tropic_custom_session_start()` for privileged key failed with "
              "error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  tropic_expected_config_t config = {0};
  if (!tropic_get_expected_tropic_config_from_distribution_version(
          tropic_prodtest_config_distribution_version, &config)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_EXPECTED_CONFIG,
              "Prodtest expected configuration not found.");
    return;
  }

  lt_config_t configuration_read = {0};
  lt_handle_t* tropic_handle = tropic_get_handle();

  ret = lt_r_config_erase(tropic_handle);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_ERASE,
              "`lt_r_config_erase()` failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  ret = lt_write_whole_R_config(tropic_handle, config.max_r_config);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_R_CONFIG_WRITE,
              "`lt_write_whole_R_config()` failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  ret = lt_read_whole_R_config(tropic_handle, &configuration_read);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_R_CONFIG_VERIFY_READ,
              "`lt_read_whole_R_config()` failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  if (memcmp(config.max_r_config, (uint8_t*)&configuration_read,
             sizeof(*config.max_r_config)) != 0) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_MISMATCH,
              "Reversible configuration mismatch after write.");
    return;
  }

  ret = lt_write_whole_I_config(tropic_handle, config.i_config);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_I_CONFIG_WRITE,
              "`lt_write_whole_I_config()` failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  ret = lt_read_whole_I_config_retry(tropic_handle, &configuration_read);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_I_CONFIG_VERIFY_READ,
              "`lt_read_whole_I_config_retry()` failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  if (memcmp(config.i_config, (uint8_t*)&configuration_read,
             sizeof(*config.i_config)) != 0) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_I_CONFIG_MISMATCH,
              "Irreversible configuration mismatch after write.");
    return;
  }

  ret = lt_r_mem_data_erase(tropic_handle,
                            TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_DISTR_VERSION_ERASE,
              "`lt_r_mem_data_erase()` failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  uint8_t distribution_version_bytes[sizeof(config.distribution_version)] = {0};
  write_be(distribution_version_bytes, config.distribution_version);
  ret = lt_r_mem_data_write(
      tropic_handle, TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT,
      distribution_version_bytes, sizeof(distribution_version_bytes));
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_DISTR_VERSION_WRITE,
              "`lt_r_mem_data_write()` failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  uint16_t distribution_version_read_length = 0;
  ret = lt_r_mem_data_read(
      tropic_handle, TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT,
      distribution_version_bytes, sizeof(distribution_version_bytes),
      &distribution_version_read_length);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_DISTR_VERSION_READ,
              "`lt_r_mem_data_read()` failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  if (distribution_version_read_length != sizeof(distribution_version_bytes)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_DISTR_VERSION_LEN,
              "Distribution version length mismatch after write. Expected %zu, "
              "got %u.",
              sizeof(distribution_version_bytes),
              (unsigned int)distribution_version_read_length);
    return;
  }

  if (config.distribution_version != read_be(distribution_version_bytes)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_DISTR_VERSION_MISMATCH,
              "Distribution version mismatch after write. Expected %u, got %u.",
              (unsigned int)config.distribution_version,
              (unsigned int)read_be(distribution_version_bytes));
    return;
  }

  ret = lt_r_mem_data_erase(tropic_handle,
                            TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_BACKUP_DISTR_VERSION_ERASE,
              "`lt_r_mem_data_erase()` failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  ret = lt_r_mem_data_read(
      tropic_handle, TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT,
      distribution_version_bytes, sizeof(distribution_version_bytes),
      &distribution_version_read_length);
  switch (ret) {
    case LT_L3_R_MEM_DATA_READ_SLOT_EMPTY:
      break;  // the backup slot is expected to be empty
    case LT_OK:
      cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_BACKUP_DISTR_VERSION_NOT_EMPTY,
                "The backup distribution version slot is not empty.");
      return;
    default:
      cli_error(cli, PRODTEST_ERR_TROPIC_LOCK_BACKUP_DISTR_VERSION_READ,
                "`lt_r_mem_data_read()` failed with error '%s'",
                lt_ret_verbose(ret));
      return;
  }

  cli_ok(cli, "");
}

static lt_ret_t data_write(lt_handle_t* h, uint16_t first_slot,
                           uint16_t slots_count, uint8_t* data,
                           size_t data_length) {
  const uint16_t last_data_slot = first_slot + slots_count - 1;
  if (slots_count == 0 || last_data_slot > TR01_R_MEM_DATA_SLOT_MAX) {
    return LT_PARAM_ERR;
  }

  const size_t prefix_length = 2;
  const size_t prefixed_data_length = data_length + prefix_length;
  const size_t total_slots_length = TROPIC_SLOT_MAX_SIZE_V1 * slots_count;
  if (prefixed_data_length > total_slots_length) {
    return LT_PARAM_ERR;
  }

  // The following of code can be further optimized:
  //   * It uses unnecessary amount of memory.
  //   * It writes to a data slot even if there is no data to be written.

  uint8_t prefixed_data[total_slots_length];
  memset(prefixed_data, 0, sizeof(prefixed_data));
  prefixed_data[0] = (data_length >> 8) & 0xFF;
  prefixed_data[1] = data_length & 0xFF;
  memcpy(prefixed_data + prefix_length, data, data_length);

  size_t position = 0;
  uint16_t slot = first_slot;

  while (slot <= last_data_slot) {
    lt_ret_t ret = LT_FAIL;

    ret = lt_r_mem_data_erase(h, slot);
    if (ret != LT_OK) {
      return ret;
    }

    ret = lt_r_mem_data_write(h, slot, prefixed_data + position,
                              TROPIC_SLOT_MAX_SIZE_V1);
    if (ret != LT_OK) {
      return ret;
    }

    position += TROPIC_SLOT_MAX_SIZE_V1;
    slot += 1;
  }

  return LT_OK;
}

static lt_ret_t data_read(lt_handle_t* h, uint16_t first_slot,
                          uint16_t slots_count, uint8_t* data,
                          size_t max_data_length, size_t* data_length) {
  const uint16_t last_data_slot = first_slot + slots_count - 1;
  if (slots_count == 0 || last_data_slot > TR01_R_MEM_DATA_SLOT_MAX) {
    return LT_PARAM_ERR;
  }

  // The following code can be further optimized:
  //   * It uses unnecessary amount of memory.
  //   * It reads from a data slot even if there is no data to be read.

  const size_t total_slots_length = TROPIC_SLOT_MAX_SIZE_V1 * slots_count;
  uint8_t prefixed_data[total_slots_length];
  size_t position = 0;
  uint16_t slot = first_slot;

  while (slot <= last_data_slot) {
    uint16_t slot_length = 0;
    lt_ret_t ret = lt_r_mem_data_read(h, slot, prefixed_data + position,
                                      TROPIC_SLOT_MAX_SIZE_V1, &slot_length);
    if (ret != LT_OK) {
      return ret;
    }

    if (slot_length != TROPIC_SLOT_MAX_SIZE_V1) {
      return LT_FAIL;
    }

    position += TROPIC_SLOT_MAX_SIZE_V1;
    slot += 1;
  }

  const size_t prefix_length = 2;
  size_t length = prefixed_data[0] << 8 | prefixed_data[1];
  if (length > max_data_length || length + prefix_length > total_slots_length) {
    return LT_PARAM_ERR;
  }

  *data_length = length;
  memcpy(data, prefixed_data + prefix_length, length);

  return LT_OK;
}

static bool check_device_cert_chain(cli_t* cli, const uint8_t* chain,
                                    size_t chain_size) {
  uint8_t challenge[CHALLENGE_SIZE] = {
      0};  // The challenge is intentionally constant zero.

  ed25519_signature signature = {0};

  lt_ret_t ret = lt_ecc_eddsa_sign(tropic_get_handle(), TROPIC_DEVICE_KEY_SLOT,
                                   challenge, sizeof(challenge), signature);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CERT_SIGN,
              "`lt_ecc_eddsa_sign()` failed with error '%s'",
              lt_ret_verbose(ret));
    return false;
  }

  if (!check_cert_chain(cli, chain, chain_size, signature, sizeof(signature),
                        challenge)) {
    return false;
  }

  return true;
}

static void cert_write(cli_t* cli, uint16_t first_slot, uint16_t slots_count) {
  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  size_t certificate_length = 0;
  uint8_t certificate[TROPIC_SLOT_MAX_SIZE_V1 * slots_count];
  if (!cli_arg_hex(cli, "hex-data", certificate, sizeof(certificate),
                   &certificate_length)) {
    if (certificate_length == sizeof(certificate)) {
      cli_error(cli, PRODTEST_ERR_TROPIC_CERT_WRITE_TOO_LONG,
                "Certificate too long.");
    } else {
      cli_error(cli, PRODTEST_ERR_TROPIC_CERT_WRITE_HEX_DECODE,
                "Hexadecimal decoding error.");
    }
    return;
  }

  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  lt_ret_t ret =
      tropic_custom_session_start(cli, TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CERT_WRITE_CHAIN,
              "`tropic_custom_session_start()` for privileged key failed with "
              "error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  if (first_slot == TROPIC_DEVICE_CERT_FIRST_SLOT &&
      !check_device_cert_chain(cli, certificate, certificate_length)) {
    // Error returned by check_device_cert_chain().
    return;
  }

  lt_handle_t* tropic_handle = tropic_get_handle();

  ret = data_write(tropic_handle, first_slot, slots_count, certificate,
                   certificate_length);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CERT_WRITE_DATA,
              "`data_write()` failed with error '%s'", lt_ret_verbose(ret));
    return;
  }

  size_t certificate_read_length = 0;
  uint8_t certificate_read[TROPIC_SLOT_MAX_SIZE_V1 * slots_count];
  ret = data_read(tropic_handle, first_slot, slots_count, certificate_read,
                  sizeof(certificate_read), &certificate_read_length);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CERT_WRITE_READ_BACK,
              "`data_read()` failed with error '%s'", lt_ret_verbose(ret));
    return;
  }
  if (certificate_read_length != certificate_length ||
      memcmp(certificate, certificate_read, certificate_length) != 0) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CERT_WRITE_MISMATCH,
              "Certificate does not match the expected value");
    return;
  }

  cli_ok(cli, "");
}

static void cert_read(cli_t* cli, uint16_t first_slot, uint16_t slots_count) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;
  lt_ret_t ret = LT_FAIL;

  ret = tropic_custom_session_start(cli, TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CERT_READ_DATA,
              "`tropic_custom_session_start()` for privileged key failed with "
              "error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  uint8_t certificate[TROPIC_SLOT_MAX_SIZE_V1 * slots_count];
  size_t certificate_length = 0;
  ret = data_read(tropic_get_handle(), first_slot, slots_count, certificate,
                  sizeof(certificate), &certificate_length);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_CERT_READ_FAILED,
              "Reading certificate failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  cli_ok_hexdata(cli, certificate, certificate_length);
}

static void prodtest_tropic_certfido_write(cli_t* cli) {
  cert_write(cli, TROPIC_FIDO_CERT_FIRST_SLOT, TROPIC_FIDO_CERT_SLOT_COUNT);
}

static void prodtest_tropic_certdev_write(cli_t* cli) {
  cert_write(cli, TROPIC_DEVICE_CERT_FIRST_SLOT, TROPIC_DEVICE_CERT_SLOT_COUNT);
}

static void prodtest_tropic_certfido_read(cli_t* cli) {
  cert_read(cli, TROPIC_FIDO_CERT_FIRST_SLOT, TROPIC_FIDO_CERT_SLOT_COUNT);
}

static void prodtest_tropic_certdev_read(cli_t* cli) {
  cert_read(cli, TROPIC_DEVICE_CERT_FIRST_SLOT, TROPIC_DEVICE_CERT_SLOT_COUNT);
}

static void pubkey_read(cli_t* cli, lt_ecc_slot_t slot,
                        const uint8_t masking_key[ECDSA_PRIVATE_KEY_SIZE]) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_ret_t ret = LT_FAIL;

  ret = tropic_custom_session_start(cli, TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_PUBKEY_READ_LT,
              "`tropic_custom_session_start()` for privileged key failed with "
              "error '%s'",
              lt_ret_verbose(ret));
    return;
  }

  uint8_t public_key[ECDSA_PUBLIC_KEY_SIZE] = {0x04};
  lt_ecc_curve_type_t curve_type = 0;
  lt_ecc_key_origin_t origin = 0;
  ret = lt_ecc_key_read(tropic_get_handle(), slot, &public_key[1],
                        ECDSA_PUBLIC_KEY_SIZE - 1, &curve_type, &origin);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_PUBKEY_READ_KEY,
              "`lt_ecc_key_read()` failed with error '%s'",
              lt_ret_verbose(ret));
    return;
  }
  if (curve_type != TR01_CURVE_P256) {
    cli_error(cli, PRODTEST_ERR_TROPIC_PUBKEY_READ_CURVE,
              "Curve type is not P-256");
    return;
  }

  if (masking_key != NULL) {
    if (ecdsa_unmask_public_key(&nist256p1, masking_key, public_key,
                                public_key) != 0) {
      cli_error(cli, PRODTEST_ERR_TROPIC_PUBKEY_READ_UNMASK,
                "key unmasking error");
      return;
    }
  }

  cli_ok_hexdata(cli, public_key, sizeof(public_key));
}

static void prodtest_tropic_keyfido_read(cli_t* cli) {
#ifdef SECRET_KEY_MASKING
  uint8_t masking_key[ECDSA_PRIVATE_KEY_SIZE] = {0};
  if (secret_key_tropic_masking(masking_key) != sectrue) {
    cli_error(cli, PRODTEST_ERR_TROPIC_KEYFIDO_READ_MASK,
              "masking key not available");
    return;
  }
  pubkey_read(cli, TROPIC_FIDO_KEY_SLOT, masking_key);
  memzero(masking_key, sizeof(masking_key));
#else
  pubkey_read(cli, TROPIC_FIDO_KEY_SLOT, NULL);
#endif  // SECRET_KEY_MASKING
}

static void prodtest_tropic_update_fw(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_handle_t* h = tropic_get_handle();

  lt_chip_id_t chip_id = {0};
  if (lt_get_info_chip_id(h, &chip_id) != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_UPDATE_CHIP_ID, "Unable to get CHIP ID");
    return;
  }

  cli_trace(cli, "Silicon revision: %c%c%c%c", chip_id.silicon_rev[0],
            chip_id.silicon_rev[1], chip_id.silicon_rev[2],
            chip_id.silicon_rev[3]);

#ifdef LT_SILICON_REV_ABAB
  if (strncmp((char*)chip_id.silicon_rev, "ABAB", 4) != 0) {
    cli_error(cli, PRODTEST_ERR_TROPIC_UPDATE_WRONG_REVISION,
              "Wrong tropic chip silicon revision");
    return;
  }
#else
  cli_error(cli, PRODTEST_ERR_TROPIC_UPDATE_NO_REVISION,
            "Tropic chip silicon revision not set");
  return;
#endif

  // For firmware update chip must be rebooted into MAINTENANCE mode.
  cli_trace(cli, "Rebooting into Maintenance mode");
  lt_ret_t ret = lt_reboot(h, TR01_MAINTENANCE_REBOOT);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_UPDATE_REBOOT_MAINTENANCE,
              "lt_reboot() failed, ret=%s", lt_ret_verbose(ret));
    return;
  }

  cli_trace(cli, "Chip is executing bootloader");

  cli_trace(cli, "Updating RISC-V and SPECT FW");
  ret = lt_do_mutable_fw_update(h, fw_CPU, sizeof(fw_CPU), fw_SPECT,
                                sizeof(fw_SPECT));
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_UPDATE_FW, "FW update failed, ret=%s",
              lt_ret_verbose(ret));
    goto cleanup;
  }

  // To read firmware versions chip must be rebooted into application mode.
  cli_trace(cli, "Rebooting into Application mode");
  ret = lt_reboot(h, TR01_REBOOT);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_UPDATE_REBOOT_APP,
              "lt_reboot() failed, ret=%s", lt_ret_verbose(ret));
    goto cleanup;
  }

  cli_trace(cli, "Reading RISC-V FW version");

  uint8_t risc_fw_ver[TR01_L2_GET_INFO_RISCV_FW_SIZE] = {0};
  ret = lt_get_info_riscv_fw_ver(h, risc_fw_ver);

  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_UPDATE_RISCV_VERSION,
              "Failed to get RISC-V FW version, ret=%s", lt_ret_verbose(ret));
    goto cleanup;
  }

  cli_trace(cli,
            "Chip is executing RISC-V application FW version: %d.%d.%d (+ .%d)",
            risc_fw_ver[3], risc_fw_ver[2], risc_fw_ver[1], risc_fw_ver[0]);

  cli_trace(cli, "Reading SPECT FW version");
  uint8_t spect_fw_ver[TR01_L2_GET_INFO_SPECT_FW_SIZE] = {0};
  ret = lt_get_info_spect_fw_ver(h, spect_fw_ver);

  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_UPDATE_SPECT_VERSION,
              "Failed to get SPECT FW version, ret=%s", lt_ret_verbose(ret));
    goto cleanup;
  }

  cli_trace(cli, "Chip is executing SPECT FW version: %d.%d.%d (+ .%d)",
            spect_fw_ver[3], spect_fw_ver[2], spect_fw_ver[1], spect_fw_ver[0]);

  cli_ok(cli, "");

  return;

cleanup:
  tropic_deinit();
}

// Per-command identifiers used as PRNG seeds so that different commands sample
// different slot subsets.
typedef enum {
  TROPIC_CMD_STRESS_MAC_AND_DESTROY = 1,
  TROPIC_CMD_TEST_MAC_AND_DESTROY,
  TROPIC_CMD_TEST_COUNTER,
  TROPIC_CMD_TEST_RMEM,
} tropic_command_id_t;

// Deterministic PRNG (xorshift32) used for slot selection only.
static uint32_t tropic_prng_next(uint32_t* state) {
  uint32_t x = *state;
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  *state = x;
  return x;
}

// Selects slots for a slot-based test, writing them to `out`. [lo, hi) is the
// valid range of slots for the test. `*slot_count` is the requested number of
// slots; it is clamped in place to the number available (`hi - lo`). Returns
// false (after reporting via `cli`) only for an invalid explicit-slot request.
static bool tropic_select_slots(cli_t* cli, tropic_command_id_t command_id,
                                uint16_t lo, uint16_t hi, uint32_t* slot_count,
                                int32_t explicit_slot, uint16_t* out) {
  if (explicit_slot >= 0) {
    if (*slot_count != 1) {
      cli_error(cli, PRODTEST_ERR_TROPIC_EXPLICIT_SLOT_COUNT,
                "An explicit slot requires a slot count of 1.");
      return false;
    }
    if (explicit_slot < lo || explicit_slot >= hi) {
      cli_error(cli, PRODTEST_ERR_TROPIC_EXPLICIT_SLOT_RANGE,
                "Slot %d is outside the valid range [%d, %d).", explicit_slot,
                lo, hi);
      return false;
    }
    out[0] = explicit_slot;
    return true;
  }

  size_t max_slots = hi - lo;
  if (*slot_count > max_slots) {
    cli_trace(cli, "Clamping slot count to %u available slots.",
              (unsigned)max_slots);
    *slot_count = max_slots;
  }

  uint16_t candidates[max_slots];
  for (size_t i = 0; i < max_slots; i++) {
    candidates[i] = lo + i;
  }

  uint32_t prng_state = ((uint32_t)command_id << 24) ^ *slot_count;
  for (size_t i = 0; i < *slot_count; i++) {
    // A Fisher-Yates shuffle step to select a random slot from the remaining
    // candidates.
    size_t j = i + (tropic_prng_next(&prng_state) % (max_slots - i));
    out[i] = candidates[j];
    candidates[j] = candidates[i];
  }
  return true;
}

// Ensures a secure session is established and reports which pairing key was
// used if `pairing_key_index` is non-NULL.
static bool tropic_ensure_session(cli_t* cli,
                                  lt_pkey_index_t* pairing_key_index) {
  static const lt_pkey_index_t keys[] = {
      TROPIC_PRIVILEGED_PAIRING_KEY_SLOT,
      TROPIC_FACTORY_PAIRING_KEY_SLOT,
      TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT,
  };
  lt_ret_t results[ARRAY_LENGTH(keys)];
  for (size_t i = 0; i < ARRAY_LENGTH(keys); i++) {
    results[i] = tropic_custom_session_start(NULL, keys[i]);
    if (results[i] == LT_OK) {
      if (pairing_key_index != NULL) {
        *pairing_key_index = keys[i];
      }
      return true;
    }
  }

  // No key worked. Explain why each attempt failed.
  for (size_t i = 0; i < ARRAY_LENGTH(keys); i++) {
    cli_trace(
        cli,
        "`tropic_custom_session_start()` for key %d failed with error '%s'",
        keys[i], lt_ret_verbose(results[i]));
  }
  cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_NO_PAIRING_KEY,
            "No pairing key is available");
  return false;
}

static bool tropic_parse_iterations(cli_t* cli, uint32_t* iterations);
static bool tropic_parse_iterations_and_slots(cli_t* cli, uint32_t* iterations,
                                              uint32_t* slot_count,
                                              int32_t* explicit_slot);

// Stress test: reinitialize the chip repeatedly to provoke startup faults.
static void prodtest_tropic_stress_init(cli_t* cli) {
  uint32_t iterations = 100;
  uint32_t delay_ms = 0;
  uint32_t argc = cli_arg_count(cli);
  if (argc > 2) {
    cli_error_arg_count(cli);
    return;
  }
  if (argc >= 1 && !cli_arg_uint32(cli, "iterations", &iterations)) {
    cli_error_arg(cli, "Expecting number of iterations.");
    return;
  }
  if (argc >= 2 && !cli_arg_uint32(cli, "delay-ms", &delay_ms)) {
    cli_error_arg(cli, "Expecting init delay in ms.");
    return;
  }
  if (iterations == 0) {
    cli_error_arg(cli, "Iterations must be greater than 0.");
    return;
  }
  cli_trace(cli, "Initialization iterations: %u. Init delay: %u ms.",
            (unsigned)iterations, (unsigned)delay_ms);

  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  for (int i = 0; i < iterations; i++) {
    tropic_deinit();
    // Simulate a delay between suspend and wake-up.
    systick_delay_ms(delay_ms);
    if (!tropic_init()) {
      cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_INIT,
                "Call #%d of `tropic_init()` failed", i + 1);
      return;
    }
    if (!tropic_wait_for_ready(cli)) {
      cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_READY,
                "Call #%d of `tropic_wait_for_ready()` failed", i + 1);
      return;
    }
  }
  cli_ok(cli, "");
}

// Stress test: tear down and re-establish the secure session repeatedly.
static void prodtest_tropic_stress_session(cli_t* cli) {
  uint32_t iterations = 5;
  if (!tropic_parse_iterations(cli, &iterations)) {
    return;
  }
  cli_trace(cli, "Session iterations: %u.", (unsigned)iterations);

  lt_pkey_index_t pairing_key_index = -1;
  if (!tropic_ensure_session(cli, &pairing_key_index)) {
    return;
  }

  for (int i = 0; i < iterations; i++) {
    lt_ret_t res = tropic_session_invalidate();
    if (res != LT_OK) {
      cli_error(
          cli, PRODTEST_ERR_TROPIC_STRESS_SESSION_INVALIDATE,
          "Call #%d of `tropic_session_invalidate()` failed with error '%s'",
          i + 1, lt_ret_verbose(res));
      return;
    }
    res = tropic_custom_session_start(cli, pairing_key_index);
    if (res != LT_OK) {
      cli_error(
          cli, PRODTEST_ERR_TROPIC_STRESS_SESSION_START,
          "Call #%d of `tropic_custom_session_start()` failed with error '%s'",
          i + 1, lt_ret_verbose(res));
      return;
    }
  }
  cli_ok(cli, "");
}

// Stress test: hammer MAC-and-destroy on a sample of slots with random inputs,
// without checking the results, to provoke alarm mode.
static void prodtest_tropic_stress_mac_and_destroy(cli_t* cli) {
  uint32_t iterations = 3;
  uint32_t slot_count = TROPIC_MAC_AND_DESTROY_SLOT_TOTAL;
  int32_t explicit_slot = -1;
  if (!tropic_parse_iterations_and_slots(cli, &iterations, &slot_count,
                                         &explicit_slot)) {
    return;
  }
  cli_trace(cli, "Iterations per slot: %u. Slot count: %u. Explicit slot: %d.",
            (unsigned)iterations, (unsigned)slot_count, (int)explicit_slot);

  lt_pkey_index_t pairing_key_index = -1;
  if (!tropic_ensure_session(cli, &pairing_key_index)) {
    return;
  }
  bool unprivileged = pairing_key_index == TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT;
  if (unprivileged) {
    cli_trace(cli,
              "Privileged session unavailable; sampling only the unprivileged "
              "MAC-and-destroy range.");
  }
  uint16_t first = unprivileged ? TROPIC_FIRST_MAC_AND_DESTROY_SLOT_UNPRIVILEGED
                                : TROPIC_FIRST_MAC_AND_DESTROY_SLOT_PRIVILEGED;

  uint16_t slots[TROPIC_MAC_AND_DESTROY_SLOT_TOTAL];
  if (!tropic_select_slots(cli, TROPIC_CMD_STRESS_MAC_AND_DESTROY, first,
                           TROPIC_MAC_AND_DESTROY_SLOT_TOTAL, &slot_count,
                           explicit_slot, slots)) {
    return;
  }

  lt_handle_t* h = tropic_get_handle();
  for (int s = 0; s < slot_count; s++) {
    lt_mac_and_destroy_slot_t slot = slots[s];
    for (int i = 0; i < iterations; i++) {
      uint8_t buffer[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
      rng_fill_buffer(buffer, sizeof(buffer));
      lt_ret_t res = lt_mac_and_destroy(h, slot, buffer, buffer);
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_MAC_AND_DESTROY,
                  "Call #%d of `lt_mac_and_destroy()` for slot %d failed with "
                  "error '%s'",
                  i + 1, slot, lt_ret_verbose(res));
        return;
      }
    }
  }
  cli_ok(cli, "");
}

// Integrity test: verify MAC-and-destroy produces consistent results on a
// sample of slots.
// for each slot in sample_slots:
//   generate reset_key and input randomly
//   M&D(reset_key)
//   output_0 = M&D(input)
//   for i in 1..iterations:
//     M&D(reset_key)
//     output = M&D(input)
//     assert output == output_0
static void prodtest_tropic_test_mac_and_destroy(cli_t* cli) {
  uint32_t iterations = 2;
  uint32_t slot_count = TROPIC_MAC_AND_DESTROY_SLOT_TOTAL / 2;
  int32_t explicit_slot = -1;
  if (!tropic_parse_iterations_and_slots(cli, &iterations, &slot_count,
                                         &explicit_slot)) {
    return;
  }
  cli_trace(cli, "Iterations per slot: %u. Slot count: %u. Explicit slot: %d.",
            (unsigned)iterations, (unsigned)slot_count, (int)explicit_slot);

  lt_pkey_index_t pairing_key_index = -1;
  if (!tropic_ensure_session(cli, &pairing_key_index)) {
    return;
  }
  bool unprivileged = pairing_key_index == TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT;
  if (unprivileged) {
    cli_trace(cli,
              "Privileged session unavailable; sampling only the unprivileged "
              "MAC-and-destroy range.");
  }
  uint16_t first = unprivileged ? TROPIC_FIRST_MAC_AND_DESTROY_SLOT_UNPRIVILEGED
                                : TROPIC_FIRST_MAC_AND_DESTROY_SLOT_PRIVILEGED;

  uint16_t slots[TROPIC_MAC_AND_DESTROY_SLOT_TOTAL];
  if (!tropic_select_slots(cli, TROPIC_CMD_TEST_MAC_AND_DESTROY, first,
                           TROPIC_MAC_AND_DESTROY_SLOT_TOTAL, &slot_count,
                           explicit_slot, slots)) {
    return;
  }

  lt_handle_t* h = tropic_get_handle();
  for (int s = 0; s < slot_count; s++) {
    lt_mac_and_destroy_slot_t slot = slots[s];

    uint8_t reset_key[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
    uint8_t input[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
    uint8_t output_0[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
    uint8_t output[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
    rng_fill_buffer(reset_key, sizeof(reset_key));
    rng_fill_buffer(input, sizeof(input));

    // Setup: M&D(reset_key)
    lt_ret_t res = lt_mac_and_destroy(h, slot, reset_key, output);
    if (res != LT_OK) {
      cli_error(
          cli, PRODTEST_ERR_TROPIC_TEST_MAC_AND_DESTROY,
          "`lt_mac_and_destroy()` setup for slot %d failed with error '%s'",
          slot, lt_ret_verbose(res));
      return;
    }
    // Measure: output_0 = M&D(input)
    res = lt_mac_and_destroy(h, slot, input, output_0);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TEST_MAC_AND_DESTROY,
                "`lt_mac_and_destroy()` initial measurement for slot %d failed "
                "with error '%s'",
                slot, lt_ret_verbose(res));
      return;
    }

    for (int i = 0; i < iterations; i++) {
      // Reset: M&D(reset_key)
      res = lt_mac_and_destroy(h, slot, reset_key, output);
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_TEST_MAC_AND_DESTROY,
                  "`lt_mac_and_destroy()` reset for slot %d failed at "
                  "iteration #%d with error '%s'",
                  slot, i + 1, lt_ret_verbose(res));
        return;
      }
      // Re-measure: output = M&D(input)
      res = lt_mac_and_destroy(h, slot, input, output);
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_TEST_MAC_AND_DESTROY,
                  "`lt_mac_and_destroy()` re-measurement for slot %d failed at "
                  "iteration #%d with error '%s'",
                  slot, i + 1, lt_ret_verbose(res));
        return;
      }
      if (memcmp(output, output_0, sizeof(output_0)) != 0) {
        cli_error(cli, PRODTEST_ERR_TROPIC_TEST_MAC_AND_DESTROY_MISMATCH,
                  "MAC-and-destroy inconsistent on slot %d at iteration #%d",
                  slot, i + 1);
        return;
      }
    }
  }
  cli_ok(cli, "");
}

// Integrity test: generate an ECC key, then sign random messages and verify
// each signature against the slot's public key.
static void prodtest_tropic_test_sign(cli_t* cli) {
  uint32_t iterations = 10;
  if (!tropic_parse_iterations(cli, &iterations)) {
    return;
  }
  cli_trace(cli, "Signing iterations: %u. ECC slot: %d.", (unsigned)iterations,
            TR01_ECC_SLOT_31);

  if (!tropic_ensure_session(cli, NULL)) {
    return;
  }

  lt_handle_t* h = tropic_get_handle();
  // Slot 31 is usable by both privileged and unprivileged sessions.
  lt_ecc_slot_t ecc_slot = TR01_ECC_SLOT_31;

  ed25519_public_key public_key = {0};
  uint8_t message[32] = {0};
  ed25519_signature signature = {0};

  lt_ret_t res = lt_ecc_key_generate(h, ecc_slot, TR01_CURVE_ED25519);
  if (res != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_KEY_GENERATE,
              "`lt_ecc_key_generate()` for slot %d failed with error '%s'",
              ecc_slot, lt_ret_verbose(res));
    goto cleanup_error;
  }

  lt_ecc_curve_type_t curve_type = 0;
  lt_ecc_key_origin_t origin = 0;
  res = lt_ecc_key_read(h, ecc_slot, public_key, sizeof(public_key),
                        &curve_type, &origin);
  if (res != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_TEST_SIGN_KEY_READ,
              "`lt_ecc_key_read()` for slot %d failed with error '%s'",
              ecc_slot, lt_ret_verbose(res));
    goto cleanup_error;
  }
  if (curve_type != TR01_CURVE_ED25519) {
    cli_error(cli, PRODTEST_ERR_TROPIC_TEST_SIGN_CURVE,
              "Curve type on slot %d is not Ed25519 (got %d)", ecc_slot,
              curve_type);
    goto cleanup_error;
  }

  for (int i = 0; i < iterations; i++) {
    rng_fill_buffer(message, sizeof(message));
    res = lt_ecc_eddsa_sign(h, ecc_slot, message, sizeof(message), signature);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_EDDSA_SIGN,
                "Call #%d of `lt_ecc_eddsa_sign()` for slot %d failed with "
                "error '%s'",
                i + 1, ecc_slot, lt_ret_verbose(res));
      goto cleanup_error;
    }
    if (ed25519_sign_open(message, sizeof(message), public_key, signature) !=
        0) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TEST_SIGN_VERIFY,
                "Signature #%d for slot %d failed verification", i + 1,
                ecc_slot);
      goto cleanup_error;
    }
  }

  res = lt_ecc_key_erase(h, ecc_slot);
  if (res != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_KEY_ERASE,
              "`lt_ecc_key_erase()` for slot %d failed with error '%s'",
              ecc_slot, lt_ret_verbose(res));
    return;
  }
  cli_ok(cli, "");
  return;

cleanup_error:
  lt_ecc_key_erase(h, ecc_slot);
  return;
}

// Integrity test: verify monotonic counters set, read back, and decrement
// correctly on a sample of counters.
static void prodtest_tropic_test_counter(cli_t* cli) {
  uint32_t iterations = 5;
  uint32_t slot_count = TROPIC_MCOUNTER_COUNT;
  int32_t explicit_slot = -1;
  if (!tropic_parse_iterations_and_slots(cli, &iterations, &slot_count,
                                         &explicit_slot)) {
    return;
  }
  cli_trace(cli,
            "Iterations per counter: %u. Counters: %u. Explicit counter: %d.",
            (unsigned)iterations, (unsigned)slot_count, (int)explicit_slot);

  lt_pkey_index_t pairing_key_index = -1;
  if (!tropic_ensure_session(cli, &pairing_key_index)) {
    return;
  }
  bool unprivileged = pairing_key_index == TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT;
  if (unprivileged) {
    cli_trace(cli,
              "Privileged session unavailable; testing only the unprivileged "
              "counters.");
  }

  uint16_t slots[TROPIC_MCOUNTER_COUNT];
  uint16_t first = unprivileged ? TROPIC_FIRST_UNPRIVILEGED_MCOUNTER : 0;
  if (!tropic_select_slots(cli, TROPIC_CMD_TEST_COUNTER, first,
                           TROPIC_MCOUNTER_COUNT, &slot_count, explicit_slot,
                           slots)) {
    return;
  }

  lt_handle_t* h = tropic_get_handle();
  for (int s = 0; s < slot_count; s++) {
    lt_mcounter_index_t idx = slots[s];

    lt_ret_t res = lt_mcounter_init(h, idx, iterations);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TEST_COUNTER_INIT,
                "`lt_mcounter_init()` for counter %d failed with error '%s'",
                idx, lt_ret_verbose(res));
      return;
    }

    uint32_t value = 0;
    res = lt_mcounter_get(h, idx, &value);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TEST_COUNTER_GET,
                "`lt_mcounter_get()` for counter %d failed with error '%s'",
                idx, lt_ret_verbose(res));
      return;
    }
    if (value != iterations) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TEST_COUNTER_INIT_MISMATCH,
                "Counter %d read %d after init, expected %d", idx, value,
                iterations);
      return;
    }

    for (int i = 0; i < iterations; i++) {
      res = lt_mcounter_update(h, idx);
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_TEST_COUNTER_UPDATE,
                  "`lt_mcounter_update()` for counter %d failed at iteration "
                  "#%d with error '%s'",
                  idx, i + 1, lt_ret_verbose(res));
        return;
      }
      res = lt_mcounter_get(h, idx, &value);
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_TEST_COUNTER_GET,
                  "`lt_mcounter_get()` for counter %d failed at iteration #%d "
                  "with error '%s'",
                  idx, i + 1, lt_ret_verbose(res));
        return;
      }
      uint32_t expected = iterations - i - 1;
      if (value != expected) {
        cli_error(cli, PRODTEST_ERR_TROPIC_TEST_COUNTER_MISMATCH,
                  "Counter %d read %d after %d decrements, expected %d", idx,
                  value, i + 1, expected);
        return;
      }
    }

    // Re-initialize counter so it is never left depleted.
    res = lt_mcounter_init(h, idx, TR01_MCOUNTER_VALUE_MAX);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TEST_COUNTER_INIT,
                "`lt_mcounter_init()` for counter %d failed with error '%s'",
                idx, lt_ret_verbose(res));
      return;
    }
  }
  cli_ok(cli, "");
}

// Integrity test: write random data to a sample of R-memory slots and read it
// back. Restricted to the range above the certificate slots so it can never
// overwrite them.
static void prodtest_tropic_test_rmem(cli_t* cli) {
  uint32_t iterations = 1;
  uint32_t slot_count = 25;
  int32_t explicit_slot = -1;
  if (!tropic_parse_iterations_and_slots(cli, &iterations, &slot_count,
                                         &explicit_slot)) {
    return;
  }
  cli_trace(cli, "Iterations per slot: %u. Slot count: %u. Explicit slot: %d.",
            (unsigned)iterations, (unsigned)slot_count, (int)explicit_slot);

  lt_pkey_index_t pairing_key_index = -1;
  if (!tropic_ensure_session(cli, &pairing_key_index)) {
    return;
  }
  bool unprivileged = pairing_key_index == TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT;
  if (unprivileged) {
    cli_trace(cli,
              "Privileged session unavailable; testing only the unprivileged "
              "R-memory range.");
  }

  uint16_t slots[TROPIC_RMEM_TEST_COUNT];
  uint16_t first =
      unprivileged ? TROPIC_RMEM_UNPRIVILEGED_FIRST : TROPIC_RMEM_TEST_FIRST;
  if (!tropic_select_slots(cli, TROPIC_CMD_TEST_RMEM, first,
                           TROPIC_RMEM_TEST_LAST + 1, &slot_count,
                           explicit_slot, slots)) {
    return;
  }

  lt_handle_t* h = tropic_get_handle();
  for (int s = 0; s < slot_count; s++) {
    uint16_t slot = slots[s];
    for (int i = 0; i < iterations; i++) {
      uint8_t write_data[TROPIC_RMEM_TEST_DATA_SIZE] = {0};
      uint8_t read_data[TROPIC_RMEM_TEST_DATA_SIZE] = {0};
      rng_fill_buffer(write_data, sizeof(write_data));

      // A write to a non-empty slot fails, so erase first (this also clears the
      // data written by the previous iteration).
      lt_ret_t res = lt_r_mem_data_erase(h, slot);
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_TEST_RMEM_ERASE,
                  "`lt_r_mem_data_erase()` for slot %d failed at iteration #%d "
                  "with error '%s'",
                  slot, i + 1, lt_ret_verbose(res));
        return;
      }
      res = lt_r_mem_data_write(h, slot, write_data, sizeof(write_data));
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_TEST_RMEM_WRITE,
                  "`lt_r_mem_data_write()` for slot %d failed at iteration #%d "
                  "with error '%s'",
                  slot, i + 1, lt_ret_verbose(res));
        lt_r_mem_data_erase(h, slot);
        return;
      }
      uint16_t read_size = 0;
      res =
          lt_r_mem_data_read(h, slot, read_data, sizeof(read_data), &read_size);
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_TEST_RMEM_READ,
                  "`lt_r_mem_data_read()` for slot %d failed at iteration #%d "
                  "with error '%s'",
                  slot, i + 1, lt_ret_verbose(res));
        lt_r_mem_data_erase(h, slot);
        return;
      }
      if (read_size != sizeof(write_data) ||
          memcmp(read_data, write_data, sizeof(write_data)) != 0) {
        cli_error(cli, PRODTEST_ERR_TROPIC_TEST_RMEM_MISMATCH,
                  "R-memory slot %d read-back mismatch at iteration #%d", slot,
                  i + 1);
        lt_r_mem_data_erase(h, slot);
        return;
      }
    }

    // Leave the slot empty.
    lt_ret_t res = lt_r_mem_data_erase(h, slot);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TEST_RMEM_ERASE,
                "`lt_r_mem_data_erase()` for slot %d failed with error '%s'",
                slot, lt_ret_verbose(res));
      return;
    }
  }
  cli_ok(cli, "");
}

// Integrity test: sanity-check the TRNG output (non-zero and not identical to
// the previous value).
static void prodtest_tropic_test_rng(cli_t* cli) {
  uint32_t iterations = 100;
  if (!tropic_parse_iterations(cli, &iterations)) {
    return;
  }
  cli_trace(cli, "RNG iterations: %u.", (unsigned)iterations);

  if (!tropic_ensure_session(cli, NULL)) {
    return;
  }

  lt_handle_t* h = tropic_get_handle();
  uint8_t previous[32] = {0};
  for (int i = 0; i < iterations; i++) {
    uint8_t value[32] = {0};
    lt_ret_t res = lt_random_value_get(h, value, sizeof(value));
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_RANDOM_GET,
                "Call #%d of `lt_random_value_get()` failed with error '%s'",
                i + 1, lt_ret_verbose(res));
      return;
    }

    bool all_zero = true;
    for (size_t j = 0; j < sizeof(value); j++) {
      if (value[j] != 0) {
        all_zero = false;
        break;
      }
    }
    if (all_zero) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TEST_RNG_ZERO,
                "RNG returned an all-zero value at iteration #%d", i + 1);
      return;
    }
    if (i > 0 && memcmp(value, previous, sizeof(value)) == 0) {
      cli_error(cli, PRODTEST_ERR_TROPIC_TEST_RNG_REPEAT,
                "RNG returned a repeated value at iteration #%d", i + 1);
      return;
    }
    memcpy(previous, value, sizeof(value));
  }
  cli_ok(cli, "");
}

static bool tropic_parse_iterations(cli_t* cli, uint32_t* iterations) {
  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return false;
  }
  if (cli_arg_count(cli) != 0 &&
      !cli_arg_uint32(cli, "iterations", iterations)) {
    cli_error_arg(cli, "Expecting number of iterations.");
    return false;
  }
  if (*iterations == 0) {
    cli_error_arg(cli, "Iterations must be greater than 0.");
    return false;
  }
  return true;
}

// Parses `[<iterations> <slot_count> [<slot>]]`. `iterations` is the number of
// test iterations per slot. The optional third argument pins the exact slot to
// use (only valid with a slot count of 1).
static bool tropic_parse_iterations_and_slots(cli_t* cli, uint32_t* iterations,
                                              uint32_t* slot_count,
                                              int32_t* explicit_slot) {
  *explicit_slot = -1;
  uint32_t argc = cli_arg_count(cli);
  if (argc != 0 && argc != 2 && argc != 3) {
    cli_error_arg_count(cli);
    return false;
  }
  if (argc >= 2) {
    if (!cli_arg_uint32(cli, "iterations", iterations)) {
      cli_error_arg(cli, "Expecting number of iterations.");
      return false;
    }
    if (!cli_arg_uint32(cli, "slot-count", slot_count)) {
      cli_error_arg(cli, "Expecting slot count.");
      return false;
    }
  }
  if (*iterations == 0) {
    cli_error_arg(cli, "Iterations must be greater than 0.");
    return false;
  }
  if (*slot_count == 0) {
    cli_error_arg(cli, "Slot count must be greater than 0.");
    return false;
  }
  if (argc == 3) {
    uint32_t slot = 0;
    if (!cli_arg_uint32(cli, "slot", &slot)) {
      cli_error_arg(cli, "Expecting slot number.");
      return false;
    }
    *explicit_slot = slot;
  }
  return true;
}

// DEPRECATED: superseded by the `tropic-stress-*` and `tropic-test-*` commands;
// will be removed in a future release. Retains its original behavior and
// parameter set for backward compatibility.
static void prodtest_tropic_stress_test(cli_t* cli) {
  cli_trace(
      cli,
      "DEPRECATED: `tropic-stress-test` will be removed; use `tropic-test`.");

  if (cli_arg_count(cli) > 6) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t init_iterations = 5;
  uint32_t start_session_iterations = 10;
  uint32_t mac_and_destroy_slot_count = TROPIC_MAC_AND_DESTROY_SLOT_COUNT;
  uint32_t mac_and_destroy_per_slot_iterations = 3;
  uint32_t signing_iterations = 10;
  uint32_t rng_iterations = 10;

  if (cli_arg_count(cli) != 0) {
    if (!cli_arg_uint32(cli, "init-iterations", &init_iterations)) {
      cli_error_arg(cli, "Expecting number of initialization iterations.");
      return;
    }
    if (!cli_arg_uint32(cli, "start-session-iterations",
                        &start_session_iterations)) {
      cli_error_arg(cli, "Expecting number of start-session iterations.");
      return;
    }
    if (!cli_arg_uint32(cli, "mac-and-destroy-slot-count",
                        &mac_and_destroy_slot_count) ||
        mac_and_destroy_slot_count > TROPIC_MAC_AND_DESTROY_SLOT_COUNT) {
      cli_error_arg(cli,
                    "Expecting number of MAC-and-destroy slots in range 0-%d.",
                    TROPIC_MAC_AND_DESTROY_SLOT_COUNT);
      return;
    }
    if (!cli_arg_uint32(cli, "mac-and-destroy-per-slot-iterations",
                        &mac_and_destroy_per_slot_iterations)) {
      cli_error_arg(cli,
                    "Expecting number of MAC-and-destroy iterations per slot.");
      return;
    }
    if (!cli_arg_uint32(cli, "signing-iterations", &signing_iterations)) {
      cli_error_arg(cli, "Expecting number of signing iterations.");
      return;
    }
    if (!cli_arg_uint32(cli, "rng-iterations", &rng_iterations)) {
      cli_error_arg(cli, "Expecting number of RNG iterations.");
      return;
    }
  }

  cli_trace(cli, "Initialization iterations: %d", init_iterations);
  cli_trace(cli, "Start-session iterations: %d", start_session_iterations);
  cli_trace(cli, "MAC-and-destroy slot count: %d", mac_and_destroy_slot_count);
  cli_trace(cli, "MAC-and-destroy iterations per slot: %d",
            mac_and_destroy_per_slot_iterations);
  cli_trace(cli, "Signing iterations: %d", signing_iterations);
  cli_trace(cli, "RNG iterations: %d", rng_iterations);

  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  // test Tropic gets initialized
  for (int i = 0; i < init_iterations; i++) {
    tropic_deinit();
    if (!tropic_init()) {
      cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_INIT,
                "Call #%d of `tropic_init()` failed", i + 1);
      return;
    }
    if (!tropic_wait_for_ready(cli)) {
      cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_READY,
                "Call #%d of `tropic_wait_for_ready()` failed", i + 1);
      return;
    }
  }

  lt_ret_t res = LT_FAIL;
  lt_pkey_index_t pairing_key_index = -1;

  if (!tropic_ensure_session(cli, &pairing_key_index)) {
    return;
  }

  cli_trace(cli, "Established session using pairing key %d", pairing_key_index);

  // Test `lt_session_start()`
  for (int i = 0; i < start_session_iterations; i++) {
    res = tropic_session_invalidate();
    if (res != LT_OK) {
      cli_error(
          cli, PRODTEST_ERR_TROPIC_STRESS_SESSION_INVALIDATE,
          "`Call #%d of tropic_session_invalidate() failed with error '%s'",
          i + 1, lt_ret_verbose(res));
      return;
    }
    res = tropic_custom_session_start(cli, pairing_key_index);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_SESSION_START,
                "Call #%d of `tropic_custom_session_start()"
                "failed with error '%s'",
                i + 1, lt_ret_verbose(res));
      return;
    }
  }

  // Test `lt_mac_and_destroy()`
  for (int slot_index = TROPIC_FIRST_MAC_AND_DESTROY_SLOT_UNPRIVILEGED;
       slot_index < TROPIC_FIRST_MAC_AND_DESTROY_SLOT_UNPRIVILEGED +
                        mac_and_destroy_slot_count;
       slot_index++) {
    for (int i = 0; i < mac_and_destroy_per_slot_iterations; i++) {
      uint8_t buffer[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
      rng_fill_buffer(buffer, sizeof(buffer));
      res = lt_mac_and_destroy(tropic_get_handle(), slot_index, buffer, buffer);
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_SIGN_FAILED,
                  "Call #%d of `lt_mac_and_destroy()` for slot %d failed "
                  "with error '%s'",
                  i + 1, slot_index, lt_ret_verbose(res));
        return;
      }
    }
  }

  // Test `lt_ecc_key_generate()`
  uint8_t message[32] = {0};
  ed25519_signature signature = {0};
  lt_ecc_slot_t ecc_slot = TR01_ECC_SLOT_31;
  res = lt_ecc_key_generate(tropic_get_handle(), ecc_slot, TR01_CURVE_ED25519);
  if (res != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_KEY_GENERATE,
              "`lt_ecc_key_generate()` failed with error '%s'",
              lt_ret_verbose(res));
    return;
  }
  for (int i = 0; i < signing_iterations; i++) {
    rng_fill_buffer(message, sizeof(message));
    res = lt_ecc_eddsa_sign(tropic_get_handle(), ecc_slot, message,
                            sizeof(message), signature);
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_EDDSA_SIGN,
                "Call #%d of `lt_ecc_eddsa_sign()` failed with error '%s'",
                i + 1, lt_ret_verbose(res));
      lt_ecc_key_erase(tropic_get_handle(), ecc_slot);
      return;
    }
  }
  res = lt_ecc_key_erase(tropic_get_handle(), ecc_slot);
  if (res != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_KEY_ERASE,
              "`lt_ecc_key_erase()` failed with error '%s'",
              lt_ret_verbose(res));
    return;
  }

  // Test lt_random_value_get()
  for (int i = 0; i < rng_iterations; i++) {
    uint8_t random_value[32] = {0};
    res = lt_random_value_get(tropic_get_handle(), random_value,
                              sizeof(random_value));
    if (res != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_STRESS_RANDOM_GET,
                "Call #%d of `lt_random_value_get()` failed with error '%s'",
                i + 1, lt_ret_verbose(res));
      return;
    }
  }

  cli_ok(cli, "");
}

static void prodtest_tropic_benchmark(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  lt_ret_t res = LT_FAIL;
  lt_pkey_index_t pairing_key_index = -1;

  if (!tropic_ensure_session(cli, &pairing_key_index)) {
    return;
  }

  lt_handle_t* h = tropic_get_handle();
  uint32_t start_ms = 0;

  const int iterations = 25;
  const uint16_t timing_data_slot = TR01_R_MEM_DATA_SLOT_MAX;
  const lt_mcounter_index_t timing_mcounter_slot = TR01_MCOUNTER_INDEX_15;

  // Ensure data slot is empty before the first iteration
  res = lt_r_mem_data_erase(h, timing_data_slot);
  if (res != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_MEM_ERASE,
              "`lt_r_mem_data_erase()` failed with error '%s'",
              lt_ret_verbose(res));
    return;
  }

  uint32_t total_session_start_ms = 0;
  uint32_t total_mac_and_destroy_ms = 0;
  uint32_t total_r_mem_data_write_ms = 0;
  uint32_t total_r_mem_data_read_ms = 0;
  uint32_t total_r_mem_data_erase_ms = 0;
  uint32_t total_mcounter_init_ms = 0;
  uint32_t total_mcounter_get_ms = 0;
  uint32_t total_mcounter_update_ms = 0;
  uint32_t total_random_value_get_ms = 0;

  for (int i = 0; i < iterations; i++) {
    // Measure `tropic_custom_session_start()`
    {
      res = tropic_session_invalidate();
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_SESSION_INVALIDATE,
                  "`tropic_session_invalidate()` failed with error '%s'",
                  lt_ret_verbose(res));
        return;
      }
      start_ms = systick_ms();
      res = tropic_custom_session_start(cli, pairing_key_index);
      total_session_start_ms += systick_ms() - start_ms;
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_SESSION_START,
                  "`tropic_custom_session_start()` failed with error '%s'",
                  lt_ret_verbose(res));
        return;
      }
    }

    // Measure `lt_mac_and_destroy()`
    {
      uint8_t buffer[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
      rng_fill_buffer(buffer, sizeof(buffer));
      start_ms = systick_ms();
      res = lt_mac_and_destroy(
          h, TROPIC_FIRST_MAC_AND_DESTROY_SLOT_UNPRIVILEGED, buffer, buffer);
      total_mac_and_destroy_ms += systick_ms() - start_ms;
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_MAC_AND_DESTROY,
                  "`lt_mac_and_destroy()` failed with error '%s'",
                  lt_ret_verbose(res));
        return;
      }
    }

    uint8_t data[320] = {0};

    // Measure `lt_r_mem_data_write()` (320 bytes)
    {
      rng_fill_buffer(data, sizeof(data));
      start_ms = systick_ms();
      res = lt_r_mem_data_write(h, timing_data_slot, data, sizeof(data));
      total_r_mem_data_write_ms += systick_ms() - start_ms;
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_MEM_WRITE,
                  "`lt_r_mem_data_write()` failed with error '%s'",
                  lt_ret_verbose(res));
        return;
      }
    }

    // Measure `lt_r_mem_data_read()` (320 bytes)
    {
      uint16_t read_size = 0;
      start_ms = systick_ms();
      res = lt_r_mem_data_read(h, timing_data_slot, data, sizeof(data),
                               &read_size);
      total_r_mem_data_read_ms += systick_ms() - start_ms;
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_MEM_READ,
                  "`lt_r_mem_data_read()` failed with error '%s'",
                  lt_ret_verbose(res));
        return;
      }
    }

    // Measure `lt_r_mem_data_erase()`
    {
      start_ms = systick_ms();
      res = lt_r_mem_data_erase(h, timing_data_slot);
      total_r_mem_data_erase_ms += systick_ms() - start_ms;
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_MEM_ERASE,
                  "`lt_r_mem_data_erase()` failed with error '%s'",
                  lt_ret_verbose(res));
        return;
      }
    }

    // Measure `lt_mcounter_init()`
    {
      start_ms = systick_ms();
      res = lt_mcounter_init(h, timing_mcounter_slot, 1);
      total_mcounter_init_ms += systick_ms() - start_ms;
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_MCOUNTER_INIT,
                  "`lt_mcounter_init()` failed with error '%s'",
                  lt_ret_verbose(res));
        return;
      }
    }

    // Measure `lt_mcounter_get()`
    {
      uint32_t counter_value = 0;
      start_ms = systick_ms();
      res = lt_mcounter_get(h, timing_mcounter_slot, &counter_value);
      total_mcounter_get_ms += systick_ms() - start_ms;
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_MCOUNTER_GET,
                  "`lt_mcounter_get()` failed with error '%s'",
                  lt_ret_verbose(res));
        return;
      }
    }

    // Measure `lt_mcounter_update()`
    {
      start_ms = systick_ms();
      res = lt_mcounter_update(h, timing_mcounter_slot);
      total_mcounter_update_ms += systick_ms() - start_ms;
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_MCOUNTER_UPDATE,
                  "`lt_mcounter_update()` failed with error '%s'",
                  lt_ret_verbose(res));
        return;
      }
    }

    // Measure `lt_random_value_get()` (32 bytes)
    {
      uint8_t buffer[32] = {0};
      start_ms = systick_ms();
      res = lt_random_value_get(h, buffer, sizeof(buffer));
      total_random_value_get_ms += systick_ms() - start_ms;
      if (res != LT_OK) {
        cli_error(cli, PRODTEST_ERR_TROPIC_BENCHMARK_RANDOM_GET,
                  "`lt_random_value_get()` failed with error '%s'",
                  lt_ret_verbose(res));
        return;
      }
    }
  }

#define CLI_TRACE_AVERAGE(name, total) \
  cli_trace(cli, name " %lu ms", (((total) + iterations / 2) / iterations))

  CLI_TRACE_AVERAGE("session_start()   ", total_session_start_ms);
  CLI_TRACE_AVERAGE("mac_and_destroy() ", total_mac_and_destroy_ms);
  CLI_TRACE_AVERAGE("r_mem_data_write()", total_r_mem_data_write_ms);
  CLI_TRACE_AVERAGE("r_mem_data_read() ", total_r_mem_data_read_ms);
  CLI_TRACE_AVERAGE("r_mem_data_erase()", total_r_mem_data_erase_ms);
  CLI_TRACE_AVERAGE("mcounter_init()   ", total_mcounter_init_ms);
  CLI_TRACE_AVERAGE("mcounter_get()    ", total_mcounter_get_ms);
  CLI_TRACE_AVERAGE("mcounter_update() ", total_mcounter_update_ms);
  CLI_TRACE_AVERAGE("random_value_get()", total_random_value_get_ms);

#undef CLI_TRACE_AVERAGE

  cli_ok(cli, "");
}

static bool privileged_session_start(cli_t* cli) {
  g_tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  if (tropic_custom_session_start(cli, TROPIC_PRIVILEGED_PAIRING_KEY_SLOT) ==
      LT_OK) {
    return true;
  }

  if (tropic_custom_session_start(cli, TROPIC_FACTORY_PAIRING_KEY_SLOT) ==
      LT_OK) {
    return true;
  }

  return false;
}

static lt_ret_t tropic_erase_all_slots_internal(cli_t* cli,
                                                lt_handle_t* tropic_handle) {
  cli_trace(cli, "Erasing all ECC key slots, data slots and MAC&Destroy slots");

  lt_ret_t ret = LT_OK;

  // Erase all 32 ECC key slots
  for (lt_ecc_slot_t slot = TR01_ECC_SLOT_0; slot <= TR01_ECC_SLOT_31; slot++) {
    ret = lt_ecc_key_erase_retry(tropic_handle, slot);
    if (ret != LT_OK) {
      cli_trace(cli, "ECC slot %2d: Erase failed (error %s)", slot,
                lt_ret_verbose(ret));
      return ret;
    }
  }

  // Erase all 512 R_MEM data slots
  for (uint16_t slot = 0; slot <= TR01_R_MEM_DATA_SLOT_MAX; slot++) {
    ret = lt_r_mem_data_erase_retry(tropic_handle, slot);
    if (ret != LT_OK) {
      cli_trace(cli, "Data slot %3d: Erase failed (error %s)", slot,
                lt_ret_verbose(ret));
      return ret;
    }
  }

  // Destroy all 128 MAC and destroy slots by triggering self-destruct
  // Dummy data to trigger MAC computation
  uint8_t dummy_data[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
  // Output buffer for MAC result
  uint8_t mac_output[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
  for (lt_mac_and_destroy_slot_t slot = 0;
       slot <= TR01_MAC_AND_DESTROY_SLOT_127; slot++) {
    ret = lt_mac_and_destroy_retry(tropic_handle, slot, dummy_data, mac_output);
    if (ret != LT_OK) {
      cli_trace(cli, "M&D slot %3d: Destroy failed (error %s)", slot,
                lt_ret_verbose(ret));
      return ret;
    }
  }

  cli_trace(cli, "All cryptographic data erased successfully");
  return LT_OK;
}

static void prodtest_tropic_erase_all_slots(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!privileged_session_start(cli)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_ERASE_SLOTS_SESSION,
              "`privileged_session_start()` failed.");
    return;
  }

  lt_handle_t* tropic_handle = tropic_get_handle();

  lt_ret_t ret = tropic_erase_all_slots_internal(cli, tropic_handle);
  if (ret == LT_OK) {
    cli_ok(cli, "");
  } else {
    cli_error(cli, PRODTEST_ERR_TROPIC_ERASE_SLOTS, "Erase operation failed");
  }
}

static void prodtest_tropic_set_sensors(cli_t* cli) {
  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  // Default to 0x00000000, which enables all sensors.
  uint32_t new_sensors_config = 0;
  if (cli_arg_count(cli) == 1) {
    uint8_t input[4] = {0};
    size_t input_length = 0;
    if (!cli_arg_hex(cli, "hex-data", input, sizeof(input), &input_length)) {
      if (input_length == sizeof(input)) {
        cli_error(cli, PRODTEST_ERR_TROPIC_SENSORS_INPUT_LONG,
                  "Input too long.");
      } else {
        cli_error(cli, PRODTEST_ERR_TROPIC_SENSORS_HEX_DECODE,
                  "Hexadecimal decoding error.");
      }
      return;
    }

    if (input_length != sizeof(input)) {
      cli_error(cli, PRODTEST_ERR_TROPIC_SENSORS_INPUT_LEN,
                "Expected 4 bytes (8 hex digits) for uint32.");
      return;
    }

    new_sensors_config = ((uint32_t)input[0] << 24) |
                         ((uint32_t)input[1] << 16) |
                         ((uint32_t)input[2] << 8) | ((uint32_t)input[3]);
  }

  lt_pkey_index_t pairing_key_index = 0;
  if (!tropic_ensure_session(cli, &pairing_key_index)) {
    return;
  }

  lt_handle_t* tropic_handle = tropic_get_handle();

  // No need to wipe under a factory session. Tropic is unprovisioned.
  if (pairing_key_index != TROPIC_FACTORY_PAIRING_KEY_SLOT) {
    lt_ret_t ret = tropic_erase_all_slots_internal(cli, tropic_handle);
    if (ret != LT_OK) {
      cli_error(cli, PRODTEST_ERR_TROPIC_SENSORS_ERASE,
                "Erase operation failed");
      return;
    }
  }

  lt_config_t configuration = {0};
  lt_ret_t ret = lt_read_whole_R_config_retry(tropic_handle, &configuration);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_SENSORS_READ_CONFIG,
              "`lt_read_whole_R_config()` failed with error %s",
              lt_ret_verbose(ret));
    return;
  }

  // Update sensors in the configuration
  configuration.obj[TR01_CFG_SENSORS_IDX] = new_sensors_config;

  ret = lt_erase_and_write_R_config_retry(tropic_handle, &configuration);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_SENSORS_SLOT_WRITE,
              "`lt_erase_and_write_R_config_retry()` failed with error %s",
              lt_ret_verbose(ret));
    return;
  }

  // Verify the write
  lt_config_t verify_configuration = {0};
  ret = lt_read_whole_R_config_retry(tropic_handle, &verify_configuration);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_SENSORS_SLOT_READ,
              "`lt_r_config_read()` verification failed with error %s",
              lt_ret_verbose(ret));
    return;
  }

  if (memcmp(&configuration, &verify_configuration,
             sizeof(verify_configuration)) != 0) {
    cli_error(cli, PRODTEST_ERR_TROPIC_SENSORS_WRITE_VERIFY,
              "Configuration was not written correctly.");
    return;
  }

  // The sensor configuration only takes effect after a reboot.
  ret = lt_reboot(tropic_handle, TR01_REBOOT);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_SENSORS_REBOOT,
              "`lt_reboot()` failed with error %s", lt_ret_verbose(ret));
    return;
  }
  tropic_deinit();
  if (!tropic_init() || !tropic_wait_for_ready(cli)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_SENSORS_REBOOT,
              "Re-initialization after reboot failed.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_tropic_read_sensors(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_handle_t* tropic_handle = tropic_get_handle();

  if (!privileged_session_start(cli)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_READ_SENSORS_SESSION,
              "`privileged_session_start()` failed.");
    return;
  }

  // Read current configuration
  uint32_t sensors_config = 0;
  lt_ret_t ret =
      lt_r_config_read(tropic_handle, TR01_CFG_SENSORS_ADDR, &sensors_config);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_READ_SENSORS_CONFIG,
              "`lt_r_config_read()` failed with error %s", lt_ret_verbose(ret));
    return;
  }

  cli_ok(cli, "0x%08X", sensors_config);
}

static void prodtest_tropic_read_configs(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_handle_t* tropic_handle = tropic_get_handle();

  if (!privileged_session_start(cli)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_READ_CONFIGS_SESSION,
              "`privileged_session_start()` failed.");
    return;
  }

  // read reversible configuration
  lt_config_t r_config = {0};
  lt_ret_t ret = lt_read_whole_R_config_retry(tropic_handle, &r_config);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_READ_CONFIGS_R_CONFIG,
              "`lt_read_whole_R_config()` failed with error %s",
              lt_ret_verbose(ret));
    return;
  }

  cli_trace(cli, "=== Reversible Configuration ===");
  for (size_t i = 0; i < LT_CONFIG_OBJ_CNT; i++) {
    cli_trace(cli, "  R_config.obj[%zu]: 0x%08X  (addr: 0x%02zX)", i,
              r_config.obj[i], i * 0x08);
  }

  // read irreversible configuration
  lt_config_t i_config = {0};
  ret = lt_read_whole_I_config_retry(tropic_handle, &i_config);
  if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_READ_CONFIGS_I_CONFIG,

              "`lt_read_whole_I_config_retry()` failed with error %s",
              lt_ret_verbose(ret));
    return;
  }

  cli_trace(cli, "");
  cli_trace(cli, "=== Irreversible Configuration ===");
  for (size_t i = 0; i < LT_CONFIG_OBJ_CNT; i++) {
    cli_trace(cli, "  I_config.obj[%zu]: 0x%08X  (addr: 0x%02zX)", i,
              i_config.obj[i], i * 0x08);
  }

  cli_trace(cli, "");
  cli_trace(cli, "=== Configuration Distribution Version ===");
  uint8_t read_value_bytes[sizeof(uint32_t)] = {0};
  uint16_t read_length = 0;
  ret = lt_r_mem_data_read(
      tropic_get_handle(), TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT,
      read_value_bytes, sizeof(read_value_bytes), &read_length);
  if (ret == LT_L3_R_MEM_DATA_READ_SLOT_EMPTY) {
    cli_trace(cli, "Configuration distribution version: empty");
  } else if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_READ_CONFIGS_DISTR_VERSION_READ,
              "`lt_r_mem_data_read()` failed with error %s",
              lt_ret_verbose(ret));
    return;
  } else if (read_length != sizeof(read_value_bytes)) {
    cli_error(cli, PRODTEST_ERR_TROPIC_READ_CONFIGS_DISTR_VERSION_LEN,
              "Unexpected length of configuration distribution version data");
    return;
  } else {
    cli_trace(cli, "Configuration distribution version: %u",
              (unsigned int)read_be(read_value_bytes));
  }
  read_length = 0;
  ret = lt_r_mem_data_read(
      tropic_get_handle(), TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT,
      read_value_bytes, sizeof(read_value_bytes), &read_length);
  if (ret == LT_L3_R_MEM_DATA_READ_SLOT_EMPTY) {
    cli_trace(cli, "Configuration backup distribution version: empty");
  } else if (ret != LT_OK) {
    cli_error(cli, PRODTEST_ERR_TROPIC_READ_CONFIGS_BACKUP_DISTR_VERSION_READ,
              "`lt_r_mem_data_read()` failed with error %s",
              lt_ret_verbose(ret));
    return;
  } else if (read_length != sizeof(read_value_bytes)) {
    cli_error(
        cli, PRODTEST_ERR_TROPIC_READ_CONFIGS_BACKUP_DISTR_VERSION_LEN,
        "Unexpected length of configuration backup distribution version data");
    return;
  } else {
    cli_trace(cli, "Configuration backup distribution version: %u",
              (unsigned int)read_be(read_value_bytes));
  }

  cli_ok(cli, "");
}

static void prodtest_tropic_tests_cleanup(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }
  lt_pkey_index_t pairing_key_index = -1;
  if (!tropic_ensure_session(cli, &pairing_key_index)) {
    return;
  }
  bool unprivileged = pairing_key_index == TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT;
  if (!tropic_tests_cleanup(cli, tropic_get_handle(), unprivileged)) {
    // Error already reported by tropic_tests_cleanup().
    return;
  }
  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "tropic-tests-cleanup",
  .func = prodtest_tropic_tests_cleanup,
  .info = "Reset the slots written by the tropic-test-* commands to a clean state",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-get-riscv-fw-version",
  .func = prodtest_tropic_get_riscv_fw_version,
  .info = "Get RISCV FW version",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-get-spect-fw-version",
  .func = prodtest_tropic_get_spect_fw_version,
  .info = "Get SPECT FW version",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-get-chip-id",
  .func = prodtest_tropic_get_chip_id,
  .info = "Get Tropic CHIP ID",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-certtropic-read",
  .func = prodtest_tropic_certtropic_read,
  .info = "Read the X.509 certificate chain issued by Tropic",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-lock-check",
  .func = prodtest_tropic_lock_check,
  .info = "Check whether Tropic has been configured",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-pair",
  .func = prodtest_tropic_pair,
  .info = "Pair with Tropic",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-get-access-credential",
  .func = prodtest_tropic_get_access_credential,
  .info = "Get Tropic access credential",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-get-fido-masking-key",
  .func = prodtest_tropic_get_fido_masking_key,
  .info = "Get Tropic FIDO masking key",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-handshake",
  .func = prodtest_tropic_handshake,
  .info = "Perform handshake with Tropic",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "tropic-send-command",
  .func = prodtest_tropic_send_command,
  .info = "Send command to Tropic",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "tropic-certdev-read",
  .func = prodtest_tropic_certdev_read,
  .info = "Read the device's X.509 certificate from Tropic",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-certdev-write",
  .func = prodtest_tropic_certdev_write,
  .info = "Write the device's X.509 certificate to Tropic",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "tropic-certfido-read",
  .func = prodtest_tropic_certfido_read,
  .info = "Read the X.509 certificate for the FIDO key from Tropic",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-certfido-write",
  .func = prodtest_tropic_certfido_write,
  .info = "Write the X.509 certificate for the FIDO key to Tropic",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "tropic-keyfido-read",
  .func = prodtest_tropic_keyfido_read,
  .info = "Read the FIDO public key from Tropic.",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-lock",
  .func = prodtest_tropic_lock,
  .info = "Irreversibly configure Tropic",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-update-fw",
  .func = prodtest_tropic_update_fw,
  .info = "Update tropic FW to embedded binary",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-stress-init",
  .func = prodtest_tropic_stress_init,
  .info = "Stress test Tropic initialization",
  .args = "[<iterations> [<delay-ms>]]"
);

PRODTEST_CLI_CMD(
  .name = "tropic-stress-session",
  .func = prodtest_tropic_stress_session,
  .info = "Stress test Tropic session establishment",
  .args = "[<iterations>]"
);

PRODTEST_CLI_CMD(
  .name = "tropic-stress-mac-and-destroy",
  .func = prodtest_tropic_stress_mac_and_destroy,
  .info = "Stress test Tropic MAC-and-destroy, one MAC-and-destroy per iteration",
  .args = "[<iterations> <slot-count> [<slot>]]"
);

PRODTEST_CLI_CMD(
  .name = "tropic-test-mac-and-destroy",
  .func = prodtest_tropic_test_mac_and_destroy,
  .info = "Check Tropic MAC-and-destroy, one consistency check per iteration against first result",
  .args = "[<iterations> <slot-count> [<slot>]]"
);

PRODTEST_CLI_CMD(
  .name = "tropic-test-sign",
  .func = prodtest_tropic_test_sign,
  .info = "Check Tropic EdDSA signing, one sign & verify per iteration",
  .args = "[<iterations>]"
);

PRODTEST_CLI_CMD(
  .name = "tropic-test-counter",
  .func = prodtest_tropic_test_counter,
  .info = "Check Tropic monotonic counter integrity, one decrement & check per iteration",
  .args = "[<iterations> <slot-count> [<slot>]]"
);

PRODTEST_CLI_CMD(
  .name = "tropic-test-rmem",
  .func = prodtest_tropic_test_rmem,
  .info = "Check Tropic R-memory slot integrity, one write & read cycle per iteration",
  .args = "[<iterations> <slot-count> [<slot>]]"
);

PRODTEST_CLI_CMD(
  .name = "tropic-test-rng",
  .func = prodtest_tropic_test_rng,
  .info = "Sanity-check Tropic TRNG output",
  .args = "[<iterations>]"
);

PRODTEST_CLI_CMD(
  .name = "tropic-stress-test",
  .func = prodtest_tropic_stress_test,
  .info = "DEPRECATED: use tropic-test; will be removed",
  .args = "[<init-iterations> <start-session-iterations> <mac-and-destroy-slot-count> <mac-and-destroy-per-slot-iterations> <signing-iterations> <rng-iterations>]"
);

PRODTEST_CLI_CMD(
  .name = "tropic-benchmark",
  .func = prodtest_tropic_benchmark,
  .info = "Measure actual duration of Tropic operations",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-set-sensors",
  .func = prodtest_tropic_set_sensors,
  .info = "Set the reversible sensor configuration and reboot Tropic to apply it. Enables all sensors by default.",
  .args = "[<hex-data>]"
);

PRODTEST_CLI_CMD(
  .name = "tropic-read-sensors",
  .func = prodtest_tropic_read_sensors,
  .info = "Read the current sensor reversible configuration from Tropic",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-read-configs",
  .func = prodtest_tropic_read_configs,
  .info = "Read whole I_config and R_config.",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-erase-all-slots",
  .func = prodtest_tropic_erase_all_slots,
  .info = "Erase all ECC keys, data slots and Mac&Destroy slots. Keeps pairing keys intact.",
  .args = ""
);


#endif // USE_TROPIC
