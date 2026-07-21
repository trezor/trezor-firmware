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

#include <trezor_rtl.h>
#include <trezor_types.h>

#include <sec/rng_strong.h>
#include <sec/secret_keys.h>
#include <sec/tropic.h>
#include <sys/systick.h>

#include "bignum.h"
#include "hmac.h"

#include <libtropic.h>
#include <libtropic/cal/trezor_crypto/libtropic_trezor_crypto.h>

#ifdef TREZOR_EMULATOR
#include <arpa/inet.h>
#include <libtropic/hal/posix/tcp/libtropic_port_posix_tcp.h>
#include <time.h>
#endif  // TREZOR_EMULATOR

#include "ed25519-donna/ed25519.h"
#include "memzero.h"

#ifdef SECURE_MODE

// KEK masks used in PIN verification
#define TROPIC_KEK_MASKS_PRIVILEGED_SLOT 128
#define TROPIC_KEK_MASKS_UNPRIVILEGED_SLOT 256

// The value by which the index of the first mac-and-destroy slot is shifted
// before every PIN change. The value is coprime to
// TROPIC_MAC_AND_DESTROY_SLOT_COUNT to ensure that
// `get_mac_and_destroy_slot(i, change_pin_counter)` achieves the maximum
// possible period in `change_pin_counter`.
#define TROPIC_MAC_AND_DESTROY_SHIFT 11

// The slot that stores the number of times the PIN has been changed.
// Since the counter can only be decremented, its acutal value is
// TROPIC_CHANGE_COUNTER_SLOT_MAX_VALUE minus the number of PIN changes. This
// slot is used both for both privileged and the unprivileged sessions.
#define TROPIC_CHANGE_COUNTER_SLOT TR01_MCOUNTER_INDEX_4
#define TROPIC_CHANGE_COUNTER_SLOT_MAX_VALUE 0xfffffffe

static const uint8_t TROPIC_BATCHES_V1[][LT_MEMBER_SIZE(
    lt_chip_id_t, batch_id)] = {{0x19, 0x07, 0x11, 0x11, 0x07},
                                {0x19, 0x07, 0x1f, 0x0a, 0x04},
                                {0x19, 0x08, 0x0b, 0x10, 0x09},
                                {0x19, 0x04, 0x09, 0x0c, 0x07}};
// {0x19, 0x08, 0x13, 0x09, 0x2c},
// {0x19, 0x09, 0x10, 0x0b, 0x04}, {0x19, 0x0a, 0x08, 0x10, 0x10},
// {0x19, 0x0a, 0x1f, 0x0f, 0x2c}, {0x19, 0x0c, 0x03, 0x0d, 0x38},
// };

// clang-format off
// Temporary address table for config objects, ordered to match lt_config_t.obj[].
// Using a local const table instead of `cfg_desc_table` from libtropic because including
// that breaks the build due to RAM overflow.
// Will get removed once the libtropic table is made const.
// https://github.com/trezor/trezor-firmware/pull/6816#discussion_r3248307252
static const enum lt_config_obj_addr_t TROPIC_CONFIG_ADDRS[LT_CONFIG_OBJ_CNT] = {
    TR01_CFG_START_UP_ADDR,
    TR01_CFG_SENSORS_ADDR,
    TR01_CFG_DEBUG_ADDR,
    TR01_CFG_GPO_ADDR,
    TR01_CFG_SLEEP_MODE_ADDR,
    TR01_CFG_UAP_PAIRING_KEY_WRITE_ADDR,
    TR01_CFG_UAP_PAIRING_KEY_READ_ADDR,
    TR01_CFG_UAP_PAIRING_KEY_INVALIDATE_ADDR,
    TR01_CFG_UAP_R_CONFIG_WRITE_ERASE_ADDR,
    TR01_CFG_UAP_R_CONFIG_READ_ADDR,
    TR01_CFG_UAP_I_CONFIG_WRITE_ADDR,
    TR01_CFG_UAP_I_CONFIG_READ_ADDR,
    TR01_CFG_UAP_PING_ADDR,
    TR01_CFG_UAP_R_MEM_DATA_WRITE_ADDR,
    TR01_CFG_UAP_R_MEM_DATA_READ_ADDR,
    TR01_CFG_UAP_R_MEM_DATA_ERASE_ADDR,
    TR01_CFG_UAP_RANDOM_VALUE_GET_ADDR,
    TR01_CFG_UAP_ECC_KEY_GENERATE_ADDR,
    TR01_CFG_UAP_ECC_KEY_STORE_ADDR,
    TR01_CFG_UAP_ECC_KEY_READ_ADDR,
    TR01_CFG_UAP_ECC_KEY_ERASE_ADDR,
    TR01_CFG_UAP_ECDSA_SIGN_ADDR,
    TR01_CFG_UAP_EDDSA_SIGN_ADDR,
    TR01_CFG_UAP_MCOUNTER_INIT_ADDR,
    TR01_CFG_UAP_MCOUNTER_GET_ADDR,
    TR01_CFG_UAP_MCOUNTER_UPDATE_ADDR,
    TR01_CFG_UAP_MAC_AND_DESTROY_ADDR,
};
// clang-format on

typedef struct {
  bool has_value;
  uint32_t value;
} optional_u32_t;

typedef enum {
  TROPIC_R_CONFIG_WRITE_IF_TOO_LOOSE,
  TROPIC_R_CONFIG_WRITE_ALWAYS,
} tropic_r_config_write_mode_t;

typedef enum {
  TROPIC_CONFIG_STRICTNESS_INVALID,
  TROPIC_CONFIG_STRICTNESS_EQUAL,
  TROPIC_CONFIG_STRICTNESS_FIRST_STRICTER,
  TROPIC_CONFIG_STRICTNESS_SECOND_STRICTER,
  TROPIC_CONFIG_STRICTNESS_INCOMPARABLE,
} tropic_config_strictness_t;

#ifdef TREZOR_EMULATOR
#define TROPIC_RETRY_COMMAND(command) command
#else
#define TROPIC_MAX_RETRIES 10

bool tropic_session_start(void);

static bool is_retryable(lt_ret_t ret) {
  return ret == LT_L1_CHIP_ALARM_MODE || ret == LT_HAL_ERROR ||
         ret == LT_L2_IN_CRC_ERR || ret == LT_L2_CRC_ERR;
}

// Statement expression, see
// https://gcc.gnu.org/onlinedocs/gcc/Statement-Exprs.html
#define TROPIC_RETRY_COMMAND(command)                                     \
  ({                                                                      \
    bool TROPIC_RETRY_COMMAND_session_started =                           \
        g_tropic_driver.session_started;                                  \
    lt_pkey_index_t TROPIC_RETRY_COMMAND_pairing_key_index =              \
        g_tropic_driver.pairing_key_index;                                \
    lt_ret_t TROPIC_RETRY_COMMAND_res = command;                          \
    for (int TROPIC_RETRY_COMMAND_i = 0;                                  \
         TROPIC_RETRY_COMMAND_i < TROPIC_MAX_RETRIES - 1;                 \
         TROPIC_RETRY_COMMAND_i++) {                                      \
      if (!is_retryable(TROPIC_RETRY_COMMAND_res)) {                      \
        break;                                                            \
      }                                                                   \
      tropic_deinit();                                                    \
      tropic_init(NULL);                                                  \
      if (TROPIC_RETRY_COMMAND_session_started) {                         \
        if (tropic_custom_session_start(                                  \
                NULL, TROPIC_RETRY_COMMAND_pairing_key_index) != LT_OK) { \
          continue;                                                       \
        }                                                                 \
      }                                                                   \
      TROPIC_RETRY_COMMAND_res = command;                                 \
    }                                                                     \
    TROPIC_RETRY_COMMAND_res;                                             \
  })
