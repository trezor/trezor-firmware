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

#include <sec/secret.h>
#include "ed25519-donna/ed25519.h"
#include "libtropic.h"
#include "lt_l2.h"

#define FACTORY_PAIRING_KEY_SLOT PAIRING_KEY_SLOT_INDEX_0
#define HSM_PAIRING_KEY_SLOT PAIRING_KEY_SLOT_INDEX_1
#define MCU_PAIRING_KEY_SLOT PAIRING_KEY_SLOT_INDEX_2

static bool hsm_handshake_done = false;  // TODO: Add comment

static lt_ret_t pair(cli_t* cli, pkey_index_t slot) {
  curve25519_key private_key = {0};
  // TODO: Use different functions for different slots
  if (!secret_tropic_get_trezor_privkey(private_key)) {
    cli_error(cli, CLI_ERROR, "Unable to get factory private key");
    return LT_FAIL;
  }
  curve25519_key public_key = {0};
  curve25519_scalarmult_basepoint(public_key, private_key);

  lt_handle_t* h = &g_tropic_driver.handle;  // TODO: Maybe remove

  lt_ret_t ret = lt_session_start(h, public_key, slot, private_key, public_key);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "lt_session_start for slot %d failed with error %d", slot, ret);
    return ret;
  }

  hsm_handshake_done = false;

  return LT_OK;
}

static void prodtest_tropic_get_riscv_fw_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t version[TROPIC_RISCV_FW_SIZE];
  if (!tropic_get_riscv_fw_version(version, sizeof(version))) {
    cli_error(cli, CLI_ERROR, "Unable to get RISCV FW version");
  }

  // Respond with an OK message and version
  cli_ok_hexdata(cli, &version, sizeof(version));
}

static void prodtest_tropic_get_spect_fw_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t version[TROPIC_SPECT_FW_SIZE];
  if (!tropic_get_spect_fw_version(version, sizeof(version))) {
    cli_error(cli, CLI_ERROR, "Unable to get SPECT FW version");
  }

  // Respond with an OK message and version
  cli_ok_hexdata(cli, &version, sizeof(version));
}

static void prodtest_tropic_get_chip_id(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t chip_id[TROPIC_CHIP_ID_SIZE];
  if (!tropic_get_chip_id(chip_id, sizeof(chip_id))) {
    cli_error(cli, CLI_ERROR, "Unable to get CHIP ID");
  }

  // Respond with an OK message and chip ID
  cli_ok_hexdata(cli, &chip_id, sizeof(chip_id));
}

static void prodtest_tropic_certtropic_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_ret_t ret = LT_OK;

  struct lt_cert_store_t cert_store = {0};
  const size_t max_cert_size = 1000;
  uint8_t cert_buffer[max_cert_size * LT_NUM_CERTIFICATES];

  for (int i = 0; i < LT_NUM_CERTIFICATES; i++) {
    cert_store.certs[i] = cert_buffer + (i * max_cert_size);
    cert_store.buf_len[i] = max_cert_size;
    cert_store.cert_len[i] = 0;
  }

  ret = lt_get_info_cert_store(&g_tropic_driver.handle, &cert_store);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "lt_get_info_cert_store failed with error %d.", ret);
  }

  size_t total_size = 0;
  for (int i = 0; i < LT_NUM_CERTIFICATES; i++) {
    total_size += cert_store.cert_len[i];
  }

  cli_ok_hexdata(cli, cert_buffer, total_size);
}

