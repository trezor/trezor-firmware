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

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sec/tropic.h>
#include <sys/systick.h>

#include <sec/secret_keys.h>

#include "memzero.h"

#include "libtropic.h"

#include "secure_channel.h"

typedef enum {
  TROPIC_HANDSHAKE_STATE_0,  // Handshake has not been initiated yet
  TROPIC_HANDSHAKE_STATE_1,  // Handshake completed (after calling
                             // `tropic-handshake`), `tropic-send-command` can
                             // be called
} tropic_handshake_state_t;

static tropic_handshake_state_t tropic_handshake_state =
    TROPIC_HANDSHAKE_STATE_0;

static bool locked = false;

static void prodtest_tropic_get_riscv_fw_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_handle_t* handle = tropic_get_handle();

  uint8_t version[LT_L2_GET_INFO_RISCV_FW_SIZE] = {0};
  if (lt_get_info_riscv_fw_ver(handle, version, sizeof(version)) != LT_OK) {
    cli_error(cli, CLI_ERROR, "Unable to get RISCV FW version");
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

  lt_handle_t* handle = tropic_get_handle();

  uint8_t version[LT_L2_GET_INFO_SPECT_FW_SIZE] = {0};
  if (lt_get_info_spect_fw_ver(handle, version, sizeof(version)) != LT_OK) {
    cli_error(cli, CLI_ERROR, "Unable to get SPECT FW version");
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

  lt_handle_t* handle = tropic_get_handle();

  lt_chip_id_t chip_id = {0};
  if (lt_get_info_chip_id(handle, &chip_id) != LT_OK) {
    cli_error(cli, CLI_ERROR, "Unable to get CHIP ID");
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

  static uint8_t certificate[3000] = {0};

  // TODO: Implement properly

  cli_ok_hexdata(cli, certificate, sizeof(certificate));
}

static void prodtest_tropic_lock_check(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  // TODO: Implement properly

  if (locked) {
    cli_ok(cli, "YES");
  } else {
    cli_ok(cli, "NO");
  }
}

static void prodtest_tropic_pair(cli_t* cli) {
  // If this functions successfully completes, it is ensured that:
  //  * The factory pairing key in `PAIRING_KEY_SLOT_INDEX_0` is invalidated.
  //  * The unprivileged pairing key is written to `PAIRING_KEY_SLOT_INDEX_1`.
  //  * The privileged pairing key is written to `PAIRING_KEY_SLOT_INDEX_2`.
  //  * The pairing key in `PAIRING_KEY_SLOT_INDEX_3` is empty.

  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  curve25519_key unprivileged_private = {0};
  if (secret_key_tropic_pairing_unprivileged(unprivileged_private) != sectrue) {
    cli_error(cli, CLI_ERROR,
              "`secret_key_tropic_pairing_unprivileged()` failed.");
    goto cleanup;
  }

  curve25519_key privileged_private = {0};
  if (secret_key_tropic_pairing_privileged(privileged_private) != sectrue) {
    cli_error(cli, CLI_ERROR,
              "`secret_key_tropic_pairing_unprivileged()` failed.");
    goto cleanup;
  }

  // TODO: Implement properly

  systick_delay_ms(600);

  cli_ok(cli, "");

cleanup:
  memzero(unprivileged_private, sizeof(unprivileged_private));
  memzero(privileged_private, sizeof(privileged_private));
}

static void prodtest_tropic_get_access_credential(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  curve25519_key hsm_private_key = {0};
  if (secret_key_tropic_pairing_unprivileged(hsm_private_key) != sectrue) {
    cli_error(cli, CLI_ERROR,
              "`secret_key_tropic_pairing_unprivileged()` failed.");
    goto cleanup;
  }

  // TODO: Retrieve the certificate
  uint8_t tropic_certificate[600] = {0};

  uint8_t output[sizeof(hsm_private_key) + NOISE_TAG_SIZE] = {0};
  if (!secure_channel_encrypt((uint8_t*)hsm_private_key,
                              sizeof(hsm_private_key), tropic_certificate,
                              sizeof(tropic_certificate), output)) {
    // TODO: Consider distinguishing between cryptography error and state error
    cli_error(cli, CLI_ERROR,
              "`secure_channel_encrypt()` failed. You have to "
              "call `secure-channel-handshake-2` first.");
    goto cleanup;
  }

  cli_ok_hexdata(cli, output, sizeof(output));

cleanup:
  memzero(hsm_private_key, sizeof(hsm_private_key));
}

static void prodtest_tropic_get_fido_masking_key(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t fido_masking_key[ECDSA_PRIVATE_KEY_SIZE] = {0};
  if (!secret_key_tropic_masking(fido_masking_key)) {
    cli_error(cli, CLI_ERROR, "`secret_key_tropic_masking()` failed.");
    goto cleanup;
  }

  uint8_t output[sizeof(fido_masking_key) + NOISE_TAG_SIZE] = {0};
  if (!secure_channel_encrypt(fido_masking_key, sizeof(fido_masking_key), NULL,
                              0, output)) {
    // TODO: Consider distinguishing between cryptography error and state error
    cli_error(cli, CLI_ERROR,
              "`secure_channel_encrypt()` failed. You have to call "
              "`secure-channel-handshake-2` first.");
    goto cleanup;
  }

  cli_ok_hexdata(cli, output, sizeof(output));

cleanup:
  memzero(fido_masking_key, sizeof(fido_masking_key));
}

static void prodtest_tropic_handshake(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t input[35] = {0};
  size_t input_length = 0;
  if (!cli_arg_hex(cli, "hex-data", input, sizeof(input), &input_length)) {
    if (input_length == sizeof(input)) {
      cli_error(cli, CLI_ERROR, "Input too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }
  if (input_length != sizeof(input)) {
    cli_error(cli, CLI_ERROR, "Unexpected input length. Expecting %d bytes.",
              (int)sizeof(input));
    return;
  }

  // TODO: Implement properly

  systick_delay_ms(150);

  uint8_t output[51] = {0};

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_1;

  cli_ok_hexdata(cli, output, sizeof(output));
}

static void prodtest_tropic_send_command(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t input[60] = {0};
  size_t input_length = 0;
  if (!cli_arg_hex(cli, "hex-data", input, sizeof(input), &input_length)) {
    if (input_length == sizeof(input)) {
      cli_error(cli, CLI_ERROR, "Input too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }

  if (tropic_handshake_state != TROPIC_HANDSHAKE_STATE_1) {
    cli_error(cli, CLI_ERROR, "You have to call `tropic-handshake` first.");
    return;
  }

  // TODO: Implement properly

  systick_delay_ms(90);

  uint8_t output[60] = {0};

  cli_ok_hexdata(cli, output, sizeof(output));
}

static void prodtest_tropic_lock(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  // TODO: Implement properly

  systick_delay_ms(500);

  locked = true;

  cli_ok(cli, "");
}

static void prodtest_tropic_certdev_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  // TODO: Implement properly

  systick_delay_ms(35);

  uint8_t output[600] = {0};

  cli_ok_hexdata(cli, &output, sizeof(output));
}

static void prodtest_tropic_certdev_write(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  uint8_t input[600] = {0};
  size_t input_length = 0;
  if (!cli_arg_hex(cli, "hex-data", input, sizeof(input), &input_length)) {
    if (input_length == sizeof(input)) {
      cli_error(cli, CLI_ERROR, "Certificate too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }

  // TODO: Implement properly

  systick_delay_ms(80);

  cli_ok(cli, "");
}

static void prodtest_tropic_certfido_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  // TODO: Implement properly

  systick_delay_ms(35);

  uint8_t output[600] = {0};

  cli_ok_hexdata(cli, &output, sizeof(output));
}

static void prodtest_tropic_certfido_write(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  uint8_t input[600] = {0};
  size_t input_length = 0;
  if (!cli_arg_hex(cli, "hex-data", input, sizeof(input), &input_length)) {
    if (input_length == sizeof(input)) {
      cli_error(cli, CLI_ERROR, "Certificate too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }

  // TODO: Implement properly

  systick_delay_ms(80);

  cli_ok(cli, "");
}

// clang-format off

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
  .info = "Check whether Tropic is locked",
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
  .name = "tropic-lock",
  .func = prodtest_tropic_lock,
  .info = "Lock Tropic",
  .args = ""
);

#endif