#endif  // TREZOR_EMULATOR

typedef struct {
  bool initialized;
  bool session_started;
  lt_pkey_index_t pairing_key_index;  // This field is valid only if
                                      // session_started is true.
  lt_handle_t handle;
  lt_ctx_trezor_crypto_t crypto_ctx;
#ifdef TREZOR_EMULATOR
  lt_dev_posix_tcp_t device;
#endif
} tropic_driver_t;

static tropic_driver_t g_tropic_driver = {0};

#if !PRODUCTION || defined(TREZOR_PRODTEST)
static uint8_t tropic_cert_chain[LT_NUM_CERTIFICATES *
                                 TR01_L2_GET_INFO_REQ_CERT_SIZE_SINGLE] = {0};
static size_t tropic_cert_chain_length = 0;
static curve25519_key tropic_public_cached = {0};

// If `TREZOR_PRODTEST` is not defined, the `cli` argument is ignored.
static bool cache_tropic_cert_chain(cli_t *cli, lt_handle_t *tropic_handle) {
  if (tropic_cert_chain_length > 0) {
    return true;
  }

  lt_cert_store_t cert_store = {0};
  for (size_t i = 0; i < LT_NUM_CERTIFICATES; i++) {
    cert_store.certs[i] =
        &tropic_cert_chain[i * TR01_L2_GET_INFO_REQ_CERT_SIZE_SINGLE];
    cert_store.buf_len[i] = TR01_L2_GET_INFO_REQ_CERT_SIZE_SINGLE;
  }

  lt_ret_t ret = lt_get_info_cert_store(tropic_handle, &cert_store);
  if (ret != LT_OK) {
#if TREZOR_PRODTEST
    if (cli) {
      cli_trace(cli, "lt_get_info_cert_store() failed with error '%s'",
                lt_ret_verbose(ret));
    }
#endif
    return false;
  }

  ret = lt_get_st_pub(&cert_store, tropic_public_cached);
  if (ret != LT_OK) {
#if TREZOR_PRODTEST
    if (cli) {
      cli_trace(cli, "lt_get_st_pub() failed with error '%s'",
                lt_ret_verbose(ret));
    }
#endif
    return false;
  }

  // Compactify tropic_cert_chain for future use. This invalidates the
  // cert_store.
  size_t length = 0;
  for (size_t i = 0; i < LT_NUM_CERTIFICATES; i++) {
    memmove(&tropic_cert_chain[length], cert_store.certs[i],
            cert_store.cert_len[i]);
    length += cert_store.cert_len[i];
  }

  tropic_cert_chain_length = length;

  return true;
}

bool tropic_get_pubkey(cli_t *cli, lt_handle_t *tropic_handle,
                       curve25519_key pubkey) {
  if (!cache_tropic_cert_chain(cli, tropic_handle)) {
    return false;
  }
  memcpy(pubkey, tropic_public_cached, sizeof(curve25519_key));
  return true;
}

bool tropic_get_cert_chain_ptr(cli_t *cli, lt_handle_t *tropic_handle,
                               uint8_t const **cert_chain,
                               size_t *cert_chain_length) {
  if (!cache_tropic_cert_chain(cli, tropic_handle)) {
    return false;
  }
  *cert_chain = tropic_cert_chain;
  *cert_chain_length = tropic_cert_chain_length;
  return true;
}

#endif  // !PRODUCTION || defined(TREZOR_PRODTEST)

lt_ret_t tropic_session_invalidate(void) {
  lt_ret_t ret = lt_session_abort(&g_tropic_driver.handle);
  if (ret != LT_OK) {
    return ret;
  }
  g_tropic_driver.session_started = false;
  return LT_OK;
}

// If `TREZOR_PRODTEST` is not defined, the `cli` argument is ignored.
lt_ret_t tropic_custom_session_start(cli_t *cli,
                                     lt_pkey_index_t pairing_key_index) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return LT_FAIL;
  }

  if (drv->session_started && drv->pairing_key_index == pairing_key_index) {
    return LT_OK;
  }

  lt_ret_t ret = LT_FAIL;

  curve25519_key trezor_private = {0};
  switch (pairing_key_index) {
    case TROPIC_FACTORY_PAIRING_KEY_SLOT:
      tropic_get_factory_privkey(trezor_private);
      break;
    case TROPIC_PRIVILEGED_PAIRING_KEY_SLOT:
      if (secret_key_tropic_pairing_privileged(trezor_private) != sectrue) {
#ifdef TREZOR_PRODTEST
        if (cli) {
          cli_trace(cli, "`secret_key_tropic_pairing_privileged()` failed");
        }
#endif
        goto cleanup;
      }
      break;
    case TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT:
      if (secret_key_tropic_pairing_unprivileged(trezor_private) != sectrue) {
#ifdef TREZOR_PRODTEST
        if (cli) {
          cli_trace(cli, "`secret_key_tropic_pairing_unprivileged()` failed");
        }
#endif
        goto cleanup;
      }
      break;
    default:
      goto cleanup;
  }

  curve25519_key trezor_public = {0};
  curve25519_scalarmult_basepoint(trezor_public, trezor_private);

  curve25519_key tropic_public = {0};
  if (secret_key_tropic_public(tropic_public) != sectrue) {
#if !PRODUCTION || defined(TREZOR_PRODTEST)
    if (pairing_key_index != TROPIC_FACTORY_PAIRING_KEY_SLOT ||
        !tropic_get_pubkey(cli, &drv->handle, tropic_public))
#endif
    {
#ifdef TREZOR_PRODTEST
      if (cli) {
        cli_trace(
            cli,
            "`secret_key_tropic_public()` or `tropic_get_pubkey()` failed");
      }
#endif
      goto cleanup;
    }
  }

  ret = TROPIC_RETRY_COMMAND(lt_session_start(&drv->handle, tropic_public,
                                              pairing_key_index, trezor_private,
                                              trezor_public));
#if TREZOR_PRODTEST
  if (ret != LT_OK && cli) {
    cli_trace(cli,
              "`lt_session_start()` failed for pairing key %d "
              "with error '%s'",
              pairing_key_index, lt_ret_verbose(ret));
  }
#endif

  drv->session_started = (ret == LT_OK);
  drv->pairing_key_index = pairing_key_index;

cleanup:
  memzero(trezor_private, sizeof(trezor_private));

  return ret;
}

bool tropic_session_start(void) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return false;
  }

  if (drv->session_started) {
    return true;
  }

  if (tropic_custom_session_start(NULL, TROPIC_PRIVILEGED_PAIRING_KEY_SLOT) ==
      LT_OK) {
    return true;
  }
#ifndef TREZOR_EMULATOR
  if (tropic_custom_session_start(NULL, TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT) ==
      LT_OK) {
    return true;
  }
#endif
#if !PRODUCTION
  if (tropic_custom_session_start(NULL, TROPIC_FACTORY_PAIRING_KEY_SLOT) ==
      LT_OK) {
    return true;
  }
#endif

  return false;
}

void tropic_session_start_time(uint32_t *time_ms) {
  if (!g_tropic_driver.session_started) {
    *time_ms += 204;
  }
}