static lt_ret_t lt_l2_get_rsp_len(uint8_t* buffer, size_t buffer_length,
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

static lt_ret_t lt_l2_get_req_len(uint8_t* buffer, size_t buffer_length,
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

static void prodtest_trezor_handshake(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  size_t input_length = 0;
  uint8_t buffer[35] = {
      0};  // This value was chosen to fit the handshake request
  if (!cli_arg_hex(cli, "hex-data", buffer, sizeof(buffer), &input_length)) {
    if (input_length == sizeof(buffer)) {
      cli_error(cli, CLI_ERROR, "Data too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }

  lt_handle_t* h = &g_tropic_driver.handle;  // TODO: Maybe remove

  lt_ret_t ret = LT_OK;

  size_t request_length = 0;
  ret = lt_l2_get_req_len(buffer, sizeof(buffer), &request_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "lt_l2_get_req_len failed with error %d.", ret);
    return;
  }

  if (input_length != request_length) {
    cli_error(cli, CLI_ERROR, "Request was damaged or truncated.");
    return;
  }

  memcpy(h->l2.buff, buffer, request_length);

  ret = lt_l2_send(&h->l2);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "lt_l2_send failed with error %d.", ret);
    return;
  }

  ret = lt_l2_receive(&h->l2);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "lt_l2_receive failed with error %d.", ret);
    return;
  }

  size_t response_length = 0;
  ret = lt_l2_get_rsp_len(h->l2.buff, sizeof(h->l2.buff), &response_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "lt_l2_get_rsp_len failed with error %d.", ret);
    return;
  }

  cli_ok_hexdata(cli, h->l2.buff, response_length);

  hsm_handshake_done = true;
}

static void prodtest_tropic_send_command(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  size_t input_length = 0;
  uint8_t buffer[98];  // This value was chosen to fit ecc key store, generate,
                       // erase and read commands and results
  if (!cli_arg_hex(cli, "hex-data", buffer, sizeof(buffer), &input_length)) {
    if (input_length == sizeof(buffer)) {
      cli_error(cli, CLI_ERROR, "Data too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }

  lt_handle_t* h = &g_tropic_driver.handle;  // TODO: Maybe remove
  lt_ret_t ret = LT_OK;

  if (!hsm_handshake_done) {
    cli_error(cli, CLI_ERROR,
              "Call `tropic-handshake` first to establish a session.");
    return;
  }

  // TODO: Check already paired
  size_t command_length = 0;
  ret = l3_get_frame_len(buffer, sizeof(buffer), &command_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "l3_get_cmd_len failed with error %d.", ret);
    return;
  }

  if (input_length != command_length) {
    cli_error(cli, CLI_ERROR, "Request was damaged or truncated.");
    return;
  }

  ret = lt_l2_send_encrypted_cmd(&h->l2, (uint8_t*)buffer, input_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "lt_l2_send_encrypted_cmd failed with error %d.",
              ret);
    return;
  }

  ret = lt_l2_recv_encrypted_res(&h->l2, buffer, sizeof(buffer));
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "lt_l2_recv_encrypted_res failed with error %d.",
              ret);
    return;
  }

  size_t result_length = 0;
  ret = l3_get_frame_len(buffer, sizeof(buffer), &result_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "l3_get_cmd_len failed with error %d.", ret);
    return;
  }

  cli_ok_hexdata(cli, buffer, result_length);
}

static lt_ret_t write_pairing_key(lt_handle_t* h, pkey_index_t slot,
                                  const ed25519_secret_key private_key) {
  ed25519_public_key public_key = {0};
  curve25519_scalarmult_basepoint(public_key, private_key);

  lt_ret_t ret = lt_pairing_key_write(h, public_key, slot);
  ed25519_public_key public_key_read = {0};
  if (ret != LT_OK && ret != LT_L3_FAIL) {
    return ret;
  }
  // If the pairing has already been written, `lt_pairing_key_write` returns
  // LT_L3_FAIL.
  ret = lt_pairing_key_read(h, public_key_read, slot);
  if (ret != LT_OK) {
    return ret;
  }
  if (memcmp(public_key, public_key_read, sizeof(ed25519_public_key)) != 0) {
    return LT_FAIL;
  }

  return LT_OK;
}