lt_ret_t lt_ecc_key_erase_retry(lt_handle_t *tropic_handle,
                                const lt_ecc_slot_t ecc_slot) {
  return TROPIC_RETRY_COMMAND(lt_ecc_key_erase(tropic_handle, ecc_slot));
}

static lt_ret_t lt_r_mem_data_write_retry(lt_handle_t *tropic_handle,
                                          const uint16_t udata_slot,
                                          const uint8_t *data,
                                          const uint16_t size) {
  return TROPIC_RETRY_COMMAND(
      lt_r_mem_data_write(tropic_handle, udata_slot, data, size));
}

lt_ret_t lt_r_mem_data_erase_retry(lt_handle_t *tropic_handle,
                                   const uint16_t udata_slot) {
  return TROPIC_RETRY_COMMAND(lt_r_mem_data_erase(tropic_handle, udata_slot));
}

static lt_ret_t lt_r_mem_data_erase_write(lt_handle_t *h,
                                          const uint16_t udata_slot,
                                          const uint8_t *data,
                                          const uint16_t size) {
  lt_ret_t ret = lt_r_mem_data_erase(h, udata_slot);
  if (ret != LT_OK) {
    return ret;
  }

  return lt_r_mem_data_write(h, udata_slot, data, size);
}

lt_ret_t lt_mac_and_destroy_retry(lt_handle_t *tropic_handle,
                                  const lt_mac_and_destroy_slot_t slot,
                                  const uint8_t *data_out, uint8_t *data_in) {
  return TROPIC_RETRY_COMMAND(
      lt_mac_and_destroy(tropic_handle, slot, data_out, data_in));
}

lt_ret_t lt_read_whole_R_config_retry(lt_handle_t *tropic_handle,
                                      lt_config_t *config) {
  if (tropic_handle == NULL || config == NULL) {
    return LT_PARAM_ERR;
  }

  // We cannot simply use lt_read_whole_R_config() because it pulls the
  // cfg_desc_table and causes RAM overflow.
  // TODO: once the cfg_desc_table is made const and can be pulled without RAM
  // overflow, switch to using lt_read_whole_R_config() instead of this
  // implementation.
  for (size_t i = 0; i < LT_CONFIG_OBJ_CNT; i++) {
    lt_ret_t ret = TROPIC_RETRY_COMMAND(lt_r_config_read(
        tropic_handle, TROPIC_CONFIG_ADDRS[i], &config->obj[i]));
    if (ret != LT_OK) {
      return ret;
    }
  }

  return LT_OK;
}

lt_ret_t lt_read_whole_I_config_retry(lt_handle_t *tropic_handle,
                                      lt_config_t *config) {
  if (tropic_handle == NULL || config == NULL) {
    return LT_PARAM_ERR;
  }

  // We cannot simply use lt_read_whole_I_config() yet because it pulls the
  // cfg_desc_table and causes RAM overflow.
  // TODO: Keep this wrapper symmetric with lt_read_whole_R_config_retry()
  // so the implementation can be switched once libtropic provides a const
  // descriptor table.
  for (size_t i = 0; i < LT_CONFIG_OBJ_CNT; i++) {
    lt_ret_t ret = TROPIC_RETRY_COMMAND(lt_i_config_read(
        tropic_handle, TROPIC_CONFIG_ADDRS[i], &config->obj[i]));
    if (ret != LT_OK) {
      return ret;
    }
  }

  return LT_OK;
}

static lt_ret_t lt_erase_and_write_R_config(lt_handle_t *tropic_handle,
                                            const lt_config_t *config) {
  lt_ret_t ret = lt_r_config_erase(tropic_handle);
  if (ret != LT_OK) {
    return ret;
  }

  for (size_t i = 0; i < LT_CONFIG_OBJ_CNT; i++) {
    ret = TROPIC_RETRY_COMMAND(lt_r_config_write(
        tropic_handle, TROPIC_CONFIG_ADDRS[i], config->obj[i]));
    if (ret != LT_OK) {
      uint32_t obj = 0;
      lt_ret_t inside_ret = TROPIC_RETRY_COMMAND(
          lt_r_config_read(tropic_handle, TROPIC_CONFIG_ADDRS[i], &obj));
      if (inside_ret != LT_OK) {
        return inside_ret;
      }
      if (memcmp(&obj, &config->obj[i], sizeof(uint32_t)) != 0) {
        return ret;
      }
    }
  }

  return LT_OK;
}

lt_ret_t lt_erase_and_write_R_config_retry(lt_handle_t *tropic_handle,
                                           const lt_config_t *config) {
  return TROPIC_RETRY_COMMAND(
      lt_erase_and_write_R_config(tropic_handle, config));
}

static lt_ret_t lt_r_mem_data_read_retry(lt_handle_t *h,
                                         const uint16_t udata_slot,
                                         uint8_t *data, const uint16_t size,
                                         uint16_t *size_out) {
  return TROPIC_RETRY_COMMAND(
      lt_r_mem_data_read(h, udata_slot, data, size, size_out));
}

static tropic_config_strictness_t compare_config_strictness(
    const lt_config_t *config_1, const lt_config_t *config_2) {
  if (config_1 == NULL || config_2 == NULL) {
    return TROPIC_CONFIG_STRICTNESS_INVALID;
  }

  bool first_is_stricter = false;
  bool second_is_stricter = false;
  for (size_t i = 0; i < LT_CONFIG_OBJ_CNT; i++) {
    uint32_t first_stricter_bits = ~config_1->obj[i] & config_2->obj[i];
    uint32_t second_stricter_bits = config_1->obj[i] & ~config_2->obj[i];

    if (first_stricter_bits != 0) {
      first_is_stricter = true;
    }
    if (second_stricter_bits != 0) {
      second_is_stricter = true;
    }
    if (first_is_stricter && second_is_stricter) {
      return TROPIC_CONFIG_STRICTNESS_INCOMPARABLE;
    }
  }

  if (first_is_stricter) {
    return TROPIC_CONFIG_STRICTNESS_FIRST_STRICTER;
  }
  if (second_is_stricter) {
    return TROPIC_CONFIG_STRICTNESS_SECOND_STRICTER;
  }
  return TROPIC_CONFIG_STRICTNESS_EQUAL;
}

static secbool tropic_ensure_i_config(const lt_config_t *expected_config) {
  tropic_driver_t *drv = &g_tropic_driver;

  lt_config_t current_config = {0};
  if (lt_read_whole_I_config_retry(&drv->handle, &current_config) != LT_OK) {
    return secfalse;
  }

  switch (compare_config_strictness(&current_config, expected_config)) {
    case TROPIC_CONFIG_STRICTNESS_EQUAL:
    case TROPIC_CONFIG_STRICTNESS_FIRST_STRICTER:
      return sectrue;
    case TROPIC_CONFIG_STRICTNESS_SECOND_STRICTER:
      break;
    case TROPIC_CONFIG_STRICTNESS_INVALID:
    case TROPIC_CONFIG_STRICTNESS_INCOMPARABLE:
    default:
      return secfalse;
  }

  for (size_t i = 0; i < LT_CONFIG_OBJ_CNT; i++) {
    uint32_t expected = expected_config->obj[i];
    uint32_t to_flip = (~expected & current_config.obj[i]);
    for (size_t j = 0; j < 32; j++) {  // Tropic cfg objects are 32-bit
      if (to_flip & BIT(j)) {
        if (TROPIC_RETRY_COMMAND(lt_i_config_write(
                &drv->handle, TROPIC_CONFIG_ADDRS[i], j)) != LT_OK) {
          return secfalse;
        }
      }
    }
  }

  if (lt_read_whole_I_config_retry(&drv->handle, &current_config) != LT_OK) {
    return secfalse;
  }
  if (memcmp(&current_config, expected_config, sizeof(current_config)) != 0) {
    return secfalse;
  }

  return sectrue;
}

static secbool tropic_ensure_r_config(const lt_config_t *expected_config) {
  tropic_driver_t *drv = &g_tropic_driver;

  lt_config_t current = {0};
  if (lt_read_whole_R_config_retry(&drv->handle, &current) != LT_OK) {
    return secfalse;
  }

  if (memcmp(&current, expected_config, sizeof(current)) == 0) {
    return sectrue;
  }

  if (lt_erase_and_write_R_config_retry(&drv->handle, expected_config) !=
      LT_OK) {
    return secfalse;
  }

  current = (lt_config_t){0};
  if (lt_read_whole_R_config_retry(&drv->handle, &current) != LT_OK) {
    return secfalse;
  }

  if (memcmp(&current, expected_config, sizeof(current)) != 0) {
    return secfalse;
  }

  return sectrue;
}

static bool tropic_find_config_distribution(
    uint32_t distribution_version,
    tropic_config_distribution_t *distribution_out) {
  if (distribution_out == NULL) {
    return false;
  }

  for (size_t i = 0; i < tropic_config_distribution_count; i++) {
    if (tropic_config_distributions[i].distribution_version ==
        distribution_version) {
      *distribution_out = tropic_config_distributions[i];
      return true;
    }
  }
  return false;
}

static bool tropic_get_config_from_versioned_configs(
    const tropic_versioned_config_t *configs, size_t config_count,
    uint32_t config_version, const lt_config_t **config_out) {
  if (config_out == NULL) {
    return false;
  }

  for (size_t i = 0; i < config_count; i++) {
    if (configs[i].version == config_version) {
      *config_out = &configs[i].config;
      return true;
    }
  }
  return false;
}

bool tropic_get_expected_tropic_config_from_distribution_version(
    uint32_t distribution_version, tropic_expected_config_t *config_out) {
  if (config_out == NULL) {
    return false;
  }

  tropic_config_distribution_t distribution = {0};
  if (!tropic_find_config_distribution(distribution_version, &distribution)) {
    return false;
  }
  config_out->distribution_version = distribution_version;

  if (!tropic_get_config_from_versioned_configs(
          tropic_irreversible_configs, tropic_irreversible_config_count,
          distribution.irreversible_version, &(config_out->i_config))) {
    return false;
  }
  if (!tropic_get_config_from_versioned_configs(
          tropic_reversible_configs, tropic_reversible_config_count,
          distribution.min_reversible_version, &(config_out->min_r_config))) {
    return false;
  }
  if (!tropic_get_config_from_versioned_configs(
          tropic_reversible_configs, tropic_reversible_config_count,
          distribution.max_reversible_version, &(config_out->max_r_config))) {
    return false;
  }

  return true;
}

static lt_ret_t lt_r_mem_data_erase_write_retry(lt_handle_t *h,
                                                const uint16_t udata_slot,
                                                const uint8_t *data,
                                                const uint16_t size) {
  return TROPIC_RETRY_COMMAND(
      lt_r_mem_data_erase_write(h, udata_slot, data, size));
}

static bool tropic_get_distribution_version(
    uint16_t slot, optional_u32_t *distribution_version_out) {
  uint8_t distribution_version_bytes[sizeof(uint32_t)] = {0};
  uint16_t data_read_size = 0;
  lt_ret_t ret = lt_r_mem_data_read_retry(
      &g_tropic_driver.handle, slot, distribution_version_bytes,
      sizeof(distribution_version_bytes), &data_read_size);
  if (ret == LT_L3_R_MEM_DATA_READ_SLOT_EMPTY) {
    distribution_version_out->has_value = false;
    return true;
  } else if (ret != LT_OK) {
    return false;
  } else if (data_read_size != sizeof(distribution_version_bytes)) {
    return false;
  }
  distribution_version_out->has_value = true;
  distribution_version_out->value = read_be(distribution_version_bytes);
  return true;
}

static bool get_expected_tropic_distribution_version_from_batch_id(
    const uint8_t *batch_id, uint32_t *expected_distribution_version_out) {
  for (size_t i = 0;
       i < sizeof(TROPIC_BATCHES_V1) / sizeof(TROPIC_BATCHES_V1[0]); i++) {
    if (memcmp(batch_id, TROPIC_BATCHES_V1[i], sizeof(TROPIC_BATCHES_V1[0])) ==
        0) {
      *expected_distribution_version_out = 1;
      return true;
    }
  }
  *expected_distribution_version_out = 0;  // Default version
  return true;
}

static bool get_expected_tropic_config(tropic_expected_config_t *config_out) {
  lt_chip_id_t chip_id = {0};
  if (TROPIC_RETRY_COMMAND(
          lt_get_info_chip_id(&g_tropic_driver.handle, &chip_id)) != LT_OK) {
    return false;
  }

  uint32_t expected_distribution_version = 0;
  if (!get_expected_tropic_distribution_version_from_batch_id(
          chip_id.batch_id, &expected_distribution_version)) {
    return false;
  }

  return tropic_get_expected_tropic_config_from_distribution_version(
      expected_distribution_version, config_out);
}

static bool set_backup_distribution_version_to(uint32_t distribution_version) {
  uint8_t distribution_version_bytes[sizeof(distribution_version)] = {0};
  write_be(distribution_version_bytes, distribution_version);
  if (lt_r_mem_data_erase_write_retry(
          &g_tropic_driver.handle,
          TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT,
          distribution_version_bytes,
          sizeof(distribution_version_bytes)) != LT_OK) {
    return false;
  }
  optional_u32_t backup_distribution_version = {0};
  if (!tropic_get_distribution_version(
          TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT,
          &backup_distribution_version)) {
    return false;
  }
  if (!backup_distribution_version.has_value ||
      backup_distribution_version.value != distribution_version) {
    return false;
  }

  return true;
}