static void prodtest_tropic_pair(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_ret_t ret = LT_OK;
  lt_handle_t* h = &g_tropic_driver.handle;  // TODO: Maybe remove;

  uint8_t tropic_public[32] = {0};
  if (!secret_tropic_get_tropic_pubkey(tropic_public)) {
    cli_error(cli, CLI_ERROR, "Unable to get Tropic public key");
    return;
  }

  uint8_t factory_private[32] = {0};
  uint8_t factory_public[32] = {0};
  if (!secret_tropic_get_trezor_privkey(factory_private)) {
    cli_error(cli, CLI_ERROR, "Unable to get factory private key");
    return;
  }
  // factory_private[0] = 123; // TODO: Remove this line
  curve25519_scalarmult_basepoint(factory_public, factory_private);

  uint8_t mcu_private[32] = {0};
  if (!secret_tropic_get_trezor_privkey(mcu_private)) {
    cli_error(cli, CLI_ERROR, "Unable to get MCU private key");
    return;
  }

  uint8_t hsm_private[32] = {0};
  if (!secret_tropic_get_trezor_privkey(hsm_private)) {
    cli_error(cli, CLI_ERROR, "Unable to get HSM private key");
    return;
  }

  ret = lt_session_start(h, tropic_public, FACTORY_PAIRING_KEY_SLOT,
                         factory_private, factory_public);
  if (ret == LT_L2_HSK_ERR) {
    // If `lt_session_start` returns LT_L2_HSK_ERR, it means that the key is
    // either invalidated or blank. Since the first slot shoud never be blank,
    // it means that the key has been invalidated.
    // https://github.com/tropicsquare/ts-tvl/blob/40e6d24f92144d3b0f4981f76fa7adf735d2da01/tvl/targets/model/tropic01_l2_api_impl.py#L87

    // If the factory key has been invalidated, it is likely that
    // `prodtest_tropic_pair` has already been called. In this case, the MCU
    // pairing key has already been written, so we can initiate the session with
    // the MCU key.
    ret = lt_session_start(h, tropic_public, MCU_PAIRING_KEY_SLOT, mcu_private,
                           factory_public);
    if (ret != LT_OK) {
      cli_error(cli, CLI_ERROR,
                "The factory key has already been invalidated and "
                "lt_seesion_start for "
                "MCU key failed with error %d",
                ret);
      return;
    }
  } else if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "lt_session_start for factory key failed with error %d", ret);
    return;
  }

  ret = write_pairing_key(h, MCU_PAIRING_KEY_SLOT, mcu_private);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "lt_pairing_key_write failed for MCU key with error %d", ret);
    return;
  }

  ret = write_pairing_key(h, HSM_PAIRING_KEY_SLOT, hsm_private);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "lt_pairing_key_write failed for HSM key with error %d", ret);
    return;
  }

  ret = lt_pairing_key_invalidate(h, FACTORY_PAIRING_KEY_SLOT);
  // If the factory has already been invalidated, `lt_pairing_key_invalidate`
  // returns LT_OK.
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "lt_pairing_key_invalidate failed for HSM key with error %d",
              ret);
    return;
  }

  cli_ok(cli, "");
}

static lt_ret_t write_data(lt_handle_t* h, uint16_t first_slot,
                           uint16_t slots_count, uint8_t* data,
                           size_t data_length) {
  const uint16_t last_data_slot = first_slot + slots_count - 1;
  if (slots_count == 0 || last_data_slot > R_MEM_DATA_SLOT_MACANDD) {
    return LT_PARAM_ERR;
  }

  const size_t prefix_length = 2;
  const size_t prefixed_data_length = data_length + prefix_length;
  const size_t total_slots_length = R_MEM_DATA_SIZE_MAX * slots_count;
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
    lt_ret_t ret = LT_OK;

    ret = lt_r_mem_data_erase(h, slot);
    if (ret != LT_OK) {
      return ret;
    }

    ret = lt_r_mem_data_write(h, slot, prefixed_data + position,
                              R_MEM_DATA_SIZE_MAX);
    if (ret != LT_OK) {
      return ret;
    }

    position += R_MEM_DATA_SIZE_MAX;
    slot += 1;
  }

  return LT_OK;
}