// Applies `expected_config` and writes the new distribution version to slot 6.
//
// Crash-safety: the write order is designed so that a power-cut leaves slot 6
// empty. On the next boot, tropic_set_config_main() detects the empty slot and
// calls set_expected_config writing if the r_config is too loose, which
// re-applies the config idempotently:
// i_config writes only flip bits 1→0 (safe to repeat) and r_config is
// rewritten only when the current value is too loose.
//
// Write order (when r_config must be updated):
//   1. Write i_config
//   2. Erase slot 6  ← crash checkpoint: slot 6 empty → recovery on next boot
//   3. Write r_config
//   4. Write slot 6 (new ver)
//   5. Erase slot 7 (backup)
//   6. Restart Tropic so the new config takes effect
static secbool set_expected_config(
    const tropic_expected_config_t *expected_config,
    tropic_r_config_write_mode_t r_config_write_mode) {
  if (expected_config == NULL) {
    return secfalse;
  }
  if (tropic_ensure_i_config(expected_config->i_config) != sectrue) {
    return secfalse;
  }

  lt_config_t current_r_config = {0};
  if (lt_read_whole_R_config_retry(&g_tropic_driver.handle,
                                   &current_r_config) != LT_OK) {
    return secfalse;
  }

  bool write_r_config = false;
  switch (r_config_write_mode) {
    case TROPIC_R_CONFIG_WRITE_ALWAYS:
      write_r_config = true;
      break;
    case TROPIC_R_CONFIG_WRITE_IF_TOO_LOOSE: {
      tropic_config_strictness_t strictness = compare_config_strictness(
          expected_config->min_r_config, &current_r_config);
      if (strictness == TROPIC_CONFIG_STRICTNESS_FIRST_STRICTER) {
        write_r_config = true;
      } else if (strictness == TROPIC_CONFIG_STRICTNESS_EQUAL ||
                 strictness == TROPIC_CONFIG_STRICTNESS_SECOND_STRICTER) {
        write_r_config = false;
      } else if (strictness == TROPIC_CONFIG_STRICTNESS_INCOMPARABLE) {
        if (compare_config_strictness(expected_config->max_r_config,
                                      &current_r_config) ==
            TROPIC_CONFIG_STRICTNESS_FIRST_STRICTER) {
          write_r_config = true;
        } else {
          return secfalse;
        }
      } else {
        return secfalse;
      }
      break;
    }
    default:
      return secfalse;
  }

  if (write_r_config) {
    if (lt_r_mem_data_erase_retry(&g_tropic_driver.handle,
                                  TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT) !=
        LT_OK) {
      return secfalse;
    }

    if (tropic_ensure_r_config(expected_config->max_r_config) != sectrue) {
      return secfalse;
    }
  }

  uint8_t distribution_version_bytes[sizeof(uint32_t)] = {0};
  write_be(distribution_version_bytes, expected_config->distribution_version);
  if (lt_r_mem_data_write_retry(&g_tropic_driver.handle,
                                TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT,
                                distribution_version_bytes,
                                sizeof(distribution_version_bytes)) != LT_OK) {
    return secfalse;
  }

  optional_u32_t distribution_version_read = {0};
  if (!tropic_get_distribution_version(TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT,
                                       &distribution_version_read)) {
    return secfalse;
  }
  if (!distribution_version_read.has_value ||
      distribution_version_read.value !=
          expected_config->distribution_version) {
    return secfalse;
  }

  if (lt_r_mem_data_erase_retry(
          &g_tropic_driver.handle,
          TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT) != LT_OK) {
    return secfalse;
  }

  if (lt_reboot(&g_tropic_driver.handle, TR01_REBOOT) != LT_OK) {
    return secfalse;
  }

  return sectrue;
}

// clang-format off
// Reads the chip's current distribution state and applies the expected config.
//
// Slot 6 = current distribution version; slot 7 = backup used during upgrade.
// The four observable states and their meaning:
//
//   slot 6 empty, slot 7 empty  → fresh chip; set config if too loose
//   slot 6 empty, slot 7 set    → interrupted upgrade (power-cut during
//                                  set_expected_config); set config if too loose
//   slot 6 set,   slot 7 set    → upgrade wrote slot 6 but not yet erased slot 7;
//                                  treat as current==slot6; backup is ignored
//   slot 6 set,   slot 7 empty  → steady state
//
// Upgrade path (slot 6 < expected): write old version to slot 7 *before*
// erasing slot 6, so the "slot 6 empty" crash-recovery checkpoint always
// carries the prior version in slot 7 for diagnostic purposes.
// clang-format on
static secbool tropic_set_config_main(void) {
  tropic_expected_config_t expected_config = {0};
  if (!get_expected_tropic_config(&expected_config)) {
    return secfalse;
  }
  optional_u32_t current_distribution_version = {0};
  if (!tropic_get_distribution_version(TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT,
                                       &current_distribution_version)) {
    return secfalse;
  }
  if (!current_distribution_version.has_value) {
    optional_u32_t backup_distribution_version = {0};
    if (!tropic_get_distribution_version(
            TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT,
            &backup_distribution_version)) {
      return secfalse;
    }
    if (backup_distribution_version.has_value &&
        backup_distribution_version.value >
            expected_config.distribution_version) {
      return secfalse;
    }

    if (set_expected_config(&expected_config,
                            TROPIC_R_CONFIG_WRITE_IF_TOO_LOOSE) != sectrue) {
      return secfalse;
    }
    return sectrue;
  }
  if (current_distribution_version.value <
      expected_config.distribution_version) {
    if (!set_backup_distribution_version_to(
            current_distribution_version.value)) {
      return secfalse;
    }
    if (set_expected_config(&expected_config, TROPIC_R_CONFIG_WRITE_ALWAYS) !=
        sectrue) {
      return secfalse;
    }
    return sectrue;
  }
  // current >= expected: chip is already at or ahead of the expected
  // distribution. If ahead (downgrade scenario), preserve it unchanged.
  return sectrue;
}

secbool tropic_ensure_configuration(void) {
  if (!tropic_session_start()) {
    return secfalse;
  }

  if (tropic_set_config_main() != sectrue) {
    return secfalse;
  }
  return sectrue;
}

#ifdef TREZOR_EMULATOR
static uint16_t get_tropic_model_port(void) {
  char *port_str = getenv("TROPIC_MODEL_PORT");
  if (port_str != NULL) {
    char *endptr;
    long port_long = strtol(port_str, &endptr, 10);
    if (*endptr != '\0' || port_long < 0 || port_long > 65535) {
      printf("FATAL: invalid TROPIC_MODEL_PORT\n");
      exit(1);
    }
    return (uint16_t)port_long;
  }
  return 28992;
}
#endif

// If `TREZOR_PRODTEST` is not defined, the `cli` argument is ignored.
lt_ret_t tropic_init(cli_t *cli) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (drv->initialized) {
    return LT_OK;
  }

#ifdef TREZOR_EMULATOR
  drv->device.addr = inet_addr("127.0.0.1");
  drv->device.port = get_tropic_model_port();
  drv->handle.l2.device = &drv->device;
#endif  // TREZOR_EMULATOR

  // Initialize crypto context
  drv->handle.l3.crypto_ctx = &drv->crypto_ctx;

  lt_ret_t ret = lt_init(&drv->handle);
#if !defined(TREZOR_PRODTEST) && !defined(TREZOR_EMULATOR)
  // On HW Firmware, retry a failed init.
  // Prodtest skips it to surface the init error.
  // Emulator has no retry logic.
  for (int i = 0; i < TROPIC_MAX_RETRIES - 1 && is_retryable(ret); i++) {
    lt_deinit(&drv->handle);
    ret = lt_init(&drv->handle);
  }
#endif  // !TREZOR_PRODTEST && !TREZOR_EMULATOR

  if (ret != LT_OK) {
#ifdef TREZOR_PRODTEST
    if (cli) {
      cli_trace(cli, "`lt_init()` failed with error '%s'", lt_ret_verbose(ret));
    }
#endif
    return ret;
  }
  drv->initialized = true;

  return LT_OK;
}

void tropic_deinit(void) {
  tropic_driver_t *drv = &g_tropic_driver;
  if (drv->handle.l3.crypto_ctx != NULL) {
    lt_deinit(&drv->handle);
  }
  memset(drv, 0, sizeof(*drv));
}

#ifdef TREZOR_PRODTEST
static lt_handle_t *tropic_get_handle(void) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!drv->initialized) {
    return NULL;
  }

  return &drv->handle;
}

lt_handle_t *tropic_prodtest_init_and_get_handle(cli_t *cli) {
  if (tropic_init(cli) != LT_OK) {
    return NULL;
  }

  return tropic_get_handle();
}
#endif  // TREZOR_PRODTEST

bool tropic_ping(const uint8_t *msg_out, uint8_t *msg_in, uint16_t msg_len) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  lt_ret_t res = lt_ping(&drv->handle, msg_out, msg_in, msg_len);
  return res == LT_OK;
}

bool tropic_ecc_key_generate(uint16_t slot_index) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  if (slot_index > TR01_ECC_SLOT_31) {
    return false;
  }

  lt_ret_t ret =
      lt_ecc_key_generate(&drv->handle, slot_index, TR01_CURVE_ED25519);
  return ret == LT_OK;
}

bool tropic_ecc_sign(uint16_t key_slot_index, const uint8_t *dig,
                     uint16_t dig_len, uint8_t *sig) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  if (key_slot_index > TR01_ECC_SLOT_31) {
    return false;
  }

  lt_ret_t res = TROPIC_RETRY_COMMAND(
      lt_ecc_eddsa_sign(&drv->handle, key_slot_index, dig, dig_len, sig));
  if (res != LT_OK) {
    memzero(sig, ECDSA_RAW_SIGNATURE_SIZE);
    return false;
  }

  return true;
}

bool tropic_data_read(uint16_t udata_slot, uint8_t *data, uint16_t *size) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  if (udata_slot > TR01_R_MEM_DATA_SLOT_MAX) {
    return false;
  }

  lt_ret_t res = lt_r_mem_data_read_retry(&drv->handle, udata_slot, data,
                                          TROPIC_SLOT_MAX_SIZE_V1, size);
  return res == LT_OK;
}

void tropic_get_factory_privkey(curve25519_key privkey) {
#ifdef TREZOR_EMULATOR
  curve25519_key factory_private = {
      0xf0, 0xc4, 0xaa, 0x04, 0x8f, 0x00, 0x13, 0xa0, 0x96, 0x84, 0xdf,
      0x05, 0xe8, 0xa2, 0x2e, 0xf7, 0x21, 0x38, 0x98, 0x28, 0x2b, 0xa9,
      0x43, 0x12, 0xf3, 0x13, 0xdf, 0x2d, 0xce, 0x8d, 0x41, 0x64};
#else
#ifdef TROPIC_TESTING_KEYS
  // Testing keys (used in TROPIC01-P2S-P001)
  curve25519_key factory_private = {
      0xd0, 0x99, 0x92, 0xb1, 0xf1, 0x7a, 0xbc, 0x4d, 0xb9, 0x37, 0x17,
      0x68, 0xa2, 0x7d, 0xa0, 0x5b, 0x18, 0xfa, 0xb8, 0x56, 0x13, 0xa7,
      0x84, 0x2c, 0xa6, 0x4c, 0x79, 0x10, 0xf2, 0x2e, 0x71, 0x6b};
#else
  // Production keys
  curve25519_key factory_private = {
      0x28, 0x3f, 0x5a, 0x0f, 0xfc, 0x41, 0xcf, 0x50, 0x98, 0xa8, 0xe1,
      0x7d, 0xb6, 0x37, 0x2c, 0x3c, 0xaa, 0xd1, 0xee, 0xee, 0xdf, 0x0f,
      0x75, 0xbc, 0x3f, 0xbf, 0xcd, 0x9c, 0xab, 0x3d, 0xe9, 0x72};
#endif
#endif
  memcpy(privkey, factory_private, sizeof(curve25519_key));
}

bool tropic_random_buffer(void *buffer, size_t length) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (!tropic_session_start()) {
    return false;
  }

  if (LT_OK != lt_random_value_get(&drv->handle, buffer, length)) {
    return false;
  }

  return true;
}

void tropic_random_buffer_time(uint32_t *time_ms) {
  // Assuming the data size is 32 bytes
  *time_ms += 10;
}

#ifdef USE_STORAGE

// Defined in tropic01.c
void tropic_set_ui_progress(tropic_ui_progress_t f);

static lt_mac_and_destroy_slot_t get_mac_and_destroy_slot(
    uint16_t pin_index, uint32_t change_pin_counter) {
  lt_mac_and_destroy_slot_t first_slot_index =
      g_tropic_driver.pairing_key_index == TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT
          ? TROPIC_FIRST_MAC_AND_DESTROY_SLOT_UNPRIVILEGED
          : TROPIC_FIRST_MAC_AND_DESTROY_SLOT_PRIVILEGED;

  return first_slot_index +
         (change_pin_counter * TROPIC_MAC_AND_DESTROY_SHIFT + pin_index) %
             TROPIC_MAC_AND_DESTROY_SLOT_COUNT;
}

static uint16_t get_kek_masks_slot(tropic_driver_t *drv) {
  return drv->pairing_key_index == TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT
             ? TROPIC_KEK_MASKS_UNPRIVILEGED_SLOT
             : TROPIC_KEK_MASKS_PRIVILEGED_SLOT;
}

static void lt_mac_and_destroy_time(uint32_t *time_ms) { *time_ms += 28; }

static void lt_r_mem_data_read_time(uint32_t *time_ms) {
  // Assuming the data size is 320 bytes
  *time_ms += 33;
}

static void lt_r_mem_data_write_time(uint32_t *time_ms) {
  // Assuming the data size is 320 bytes
  *time_ms += 37;
}

static void lt_r_mem_data_erase_time(uint32_t *time_ms) { *time_ms += 4; }

static void lt_mcounter_get_time(uint32_t *time_ms) { *time_ms += 4; }

static void lt_mcounter_update_time(uint32_t *time_ms) { *time_ms += 4; }

lt_ret_t lt_r_mem_data_erase_write_time(uint32_t *time_ms) {
  lt_r_mem_data_erase_time(time_ms);
  lt_r_mem_data_write_time(time_ms);
  return LT_OK;
}

static uint32_t g_change_pin_counter_cached = 0;
static bool g_is_change_pin_counter_cached = false;

static bool get_change_pin_counter(uint32_t *change_pin_counter) {
  tropic_driver_t *drv = &g_tropic_driver;

  if (g_is_change_pin_counter_cached) {
    *change_pin_counter = g_change_pin_counter_cached;
    return true;
  }

  lt_ret_t ret = TROPIC_RETRY_COMMAND(lt_mcounter_get(
      &drv->handle, TROPIC_CHANGE_COUNTER_SLOT, change_pin_counter));
  if (ret == LT_OK) {
    *change_pin_counter =
        TROPIC_CHANGE_COUNTER_SLOT_MAX_VALUE - *change_pin_counter;
  } else if (ret == LT_L3_COUNTER_INVALID) {
    // The counter has not been initialized yet
    *change_pin_counter = 0;
  } else {
    return false;
  }

  g_change_pin_counter_cached = *change_pin_counter;
  g_is_change_pin_counter_cached = true;

  return true;
}

static void get_change_pin_counter_time(uint32_t *time_ms,
                                        bool is_change_pin_counter_cached) {
  if (!is_change_pin_counter_cached) {
    lt_mcounter_get_time(time_ms);
  }
}