static lt_ret_t read_data(lt_handle_t* h, uint16_t first_slot,
                          uint16_t slots_count, uint8_t* data,
                          size_t max_data_length, size_t* data_length) {
  const uint16_t last_data_slot = first_slot + slots_count - 1;
  if (slots_count == 0 || last_data_slot > R_MEM_DATA_SLOT_MACANDD) {
    return LT_PARAM_ERR;
  }

  // The following code can be further optimized:
  //   * It uses unnecessary amount of memory.
  //   * It reads from a data slot even if there is no data to be read.

  const size_t total_slots_length = R_MEM_DATA_SIZE_MAX * slots_count;
  uint8_t prefixed_data[total_slots_length];
  size_t position = 0;
  uint16_t slot = first_slot;

  while (slot <= last_data_slot) {
    lt_ret_t ret = lt_r_mem_data_read(h, slot, prefixed_data + position,
                                      R_MEM_DATA_SIZE_MAX);
    if (ret != LT_OK) {
      return ret;
    }

    position += R_MEM_DATA_SIZE_MAX;
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

static void cert_write(cli_t* cli, uint16_t first_slot, uint16_t slots_count) {
  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  size_t len = 0;
  uint8_t data_bytes[1000];  // TODO

  if (!cli_arg_hex(cli, "hex-data", data_bytes, sizeof(data_bytes), &len)) {
    if (len == sizeof(data_bytes)) {
      cli_error(cli, CLI_ERROR, "Certificate too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }

  lt_handle_t* h = &g_tropic_driver.handle;

  lt_ret_t ret = LT_OK;
  ;
  ret = pair(cli, HSM_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "Unable to pair using the HSM key. tropic-pair has to be called "
              "first.");
    return;
  }

  ret = write_data(h, first_slot, slots_count, data_bytes, len);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "Unable to write certificate");
    return;
  }

  uint8_t cert_data[1000];
  size_t cert_data_length = 0;
  lt_ret_t read_ret = read_data(h, first_slot, slots_count, cert_data,
                                sizeof(cert_data), &cert_data_length);
  if (read_ret != LT_OK || cert_data_length != len ||
      memcmp(data_bytes, cert_data, len) != 0) {
    cli_error(cli, CLI_ERROR, "Unable to read certificate");
    return;
  }

  // TODO: Verify key

  cli_ok(cli, "");
}

static void read_cert(cli_t* cli, uint16_t first_slot, uint16_t slots_count) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_handle_t* h = &g_tropic_driver.handle;

  uint8_t cert_data[1000];  // TODO
  size_t cert_data_length = 0;
  lt_ret_t ret = read_data(h, first_slot, slots_count, cert_data,
                           sizeof(cert_data), &cert_data_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "Unable to read certificate");
    return;
  }

  cli_ok_hexdata(cli, cert_data, cert_data_length);
}

#define FIDO_CERT_FIRST_SLOT 0
#define FIDO_CERT_SLOTS_COUNT 3
#define TROPIC_CERT_FIRST_SLOT 3
#define TROPIC_CERT_SLOTS_COUNT 3

void prodtest_tropic_certfido_write(cli_t* cli) {
  cert_write(cli, FIDO_CERT_FIRST_SLOT, FIDO_CERT_SLOTS_COUNT);
}

void prodtest_tropic_certdev_write(cli_t* cli) {
  cert_write(cli, TROPIC_CERT_FIRST_SLOT, TROPIC_CERT_SLOTS_COUNT);
}

void prodtest_tropic_certfido_read(cli_t* cli) {
  read_cert(cli, FIDO_CERT_FIRST_SLOT, FIDO_CERT_SLOTS_COUNT);
}

void prodtest_tropic_certdev_read(cli_t* cli) {
  read_cert(cli, TROPIC_CERT_FIRST_SLOT, TROPIC_CERT_SLOTS_COUNT);
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
  .name = "tropic-send-command",
  .func = prodtest_tropic_send_command,
  .info = "",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "tropic-certtropic-read",
  .func = prodtest_tropic_certtropic_read,
  .info = "Read the X.509 certificate issued by Tropic",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-certdev-read",
  .func = prodtest_tropic_certdev_read,
  .info = "Read the device's X.509 certificate",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-certdev-write",
  .func = prodtest_tropic_certdev_write,
  .info = "Write the device's X.509 certificate",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "tropic-certfido-read",
  .func = prodtest_tropic_certfido_read,
  .info = "Read the X.509 certificate for the FIDO key",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-certfido-write",
  .func = prodtest_tropic_certfido_write,
  .info = "Write the X.509 certificate for the FIDO key",
  .args = "<hex-data>"
);

PRODTEST_CLI_CMD(
  .name = "tropic-pair",
  .func = prodtest_tropic_pair,
  .info = "Pair with Tropic",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-handshake",
  .func = prodtest_trezor_handshake,
  .info = "Send a handshake command to Tropic",
  .args = "<hex-data>"
);

#endif