static bool update_change_pin_counter() {
  tropic_driver_t *drv = &g_tropic_driver;

  // The cache is invalidated because the counter may be updated more than once
  g_is_change_pin_counter_cached = false;
  lt_ret_t ret = TROPIC_RETRY_COMMAND(
      lt_mcounter_update(&drv->handle, TROPIC_CHANGE_COUNTER_SLOT));
  if (ret == LT_L3_COUNTER_INVALID || ret == LT_L3_UPDATE_ERR) {
    // The counter has not been initialized yet or is depleted.
    ret = TROPIC_RETRY_COMMAND(
        lt_mcounter_init(&drv->handle, TROPIC_CHANGE_COUNTER_SLOT,
                         TROPIC_CHANGE_COUNTER_SLOT_MAX_VALUE - 1));
    if (ret != LT_OK) {
      return false;
    }
    g_change_pin_counter_cached = 1;
    g_is_change_pin_counter_cached = true;
    return true;
  }

  if (ret != LT_OK) {
    return false;
  }

  return true;
}

static void update_change_pin_counter_time(uint32_t *time_ms) {
  lt_mcounter_update_time(time_ms);
  // Ignore the time of `lt_mcounter_init()` since we cannot easily determine
  // whether it will be executed.
}

bool tropic_pin_stretch(tropic_ui_progress_t ui_progress, uint16_t pin_index,
                        uint8_t stretched_pin[TROPIC_MAC_AND_DESTROY_SIZE]) {
  if (pin_index >= PIN_MAX_TRIES) {
    return false;
  }

  tropic_driver_t *drv = &g_tropic_driver;
  bool ret = false;

  tropic_set_ui_progress(ui_progress);

  if (!tropic_session_start()) {
    goto cleanup;
  }

  uint8_t digest[TROPIC_MAC_AND_DESTROY_SIZE] = {0};

  hmac_sha256(stretched_pin, TROPIC_MAC_AND_DESTROY_SIZE, NULL, 0, digest);

  uint32_t change_pin_counter = 0;
  if (!get_change_pin_counter(&change_pin_counter)) {
    goto cleanup;
  }

  lt_mac_and_destroy_slot_t slot_index =
      get_mac_and_destroy_slot(pin_index, change_pin_counter);
  // When `lt_mac_and_destroy()` returns an error and it is unclear whether the
  // command was executed or not (for example, it returns LT_L1_CHIP_ALARM_MODE
  // or LT_L1_SPI_ERROR), the best approach is to retry the command, hoping it
  // has not already been been executed. If it has been executed, the PIN
  // verification will fail.
  if (TROPIC_RETRY_COMMAND(lt_mac_and_destroy(&drv->handle, slot_index, digest,
                                              digest)) != LT_OK) {
    goto cleanup;
  }

  hmac_sha256(stretched_pin, TROPIC_MAC_AND_DESTROY_SIZE, digest,
              sizeof(digest), stretched_pin);

  ret = true;

cleanup:
  memzero(digest, sizeof(digest));
  tropic_set_ui_progress(NULL);
  return ret;
}

void tropic_pin_stretch_time(uint32_t *time_ms) {
  get_change_pin_counter_time(time_ms, g_is_change_pin_counter_cached);
  lt_mac_and_destroy_time(time_ms);
}

bool tropic_pin_reset_slots(
    tropic_ui_progress_t ui_progress, uint16_t pin_index,
    const uint8_t reset_key[TROPIC_MAC_AND_DESTROY_SIZE]) {
  if (pin_index >= PIN_MAX_TRIES) {
    return false;
  }

  tropic_driver_t *drv = &g_tropic_driver;
  bool ret = false;

  tropic_set_ui_progress(ui_progress);

  if (!tropic_session_start()) {
    goto cleanup;
  }

  uint8_t output[TROPIC_MAC_AND_DESTROY_SIZE] = {0};

  uint32_t change_pin_counter = 0;
  if (!get_change_pin_counter(&change_pin_counter)) {
    goto cleanup;
  }

  for (int i = 0; i <= pin_index; i++) {
    if (TROPIC_RETRY_COMMAND(lt_mac_and_destroy(
            &drv->handle, get_mac_and_destroy_slot(i, change_pin_counter),
            reset_key, output)) != LT_OK) {
      goto cleanup;
    }
  }

  ret = true;

cleanup:
  memzero(output, sizeof(output));
  tropic_set_ui_progress(NULL);

  return ret;
}

void tropic_pin_reset_slots_time(uint32_t *time_ms, uint16_t pin_index) {
  // When get_change_pin_counter() is called in tropic_pin_reset_slots(), the
  // change pin counter will have already been cached by
  // get_change_pin_counter() in tropic_pin_stretch()
  get_change_pin_counter_time(time_ms, true);
  for (int i = 0; i <= pin_index; i++) {
    lt_mac_and_destroy_time(time_ms);
  }
}

static lt_ret_t generate_correct_mac_and_destroy_output(
    lt_handle_t *handle, uint16_t slot_index,
    const uint8_t reset_key[TROPIC_MAC_AND_DESTROY_SIZE],
    const uint8_t input[TROPIC_MAC_AND_DESTROY_SIZE],
    uint8_t output[TROPIC_MAC_AND_DESTROY_SIZE]) {
  lt_ret_t res = lt_mac_and_destroy(handle, slot_index, reset_key, output);
  if (res != LT_OK) {
    return res;
  }

  return lt_mac_and_destroy(handle, slot_index, input, output);
}

static void generate_correct_mac_and_destroy_output_time(uint32_t *time_ms) {
  lt_mac_and_destroy_time(time_ms);
  lt_mac_and_destroy_time(time_ms);
}

bool tropic_pin_set(
    tropic_ui_progress_t ui_progress,
    uint8_t stretched_pins[PIN_MAX_TRIES][TROPIC_MAC_AND_DESTROY_SIZE],
    uint8_t reset_key[TROPIC_MAC_AND_DESTROY_SIZE]) {
  tropic_driver_t *drv = &g_tropic_driver;
  bool ret = false;

  tropic_set_ui_progress(ui_progress);

  if (!tropic_session_start()) {
    goto cleanup;
  }

  if (!rng_fill_buffer_strong(reset_key, TROPIC_MAC_AND_DESTROY_SIZE)) {
    goto cleanup;
  }

  if (!update_change_pin_counter()) {
    goto cleanup;
  }
  uint32_t change_pin_counter = 0;
  if (!get_change_pin_counter(&change_pin_counter)) {
    goto cleanup;
  }

  uint8_t output[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
  uint8_t digest[TROPIC_MAC_AND_DESTROY_SIZE] = {0};

  for (int i = 0; i < PIN_MAX_TRIES; i++) {
    lt_mac_and_destroy_slot_t slot_index =
        get_mac_and_destroy_slot(i, change_pin_counter);

    hmac_sha256(stretched_pins[i], TROPIC_MAC_AND_DESTROY_SIZE, NULL, 0,
                digest);

    if (TROPIC_RETRY_COMMAND(generate_correct_mac_and_destroy_output(
            &drv->handle, slot_index, reset_key, digest, output)) != LT_OK) {
      goto cleanup;
    }

    hmac_sha256(stretched_pins[i], TROPIC_MAC_AND_DESTROY_SIZE, output,
                sizeof(output), stretched_pins[i]);

    if (TROPIC_RETRY_COMMAND(lt_mac_and_destroy(&drv->handle, slot_index,
                                                reset_key, output)) != LT_OK) {
      goto cleanup;
    }
  }

  ret = true;

cleanup:
  memzero(output, sizeof(output));
  memzero(digest, sizeof(digest));
  tropic_set_ui_progress(NULL);

  return ret;
}

void tropic_pin_set_time(uint32_t *time_ms) {
  rng_fill_buffer_strong_time(time_ms);
  update_change_pin_counter_time(time_ms);
  // When get_change_pin_counter() is called in tropic_pin_set(), the
  // change pin counter will have already been cached by
  // update_change_pin_counter() in tropic_pin_set()
  get_change_pin_counter_time(time_ms, true);
  for (int i = 0; i < PIN_MAX_TRIES; i++) {
    generate_correct_mac_and_destroy_output_time(time_ms);
    lt_mac_and_destroy_time(time_ms);
  }
}

bool tropic_pin_set_kek_masks(
    tropic_ui_progress_t ui_progress,
    const uint8_t kek[TROPIC_MAC_AND_DESTROY_SIZE],
    const uint8_t stretched_pins[PIN_MAX_TRIES][TROPIC_MAC_AND_DESTROY_SIZE]) {
  tropic_driver_t *drv = &g_tropic_driver;
  bool ret = false;

  tropic_set_ui_progress(ui_progress);

  if (!tropic_session_start()) {
    goto cleanup;
  }

  uint8_t masks[PIN_MAX_TRIES * TROPIC_MAC_AND_DESTROY_SIZE] = {0};
  for (int i = 0; i < PIN_MAX_TRIES; i++) {
    for (int j = 0; j < TROPIC_MAC_AND_DESTROY_SIZE; j++) {
      masks[i * TROPIC_MAC_AND_DESTROY_SIZE + j] =
          kek[j] ^ stretched_pins[i][j];
    }
  }

  uint16_t masked_kek_slot = get_kek_masks_slot(drv);

  // Size of masks need to be smaller than or equal to TROPIC_SLOT_MAX_SIZE_V1
  // for backwards compatibility. See the definition of TROPIC_SLOT_MAX_SIZE_V1
  // for more details.
  _Static_assert(TROPIC_SLOT_MAX_SIZE_V1 >= sizeof(masks),
                 "masks buffer too big");

  if (TROPIC_RETRY_COMMAND(lt_r_mem_data_erase_write(
          &drv->handle, masked_kek_slot, masks, sizeof(masks))) != LT_OK) {
    goto cleanup;
  }

  ret = true;

cleanup:
  memzero(masks, sizeof(masks));
  tropic_set_ui_progress(NULL);

  return ret;
}

void tropic_pin_set_kek_masks_time(uint32_t *time_ms) {
  lt_r_mem_data_erase_write_time(time_ms);
}

bool tropic_pin_unmask_kek(
    tropic_ui_progress_t ui_progress, uint16_t pin_index,
    const uint8_t stretched_pin[TROPIC_MAC_AND_DESTROY_SIZE],
    uint8_t kek[TROPIC_MAC_AND_DESTROY_SIZE]) {
  tropic_driver_t *drv = &g_tropic_driver;

  tropic_set_ui_progress(ui_progress);
  bool ret = false;

  if (!tropic_session_start()) {
    goto cleanup;
  }

  uint8_t masks[TROPIC_SLOT_MAX_SIZE_V1] = {0};
  _Static_assert(
      TROPIC_SLOT_MAX_SIZE_V1 >= PIN_MAX_TRIES * TROPIC_MAC_AND_DESTROY_SIZE,
      "TROPIC_SLOT_MAX_SIZE_V1 too small");
  uint16_t length = 0;

  uint16_t masked_kek_slot = get_kek_masks_slot(drv);

  if (TROPIC_RETRY_COMMAND(lt_r_mem_data_read(&drv->handle, masked_kek_slot,
                                              masks, TROPIC_SLOT_MAX_SIZE_V1,
                                              &length)) != LT_OK) {
    goto cleanup;
  }

  if (length != PIN_MAX_TRIES * TROPIC_MAC_AND_DESTROY_SIZE) {
    goto cleanup;
  }

  for (int i = 0; i < TROPIC_MAC_AND_DESTROY_SIZE; i++) {
    kek[i] =
        masks[pin_index * TROPIC_MAC_AND_DESTROY_SIZE + i] ^ stretched_pin[i];
  }

  ret = true;

cleanup:
  tropic_set_ui_progress(NULL);
  return ret;
}

void tropic_pin_unmask_kek_time(uint32_t *time_ms) {
  lt_r_mem_data_read_time(time_ms);
}

#endif  // USE_STORAGE

#endif  // SECURE_MODE

bool tropic_data_multi_size(uint16_t first_slot, size_t *data_length) {
  if (first_slot > TR01_R_MEM_DATA_SLOT_MAX) {
    return false;
  }

  uint8_t prefixed_data[TROPIC_SLOT_MAX_SIZE_V1];
  uint16_t slot_length = 0;
  if (!tropic_data_read(first_slot, prefixed_data, &slot_length)) {
    return false;
  }

  const size_t prefix_length = 2;
  if (slot_length < prefix_length) {
    return false;
  }

  *data_length = prefixed_data[0] << 8 | prefixed_data[1];
  return true;
}

static size_t min(size_t x, size_t y) { return (x < y) ? x : y; }

bool tropic_data_multi_read(uint16_t first_slot, uint16_t slot_count,
                            uint8_t *data, size_t max_data_length,
                            size_t *data_length) {
  if (first_slot > TR01_R_MEM_DATA_SLOT_MAX || slot_count == 0 ||
      slot_count > TR01_R_MEM_DATA_SLOT_MAX + 1 - first_slot) {
    return false;
  }

  uint16_t slot = first_slot;
  uint8_t slot_buffer[TROPIC_SLOT_MAX_SIZE_V1] = {0};
  uint16_t slot_length = 0;
  if (!tropic_data_read(slot, slot_buffer, &slot_length)) {
    return false;
  }

  const size_t prefix_length = 2;
  if (slot_length < prefix_length) {
    return false;
  }

  size_t out_length = slot_buffer[0] << 8 | slot_buffer[1];
  uint16_t occupied_slot_count =
      (out_length + prefix_length + TROPIC_SLOT_MAX_SIZE_V1 - 1) /
      TROPIC_SLOT_MAX_SIZE_V1;
  if (out_length > max_data_length || occupied_slot_count > slot_count) {
    return false;
  }

  size_t out_pos = 0;
  // Terminal slots may be padded. Make sure not to copy beyond the actual data
  // length.
  size_t copy_length = min(slot_length - prefix_length, out_length - out_pos);
  if (out_pos + copy_length > max_data_length) {
    return false;
  }
  memcpy(&data[out_pos], &slot_buffer[prefix_length], copy_length);
  out_pos += copy_length;

  uint16_t last_data_slot = first_slot + occupied_slot_count - 1;
  while (slot < last_data_slot) {
    // Non-terminal slots must be used to their full capacity.
    if (slot_length != TROPIC_SLOT_MAX_SIZE_V1) {
      return false;
    }

    // Read next slot.
    slot += 1;
    if (!tropic_data_read(slot, slot_buffer, &slot_length)) {
      return false;
    }

    // Terminal slots may be padded. Make sure not to copy beyond the actual
    // data length.
    copy_length = min(slot_length, out_length - out_pos);
    memcpy(&data[out_pos], slot_buffer, copy_length);
    out_pos += copy_length;
  }

  if (out_pos != out_length) {
    // The terminal slot had less data than expected.
    return false;
  }

  *data_length = out_length;

  return true;
}
