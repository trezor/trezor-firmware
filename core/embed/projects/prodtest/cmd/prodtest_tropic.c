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
#include <sec/rng.h>
#include <sec/tropic.h>
#include <sys/systick.h>

#include <sec/secret.h>
#include <sec/secret_keys.h>

#include "ecdsa.h"
#include "memzero.h"
#include "nist256p1.h"

#include "common.h"
#include "fw_CPU.h"
#include "fw_SPECT.h"
#include "libtropic.h"
#include "lt_l2.h"

#include <sec/tropic.h>

#include "secure_channel.h"

typedef enum {
  TROPIC_HANDSHAKE_STATE_0,  // Handshake has not been initiated yet
  TROPIC_HANDSHAKE_STATE_1,  // Handshake completed (after calling
                             // `tropic-handshake`), `tropic-send-command` can
                             // be called
} tropic_handshake_state_t;

static tropic_handshake_state_t tropic_handshake_state =
    TROPIC_HANDSHAKE_STATE_0;

// TODO: Update this link to correspond with the latest chip revision when it
// becomes available.
// https://github.com/tropicsquare/tropic01/blob/da459d18db7aea107419035b9cdf316d89a73445/doc/api/tropic01_user_api_v1.1.2.pdf
// TODO: Adjust the configuration to match the revision of the provisioned
// tropics.
// clang-format off
static struct lt_config_t irreversible_configuration = {
    .obj = {
        // # CFG_START_UP (0x00)
        // | Setting                 | Value                   |
        // |-------------------------|-------------------------|
        // | RFU_1 (bit 0)           | 1                       |
        // | MBIST_DIS (bit 1)       | 0 (TEST_ON)             |
        // | RNGTEST_DIS (bit 2)     | 0 (TEST_ON)             |
        // | MAINTENANCE_ENA (bit 3) | 1 (MAINTENANCE_ALLOWED) |
        ~0U & ~BIT(1) & ~BIT(2),
        // # CFG_SENSORS (0x08)
        // | Setting                         | Value                |
        // |---------------------------------|----------------------|
        // | PTRNG0_TEST_DIS (bit 0)         | 1 (NO_ACTION)        |
        // | PTRNG1_TEST_DIS (bit 1)         | 1 (NO_ACTION)        |
        // | OSCILLATOR_MON_DIS (bit 2)      | 1 (NO_ACTION)        |
        // | SHIELD_DIS (bit 3)              | 1 (NO_ACTION)        |
        // | VOLTAGE_MON_DIS (bit 4)         | 1 (NO_ACTION)        |
        // | GLITCH_DET_DIS (bit 5)          | 1 (NO_ACTION)        |
        // | TEMP_SENS_DIS (bit 6)           | 1 (NO_ACTION)        |
        // | LASER_DET_DIS (bit 7)           | 1 (NO_ACTION)        |
        // | EM_PULSE_DET_DIS (bit 8)        | 1 (NO_ACTION)        |
        // | CPU_ALERT_DIS (bit 9)           | 1 (NO_ACTION)        |
        // | PIN_VERIF_BIT_FLIP_DIS (bit 10) | 1 (NO_ACTION)        |
        // | SCB_BIT_FLIP_DIS (bit 11)       | 1 (NO_ACTION)        |
        // | CPB_BIT_FLIP_DIS (bit 12)       | 1 (NO_ACTION)        |
        // | ECC_BIT_FLIP_DIS (bit 13)       | 1 (NO_ACTION)        |
        // | R_MEM_BIT_FLIP_DIS (bit 14)     | 1 (NO_ACTION)        |
        // | EKDB_BIT_FLIP_DIS (bit 15)      | 1 (NO_ACTION)        |
        // | I_MEM_BIT_FLIP_DIS (bit 16)     | 1 (NO_ACTION)        |
        // | PLATFORM_BIT_FLIP_DIS (bit 17)  | 1 (NO_ACTION)        |
        ~0U,
        // # CFG_DEBUG (0x10)
        // | Setting           | Value |
        // |-------------------|-------|
        // | FW_LOG_EN (bit 0) | 0     |
        ~0U & ~BIT(0),
        // # CFG_GPO (0x14)
        ~0U,
        // # CFG_SLEEP_MODE (0x18)
        // | Setting               | Value |
        // |-----------------------|-------|
        // | SLEEP_MODE_EN (bit 0) | 1     |
        ~0U,
        // # CFG_UAP_PAIRING_KEY_WRITE (0x20)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | WRITE_PKEY_SLOT_0        | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | WRITE_PKEY_SLOT_1        | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | WRITE_PKEY_SLOT_2        | 0 (bit 16)    | 0 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | WRITE_PKEY_SLOT_3        | 0 (bit 24)    | 0 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(9) & ~BIT(16) & ~BIT(17) & ~BIT(24) & ~BIT(25),
        // # CFG_UAP_PAIRING_KEY_READ (0x24)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_PKEY_SLOT_0         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | READ_PKEY_SLOT_1         | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | READ_PKEY_SLOT_2         | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | READ_PKEY_SLOT_3         | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_PAIRING_KEY_INVALIDATE (0x28)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | INVALIDATE_PKEY_SLOT_0   |   0 (bit 0)   |   1 (bit 1)   |   1 (bit 2)   |   1 (bit 3)   |
        // | INVALIDATE_PKEY_SLOT_1   |   0 (bit 8)   |   1 (bit 9)   |   1 (bit 10)  |   1 (bit 11)  |
        // | INVALIDATE_PKEY_SLOT_2   |   0 (bit 16)  |   1 (bit 17)  |   1 (bit 18)  |   1 (bit 19)  |
        // | INVALIDATE_PKEY_SLOT_3   |   0 (bit 24)  |   1 (bit 25)  |   1 (bit 26)  |   1 (bit 27)  |
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_R_CONFIG_WRITE_ERASE (0x30)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | R_CONFIG_WRITE_ERASE     | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        ~0U & ~BIT(0) & ~BIT(1),
        // # CFG_UAP_R_CONFIG_READ (0x34)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | R_CONFIG_READ_CFG        | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | R_CONFIG_READ_FUNC       | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        ~0U & ~BIT(0) & ~BIT(8),
        // # CFG_UAP_I_CONFIG_WRITE (0x40)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | I_CONFIG_WRITE_CFG       | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | I_CONFIG_WRITE_FUNC      | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        ~0U & ~BIT(0) & ~BIT(8),
        // # CFG_UAP_I_CONFIG_READ (0x44)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | I_CONFIG_READ_CFG        | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | I_CONFIG_READ_FUNC       | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        ~0U & ~BIT(0) & ~BIT(8),
        // # CFG_UAP_PING (0x100)
        // | Setting | Pairing Key 0  | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |---------|----------------|---------------|---------------|---------------|
        // | PING    | 0 (bit 0)      | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        ~0U & ~BIT(0),
        // # CFG_UAP_R_MEM_DATA_WRITE (0x110)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | WRITE_UDATA_SLOT_0_127   | 0 (bit 0)   | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | WRITE_UDATA_SLOT_128_255 | 0 (bit 8)   | 0 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | WRITE_UDATA_SLOT_256_383 | 0 (bit 16)  | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | WRITE_UDATA_SLOT_384_511 | 0 (bit 24)  | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(9) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_R_MEM_DATA_READ (0x114)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_UDATA_SLOT_0_127    | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | READ_UDATA_SLOT_128_255  | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | READ_UDATA_SLOT_256_383  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | READ_UDATA_SLOT_384_511  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(9) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_R_MEM_DATA_ERASE (0x118)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ERASE_UDATA_SLOT_0_127   | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | ERASE_UDATA_SLOT_128_255 | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | ERASE_UDATA_SLOT_256_383 | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | ERASE_UDATA_SLOT_384_511 | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(9) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_RANDOM_VALUE_GET (0x120)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | RANDOM_VALUE_GET         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        ~0U & ~BIT(0),
        // # CFG_UAP_ECC_KEY_GENERATE (0x130)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | GEN_ECCKEY_SLOT_0_7      | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | GEN_ECCKEY_SLOT_8_15     | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | GEN_ECCKEY_SLOT_16_23    | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | GEN_ECCKEY_SLOT_24_31    | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_ECC_KEY_STORE (0x134)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | STORE_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | STORE_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | STORE_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | STORE_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_ECC_KEY_READ (0x138)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_ECCKEY_SLOT_0_7     | 0 (bit 0)    | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | READ_ECCKEY_SLOT_8_15    | 0 (bit 8)    | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | READ_ECCKEY_SLOT_16_23   | 0 (bit 16)   | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | READ_ECCKEY_SLOT_24_31   | 0 (bit 24)   | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_ECC_KEY_ERASE (0x13c)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ERASE_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | ERASE_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | ERASE_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | ERASE_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_ECDSA_SIGN (0x140)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ECDSA_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | ECDSA_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | ECDSA_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | ECDSA_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_EDDSA_SIGN (0x144)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | EDDSA_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | EDDSA_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | EDDSA_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | EDDSA_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_MCOUNTER_INIT (0x150)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_INIT_0_3        | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | MCOUNTER_INIT_4_7        | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | MCOUNTER_INIT_8_11       | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | MCOUNTER_INIT_12_15      | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_MCOUNTER_GET (0x154)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_GET_0_3         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | MCOUNTER_GET_4_7         | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | MCOUNTER_GET_8_11        | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | MCOUNTER_GET_12_15       | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_MCOUNTER_UPDATE (0x158)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_UPDATE_0_3      | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | MCOUNTER_UPDATE_4_7      | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | MCOUNTER_UPDATE_8_11     | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | MCOUNTER_UPDATE_12_15    | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        // # CFG_UAP_MAC_AND_DESTROY (0x160)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MACANDD_0_31             | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | MACANDD_32_63            | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | MACANDD_64_95            | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | MACANDD_96_127           | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(9) & ~BIT(16) & ~BIT(24),
    }};

// TODO: Adjust the configuration to match the revision of the provisioned
// tropics.
static struct lt_config_t reversible_configuration = {
    .obj = {
        // # CFG_START_UP (0x00)
        // | Setting                 | Value                   |
        // |-------------------------|-------------------------|
        // | RFU_1 (bit 0)           | 1                       |
        // | MBIST_DIS (bit 1)       | 0 (TEST_ON)             |
        // | RNGTEST_DIS (bit 2)     | 0 (TEST_ON)             |
        // | MAINTENANCE_ENA (bit 3) | 1 (MAINTENANCE_ALLOWED) |
        BIT(0) | BIT(3),
        // # CFG_SENSORS (0x08)
        // | Setting                         | Value                |
        // |---------------------------------|----------------------|
        // | PTRNG0_TEST_DIS (bit 0)         | 0 (ENTER_ALARM_MODE) |
        // | PTRNG1_TEST_DIS (bit 1)         | 0 (ENTER_ALARM_MODE) |
        // | OSCILLATOR_MON_DIS (bit 2)      | 0 (ENTER_ALARM_MODE) |
        // | SHIELD_DIS (bit 3)              | 0 (ENTER_ALARM_MODE) |
        // | VOLTAGE_MON_DIS (bit 4)         | 0 (ENTER_ALARM_MODE) |
        // | GLITCH_DET_DIS (bit 5)          | 0 (ENTER_ALARM_MODE) |
        // | TEMP_SENS_DIS (bit 6)           | 0 (ENTER_ALARM_MODE) |
        // | LASER_DET_DIS (bit 7)           | 0 (ENTER_ALARM_MODE) |
        // | EM_PULSE_DET_DIS (bit 8)        | 0 (ENTER_ALARM_MODE) |
        // | CPU_ALERT_DIS (bit 9)           | 0 (ENTER_ALARM_MODE) |
        // | PIN_VERIF_BIT_FLIP_DIS (bit 10) | 0 (ENTER_ALARM_MODE) |
        // | SCB_BIT_FLIP_DIS (bit 11)       | 0 (ENTER_ALARM_MODE) |
        // | CPB_BIT_FLIP_DIS (bit 12)       | 0 (ENTER_ALARM_MODE) |
        // | ECC_BIT_FLIP_DIS (bit 13)       | 0 (ENTER_ALARM_MODE) |
        // | R_MEM_BIT_FLIP_DIS (bit 14)     | 0 (ENTER_ALARM_MODE) |
        // | EKDB_BIT_FLIP_DIS (bit 15)      | 0 (ENTER_ALARM_MODE) |
        // | I_MEM_BIT_FLIP_DIS (bit 16)     | 0 (ENTER_ALARM_MODE) |
        // | PLATFORM_BIT_FLIP_DIS (bit 17)  | 0 (ENTER_ALARM_MODE) |
        0,
        // # CFG_DEBUG (0x10)
        // | Setting           | Value |
        // |-------------------|-------|
        // | FW_LOG_EN (bit 0) | 0     |
        0,
        // # CFG_GPO (0x14)
        0,
        // # CFG_SLEEP_MODE (0x18)
        // | Setting               | Value |
        // |-----------------------|-------|
        // | SLEEP_MODE_EN (bit 0) | 1     |
        BIT(0),
        // # CFG_UAP_PAIRING_KEY_WRITE (0x20)
        // | Target                   | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | WRITE_PKEY_SLOT_0        | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | WRITE_PKEY_SLOT_1        | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | WRITE_PKEY_SLOT_2        | 0 (bit 16)    | 0 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | WRITE_PKEY_SLOT_3        | 0 (bit 24)    | 0 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(2) | BIT(10) | BIT(18) | BIT(26),
        // # CFG_UAP_PAIRING_KEY_READ (0x24)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_PKEY_SLOT_0         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | READ_PKEY_SLOT_1         | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | READ_PKEY_SLOT_2         | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | READ_PKEY_SLOT_3         | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_PAIRING_KEY_INVALIDATE (0x28)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | INVALIDATE_PKEY_SLOT_0   |   0 (bit 0)   |   1 (bit 1)   |   1 (bit 2)   |   0 (bit 3)   |
        // | INVALIDATE_PKEY_SLOT_1   |   0 (bit 8)   |   1 (bit 9)   |   1 (bit 10)  |   0 (bit 11)  |
        // | INVALIDATE_PKEY_SLOT_2   |   0 (bit 16)  |   1 (bit 17)  |   1 (bit 18)  |   0 (bit 19)  |
        // | INVALIDATE_PKEY_SLOT_3   |   0 (bit 24)  |   1 (bit 25)  |   1 (bit 26)  |   0 (bit 27)  |
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_R_CONFIG_WRITE_ERASE (0x30)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | R_CONFIG_WRITE_ERASE     | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        BIT(2),
        // # CFG_UAP_R_CONFIG_READ (0x34)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | R_CONFIG_READ_CFG        | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | R_CONFIG_READ_FUNC       | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        BIT(1) | BIT(2) | BIT(9) | BIT(10),
        // # CFG_UAP_I_CONFIG_WRITE (0x40)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | I_CONFIG_WRITE_CFG       | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | I_CONFIG_WRITE_FUNC      | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        BIT(1) | BIT(2) | BIT(9) | BIT(10),
        // # CFG_UAP_I_CONFIG_READ (0x44)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | I_CONFIG_READ_CFG        | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | I_CONFIG_READ_FUNC       | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        BIT(1) | BIT(2) | BIT(9) | BIT(10),
        // # CFG_UAP_PING (0x100)
        // | Setting | Pairing Key 0  | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |---------|----------------|---------------|---------------|---------------|
        // | PING    | 0 (bit 0)      | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        BIT(1) | BIT(2),
        // # CFG_UAP_R_MEM_DATA_WRITE (0x110)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | WRITE_UDATA_SLOT_0_127   | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | WRITE_UDATA_SLOT_128_255 | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | WRITE_UDATA_SLOT_256_383 | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | WRITE_UDATA_SLOT_384_511 | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(2) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_R_MEM_DATA_READ (0x114)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_UDATA_SLOT_0_127    | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | READ_UDATA_SLOT_128_255  | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | READ_UDATA_SLOT_256_383  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | READ_UDATA_SLOT_384_511  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(1) | BIT(2) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_R_MEM_DATA_ERASE (0x118)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ERASE_UDATA_SLOT_0_127   | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | ERASE_UDATA_SLOT_128_255 | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | ERASE_UDATA_SLOT_256_383 | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | ERASE_UDATA_SLOT_384_511 | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(1) | BIT(2) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_RANDOM_VALUE_GET (0x120)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | RANDOM_VALUE_GET         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        BIT(1) | BIT(2),
        // # CFG_UAP_ECC_KEY_GENERATE (0x130)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | GEN_ECCKEY_SLOT_0_7      | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | GEN_ECCKEY_SLOT_8_15     | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | GEN_ECCKEY_SLOT_16_23    | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | GEN_ECCKEY_SLOT_24_31    | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_ECC_KEY_STORE (0x134)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | STORE_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | STORE_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | STORE_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | STORE_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_ECC_KEY_READ (0x138)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_ECCKEY_SLOT_0_7     | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | READ_ECCKEY_SLOT_8_15    | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | READ_ECCKEY_SLOT_16_23   | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | READ_ECCKEY_SLOT_24_31   | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_ECC_KEY_ERASE (0x13c)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ERASE_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | ERASE_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | ERASE_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | ERASE_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_ECDSA_SIGN (0x140)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ECDSA_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | ECDSA_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | ECDSA_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | ECDSA_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_EDDSA_SIGN (0x144)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | EDDSA_ECCKEY_0_7         | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | EDDSA_ECCKEY_8_15        | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | EDDSA_ECCKEY_16_23       | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | EDDSA_ECCKEY_24_31       | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_MCOUNTER_INIT (0x148)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_INIT_0_3        | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | MCOUNTER_INIT_4_7        | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | MCOUNTER_INIT_8_11       | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | MCOUNTER_INIT_12_15      | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_MCOUNTER_GET (0x154)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_GET_0_3         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | MCOUNTER_GET_4_7         | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | MCOUNTER_GET_8_11        | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | MCOUNTER_GET_12_15       | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_MCOUNTER_UPDATE (0x158)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_UPDATE_0_3      | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | MCOUNTER_UPDATE_4_7      | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | MCOUNTER_UPDATE_8_11     | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | MCOUNTER_UPDATE_12_15    | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        // # CFG_UAP_MAC_AND_DESTROY (0x160)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MACANDD_0_31             | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | MACANDD_32_63            | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | MACANDD_64_95            | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | MACANDD_96_127           | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        BIT(2) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
    }};
// clang-format on

static void prodtest_tropic_get_riscv_fw_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_handle_t* tropic_handle = tropic_get_handle();

  uint8_t version[LT_L2_GET_INFO_RISCV_FW_SIZE] = {0};
  if (lt_get_info_riscv_fw_ver(tropic_handle, version) != LT_OK) {
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

  lt_handle_t* tropic_handle = tropic_get_handle();

  uint8_t version[LT_L2_GET_INFO_SPECT_FW_SIZE];
  if (lt_get_info_spect_fw_ver(tropic_handle, version) != LT_OK) {
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

  lt_handle_t* tropic_handle = tropic_get_handle();

  struct lt_chip_id_t chip_id;
  if (lt_get_info_chip_id(tropic_handle, &chip_id) != LT_OK) {
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

  const uint8_t* tropic_cert_chain = NULL;
  size_t tropic_cert_chain_length = 0;
  if (!tropic_get_cert_chain_ptr(&tropic_cert_chain,
                                 &tropic_cert_chain_length)) {
    cli_error(cli, CLI_ERROR, "`tropic_get_cert_chain_ptr()` failed");
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
      cli_ok(cli, "YES");
      break;
    case TROPIC_LOCKED_FALSE:
      cli_ok(cli, "NO");
      break;
    default:
      // Error reported by get_tropic_locked_status.
      break;
  }
}

tropic_locked_status get_tropic_locked_status(cli_t* cli) {
  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  lt_handle_t* tropic_handle = tropic_get_handle();
  lt_ret_t ret = LT_FAIL;

  curve25519_key tropic_public = {0};
  if (secret_key_tropic_public(tropic_public) != sectrue) {
    // The Tropic pairing process was not initiated.
    return TROPIC_LOCKED_FALSE;
  }

  ret = tropic_custom_session_start(TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    if (ret == LT_L2_HSK_ERR) {
      // The Tropic pairing process was initiated but probably failed midway.
      return TROPIC_LOCKED_FALSE;
    } else {
      return TROPIC_LOCKED_ERROR;
    }
  }

  struct lt_config_t configuration_read = {0};

  ret = lt_read_whole_R_config(tropic_handle, &configuration_read);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`lt_read_whole_R_config()` failed with error %d",
              ret);
    return TROPIC_LOCKED_ERROR;
  }

  if (memcmp(&reversible_configuration, (uint8_t*)&configuration_read,
             sizeof(reversible_configuration)) != 0) {
    return TROPIC_LOCKED_FALSE;
  }

  ret = lt_read_whole_I_config(tropic_handle, &configuration_read);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`lt_read_whole_I_config()` failed with error %d",
              ret);
    return TROPIC_LOCKED_ERROR;
  }

  if (memcmp(&irreversible_configuration, (uint8_t*)&configuration_read,
             sizeof(irreversible_configuration)) != 0) {
    return TROPIC_LOCKED_FALSE;
  }

  return TROPIC_LOCKED_TRUE;
}

static lt_ret_t pairing_key_write(lt_handle_t* handle, pkey_index_t slot,
                                  const ed25519_secret_key public_key) {
  // If this function returns `LT_OK`, it is ensured that the pairing key
  // `public_key` is written in the slot `slot`.
  lt_ret_t ret = lt_pairing_key_write(handle, public_key, slot);
  if (ret != LT_OK && ret != LT_L3_FAIL) {
    return ret;
  }
  // If the pairing has already been written, `lt_pairing_key_write()` returns
  // `LT_L3_FAIL`.
  curve25519_key public_key_read = {0};
  ret = lt_pairing_key_read(handle, public_key_read, slot);
  if (ret != LT_OK) {
    return ret;
  }
  if (memcmp(public_key, public_key_read, sizeof(ed25519_public_key)) != 0) {
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
  ret = tropic_custom_session_start(TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    if (cli != NULL) {
      cli_error(
          cli, CLI_ERROR,
          "`tropic_custom_session_start()` for unprivileged key failed with "
          "error %d",
          ret);
    }
    goto cleanup;
  }

  // Try to establish a session using the privileged key pair.
  ret = tropic_custom_session_start(TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    if (cli != NULL) {
      cli_error(cli, CLI_ERROR,
                "`tropic_custom_session_start()` for privileged key failed "
                "with error %d",
                ret);
    }
    goto cleanup;
  }

  // Read the factory pairing key to ensure it is invalidated.
  curve25519_key public_read = {0};
  ret = lt_pairing_key_read(tropic_handle, public_read,
                            TROPIC_FACTORY_PAIRING_KEY_SLOT);
  if (ret != LT_L3_PAIRING_KEY_INVALID) {
    if (cli != NULL) {
      cli_error(cli, CLI_ERROR,
                "`lt_pairing_key_read()` for factory pairing key failed with "
                "error %d",
                ret);
    }
    goto cleanup;
  }

  // Read the fourth pairing key to ensure it is empty.
  ret =
      lt_pairing_key_read(tropic_handle, public_read, PAIRING_KEY_SLOT_INDEX_3);
  if (ret != LT_L3_PAIRING_KEY_EMPTY) {
    if (cli != NULL) {
      cli_error(cli, CLI_ERROR,
                "`lt_pairing_key_read()` for pairing key slot 3 failed with "
                "error %d",
                ret);
    }
    goto cleanup;
  }

  is_paired = true;

cleanup:
  return is_paired;
}

static void prodtest_tropic_pair(cli_t* cli) {
  // If this functions successfully completes, it is ensured that:
  //  * The public tropic key is written to MCU's flash.
  //  * The factory pairing key in tropic's `PAIRING_KEY_SLOT_INDEX_0` is
  //  invalidated.
  //  * The unprivileged pairing key is written to tropic's
  //  `PAIRING_KEY_SLOT_INDEX_1`.
  //  * The privileged pairing key is written to tropic's
  //  `PAIRING_KEY_SLOT_INDEX_2`.
  //  * The pairing key in tropic's `PAIRING_KEY_SLOT_INDEX_3` is empty.
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

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  lt_handle_t* tropic_handle = tropic_get_handle();

  // Get the Tropic01 public pairing key from the chip's certificate.
  curve25519_key tropic_public = {0};
  if (!tropic_get_pubkey(tropic_public)) {
    cli_error(cli, CLI_ERROR, "`tropic_get_tropic_pubkey()` failed");
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
      cli_error(cli, CLI_ERROR,
                "`secret_key_set()` failed for tropic public key.");
      goto cleanup;
    }
#endif
    if (secret_key_tropic_public(tropic_public_flash) != sectrue) {
      cli_error(cli, CLI_ERROR, "`secret_key_tropic_public()` failed.");
      goto cleanup;
    }
  }
  if (memcmp(tropic_public, tropic_public_flash, sizeof(curve25519_key)) != 0) {
    cli_error(cli, CLI_ERROR,
              "Tropic public key does not match the expected value.");
    goto cleanup;
  }

  // Retrieve the unprivileged pairing key pair.
  curve25519_key unprivileged_private = {0};
  if (secret_key_tropic_pairing_unprivileged(unprivileged_private) != sectrue) {
    cli_error(cli, CLI_ERROR,
              "`secret_key_tropic_pairing_unprivileged()` failed.");
    goto cleanup;
  }
  curve25519_key unprivileged_public = {0};
  curve25519_scalarmult_basepoint(unprivileged_public, unprivileged_private);

  // Retrieve the privileged pairing key pair.
  curve25519_key privileged_private = {0};
  if (secret_key_tropic_pairing_privileged(privileged_private) != sectrue) {
    cli_error(cli, CLI_ERROR,
              "`secret_key_tropic_pairing_unprivileged()` failed.");
    goto cleanup;
  }
  curve25519_key privileged_public = {0};
  curve25519_scalarmult_basepoint(privileged_public, privileged_private);

  if (tropic_custom_session_start(TROPIC_FACTORY_PAIRING_KEY_SLOT) == LT_OK) {
    // Write the privileged pairing key to the tropic's pairing key slot if it
    // has not been written yet.
    lt_ret_t ret = pairing_key_write(
        tropic_handle, TROPIC_PRIVILEGED_PAIRING_KEY_SLOT, privileged_public);
    // If the pairing key has already been written, `pairing_key_write()`
    // returns `LT_OK`.
    if (ret != LT_OK) {
      cli_error(cli, CLI_ERROR,
                "`pairing_key_write()` failed for privileged pairing key with "
                "error %d",
                ret);
      goto cleanup;
    }

    // Write the unprivileged pairing key to the tropic's pairing key slot if it
    // has not been written yet.
    ret = pairing_key_write(tropic_handle, TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT,
                            unprivileged_public);
    // If the pairing key has already been written, `pairing_key_write()`
    // returns `LT_OK`.
    if (ret != LT_OK) {
      cli_error(
          cli, CLI_ERROR,
          "`pairing_key_write()` failed for unprivileged pairing key with "
          "error %d",
          ret);
      goto cleanup;
    }

    // Invalidate the factory pairing key if it has not been invalidated yet.
    ret = lt_pairing_key_invalidate(tropic_handle,
                                    TROPIC_FACTORY_PAIRING_KEY_SLOT);
    // If the factory has already been invalidated,
    // `lt_pairing_key_invalidate()` returns `LT_OK`.
    if (ret != LT_OK) {
      cli_error(cli, CLI_ERROR,
                "`lt_pairing_key_invalidate()` failed for factory pairing key "
                "with error %d",
                ret);
      goto cleanup;
    }
  }

  if (tropic_is_paired(cli)) {
    cli_ok(cli, "");
  }

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

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  curve25519_key unprivileged_private = {0};
  if (secret_key_tropic_pairing_unprivileged(unprivileged_private) != sectrue) {
    cli_error(cli, CLI_ERROR,
              "`secret_key_tropic_pairing_unprivileged()` failed.");
    goto cleanup;
  }

  curve25519_key tropic_public = {0};
  if (!tropic_get_pubkey(tropic_public)) {
    cli_error(cli, CLI_ERROR, "`tropic_get_tropic_pubkey()` failed");
  }

  uint8_t output[sizeof(unprivileged_private) + NOISE_TAG_SIZE] = {0};
  if (!secure_channel_encrypt((uint8_t*)unprivileged_private,
                              sizeof(unprivileged_private), tropic_public,
                              sizeof(curve25519_key), output)) {
    // `secure_channel_handshake_2()` might not have been called
    cli_error(cli, CLI_ERROR, "`secure_channel_encrypt()` failed.");
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
    cli_error(cli, CLI_ERROR, "`secret_key_tropic_masking()` failed.");
    goto cleanup;
  }

  uint8_t output[sizeof(fido_masking_key) + NOISE_TAG_SIZE] = {0};
  if (!secure_channel_encrypt(fido_masking_key, sizeof(fido_masking_key), NULL,
                              0, output)) {
    // `secure_channel_handshake_2()` might not have been called
    cli_error(cli, CLI_ERROR, "`secure_channel_encrypt()` failed.");
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

  if (!tropic_is_paired(NULL)) {
    cli_error(cli, CLI_ERROR, "`tropic-pair` must be called first.");
    return;
  }

  uint8_t input[35] = {0};  // 35 is the expected size of the handshake request
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

  lt_ret_t ret = LT_FAIL;
  lt_l2_state_t l2_state = tropic_get_handle()->l2;

  size_t request_length = 0;
  ret = l2_get_req_len(input, sizeof(input), &request_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`get_req_len()` failed with error %d.", ret);
    return;
  }

  if (input_length != request_length) {
    cli_error(cli, CLI_ERROR, "Request was damaged or truncated.");
    return;
  }

  memcpy(&l2_state.buff, input, request_length);

  ret = tropic_session_invalidate();
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "`tropic_session_invalidate()` failed with error %d.", ret);
    return;
  }

  ret = lt_l2_send(&l2_state);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`lt_l2_send()` failed with error %d.", ret);
    return;
  }

  ret = lt_l2_receive(&l2_state);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`lt_l2_receive()` failed with error %d.", ret);
    return;
  }

  size_t response_length = 0;
  ret = l2_get_rsp_len(l2_state.buff, sizeof(l2_state.buff), &response_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`get_rsp_len()` failed with error %d.", ret);
    return;
  }

  if (response_length !=
      51) {  // 51 is the expected size of the handshake response
    cli_error(cli, CLI_ERROR,
              "Unexpected response length. Expecting 51 bytes, got %d bytes.",
              (int)response_length);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_1;

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

  uint8_t input[L2_MAX_FRAME_SIZE] = {0};
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

  lt_ret_t ret = LT_FAIL;
  lt_l2_state_t l2_state = tropic_get_handle()->l2;

  size_t command_length = 0;
  ret = l3_get_frame_len(input, sizeof(input), &command_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`l3_get_cmd_len()` failed with error %d.", ret);
    return;
  }

  if (input_length != command_length) {
    cli_error(cli, CLI_ERROR, "Request was damaged or truncated.");
    return;
  }

  ret = lt_l2_send_encrypted_cmd(&l2_state, (uint8_t*)input, input_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "`lt_l2_send_encrypted_cmd()` failed with error %d.", ret);
    return;
  }

  uint8_t output[L2_MAX_FRAME_SIZE] = {0};
  ret = lt_l2_recv_encrypted_res(&l2_state, output, sizeof(output));
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "`lt_l2_recv_encrypted_res()` failed with error %d.", ret);
    return;
  }

  size_t output_length = 0;
  ret = l3_get_frame_len(output, sizeof(output), &output_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`l3_get_cmd_len()` failed with error %d.", ret);
    return;
  }

  cli_ok_hexdata(cli, output, output_length);
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

  if (!tropic_is_paired(NULL)) {
    cli_error(cli, CLI_ERROR, "`tropic-pair` must be called first.");
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;
  lt_ret_t ret = LT_FAIL;

  ret = tropic_custom_session_start(TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "`tropic_custom_session_start()` for privileged key failed with "
              "error %d",
              ret);
    return;
  }

  struct lt_config_t configuration_read = {0};
  lt_handle_t* tropic_handle = tropic_get_handle();

  ret = lt_r_config_erase(tropic_handle);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`lt_r_config_erase()` failed with error %d",
              ret);
    return;
  }

  ret = lt_write_whole_R_config(tropic_handle, &reversible_configuration);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "`lt_write_whole_R_config()` failed with error %d", ret);
    return;
  }

  ret = lt_read_whole_R_config(tropic_handle, &configuration_read);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`lt_read_whole_R_config()` failed with error %d",
              ret);
    return;
  }

  if (memcmp(&reversible_configuration, (uint8_t*)&configuration_read,
             sizeof(reversible_configuration)) != 0) {
    cli_error(cli, CLI_ERROR, "Reversible configuration mismatch after write.");
    return;
  }

  ret = lt_write_whole_I_config(tropic_handle, &irreversible_configuration);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "`lt_write_whole_I_config()` failed with error %d", ret);
    return;
  }

  ret = lt_read_whole_I_config(tropic_handle, &configuration_read);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "`lt_read_whole_I_config()` failed with error %d",
              ret);
    return;
  }

  if (memcmp(&irreversible_configuration, (uint8_t*)&configuration_read,
             sizeof(irreversible_configuration)) != 0) {
    cli_error(cli, CLI_ERROR,
              "Irreversible configuration mismatch after write.");
    return;
  }

  cli_ok(cli, "");
}

static lt_ret_t data_write(lt_handle_t* h, uint16_t first_slot,
                           uint16_t slots_count, uint8_t* data,
                           size_t data_length) {
  const uint16_t last_data_slot = first_slot + slots_count - 1;
  if (slots_count == 0 || last_data_slot > R_MEM_DATA_SLOT_MAX) {
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
    lt_ret_t ret = LT_FAIL;

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

static lt_ret_t data_read(lt_handle_t* h, uint16_t first_slot,
                          uint16_t slots_count, uint8_t* data,
                          size_t max_data_length, size_t* data_length) {
  const uint16_t last_data_slot = first_slot + slots_count - 1;
  if (slots_count == 0 || last_data_slot > R_MEM_DATA_SLOT_MAX) {
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
    uint16_t slot_length = 0;
    lt_ret_t ret =
        lt_r_mem_data_read(h, slot, prefixed_data + position, &slot_length);
    if (ret != LT_OK) {
      return ret;
    }

    if (slot_length != R_MEM_DATA_SIZE_MAX) {
      return LT_FAIL;
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

static bool check_device_cert_chain(cli_t* cli, const uint8_t* chain,
                                    size_t chain_size) {
  uint8_t challenge[CHALLENGE_SIZE] = {
      0};  // The challenge is intentionally constant zero.

  ed25519_signature signature = {0};

  if (lt_ecc_eddsa_sign(tropic_get_handle(), TROPIC_DEVICE_KEY_SLOT, challenge,
                        sizeof(challenge), signature) != LT_OK) {
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
  uint8_t certificate[R_MEM_DATA_SIZE_MAX * slots_count];
  if (!cli_arg_hex(cli, "hex-data", certificate, sizeof(certificate),
                   &certificate_length)) {
    if (certificate_length == sizeof(certificate)) {
      cli_error(cli, CLI_ERROR, "Certificate too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  lt_ret_t ret =
      tropic_custom_session_start(TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "`tropic_custom_session_start()` for privileged key failed with "
              "error %d",
              ret);
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
    cli_error(cli, CLI_ERROR, "Unable to write certificate");
    return;
  }

  size_t certificate_read_length = 0;
  uint8_t certificate_read[R_MEM_DATA_SIZE_MAX * slots_count];
  ret = data_read(tropic_handle, first_slot, slots_count, certificate_read,
                  sizeof(certificate_read), &certificate_read_length);
  if (ret != LT_OK || certificate_read_length != certificate_length ||
      memcmp(certificate, certificate_read, certificate_length) != 0) {
    cli_error(cli, CLI_ERROR, "Unable to read certificate");
    return;
  }

  cli_ok(cli, "");
}

static void cert_read(cli_t* cli, uint16_t first_slot, uint16_t slots_count) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;
  lt_ret_t ret = LT_FAIL;

  ret = tropic_custom_session_start(TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "`tropic_custom_session_start()` for privileged key failed with "
              "error %d",
              ret);
    return;
  }

  uint8_t certificate[R_MEM_DATA_SIZE_MAX * slots_count];
  size_t certificate_length = 0;
  ret = data_read(tropic_get_handle(), first_slot, slots_count, certificate,
                  sizeof(certificate), &certificate_length);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "Unable to read certificate");
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

static void pubkey_read(cli_t* cli, ecc_slot_t slot,
                        const uint8_t masking_key[ECDSA_PRIVATE_KEY_SIZE]) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_ret_t ret = LT_FAIL;

  ret = tropic_custom_session_start(TROPIC_PRIVILEGED_PAIRING_KEY_SLOT);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR,
              "`tropic_custom_session_start()` for privileged key failed with "
              "error %d",
              ret);
    return;
  }

  uint8_t public_key[ECDSA_PUBLIC_KEY_SIZE] = {0x04};
  lt_ecc_curve_type_t curve_type = 0;
  ecc_key_origin_t origin = 0;
  ret = lt_ecc_key_read(tropic_get_handle(), slot, &public_key[1], &curve_type,
                        &origin);
  if (ret != LT_OK || curve_type != CURVE_P256) {
    cli_error(cli, CLI_ERROR, "lt_ecc_key_read error %d.", ret);
    return;
  }

  if (masking_key != NULL) {
    if (ecdsa_unmask_public_key(&nist256p1, masking_key, public_key,
                                public_key) != 0) {
      cli_error(cli, CLI_ERROR, "key unmasking error");
      return;
    }
  }

  cli_ok_hexdata(cli, public_key, sizeof(public_key));
}

static void prodtest_tropic_keyfido_read(cli_t* cli) {
#ifdef SECRET_KEY_MASKING
  uint8_t masking_key[ECDSA_PRIVATE_KEY_SIZE] = {0};
  if (secret_key_tropic_masking(masking_key) != sectrue) {
    cli_error(cli, CLI_ERROR, "masking key not available");
    return;
  }
  pubkey_read(cli, TROPIC_FIDO_KEY_SLOT, masking_key);
  memzero(masking_key, sizeof(masking_key));
#else
  pubkey_read(cli, TROPIC_FIDO_KEY_SLOT, NULL);
#endif  // SECRET_KEY_MASKING
}

static void prodtest_tropic_update_fw(cli_t* cli) {
#define FW_APP_UPDATE_BANK FW_BANK_FW1
#define FW_SPECT_UPDATE_BANK FW_BANK_SPECT1

  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  lt_handle_t* h = tropic_get_handle();

  lt_chip_id_t chip_id = {0};
  if (lt_get_info_chip_id(h, &chip_id) != LT_OK) {
    cli_error(cli, CLI_ERROR, "Unable to get CHIP ID");
    return;
  }

  cli_trace(cli, "Silicon revision: %c%c%c%c", chip_id.silicon_rev[0],
            chip_id.silicon_rev[1], chip_id.silicon_rev[2],
            chip_id.silicon_rev[3]);

#ifdef ABAB
  if (strncmp((char*)chip_id.silicon_rev, "ABAB", 4) != 0) {
    cli_error(cli, CLI_ERROR, "Wrong tropic chip silicon revision");
    return;
  }
#else
  cli_error(cli, CLI_ERROR, "Tropic chip silicon revision not set");
  return;
#endif

  // For firmware update chip must be rebooted into MAINTENANCE mode.
  cli_trace(cli, "Rebooting into Maintenance mode");
  lt_ret_t ret = lt_reboot(h, LT_MODE_MAINTENANCE);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "lt_reboot() failed, ret=%s",
              lt_ret_verbose(ret));
    return;
  }

  if (h->l2.mode != LT_MODE_MAINTENANCE) {
    cli_error(cli, CLI_ERROR, "Chip couldn't get into MAINTENANCE mode");
    return;
  }

  cli_trace(cli, "Chip is executing bootloader");

  cli_trace(cli, "Updating RISC-V FW");
  ret = lt_do_mutable_fw_update(h, fw_CPU, sizeof(fw_CPU), FW_APP_UPDATE_BANK);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "RISC-V FW update failed, ret=%s",
              lt_ret_verbose(ret));
    goto cleanup;
  }

  cli_trace(cli, "Updating SPECT FW");
  ret = lt_do_mutable_fw_update(h, fw_SPECT, sizeof(fw_SPECT),
                                FW_SPECT_UPDATE_BANK);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "SPECT FW update failed, ret=%s",
              lt_ret_verbose(ret));
    goto cleanup;
  }

  // To read firmware versions chip must be rebooted into application mode.
  cli_trace(cli, "Rebooting into Application mode");
  ret = lt_reboot(h, LT_MODE_APP);
  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "lt_reboot() failed, ret=%s",
              lt_ret_verbose(ret));
    goto cleanup;
  }

  if (h->l2.mode != LT_MODE_APP) {
    cli_error(cli, CLI_ERROR,
              "Device couldn't get into APP mode, APP and SPECT firmwares in "
              "fw banks are not valid or banks are empty");
    goto cleanup;
  }

  cli_trace(cli, "Reading RISC-V FW version");

  uint8_t risc_fw_ver[LT_L2_GET_INFO_RISCV_FW_SIZE] = {0};
  ret = lt_get_info_riscv_fw_ver(h, risc_fw_ver);

  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "Failed to get RISC-V FW version, ret=%s",
              lt_ret_verbose(ret));
    goto cleanup;
  }

  cli_trace(cli,
            "Chip is executing RISC-V application FW version: %d.%d.%d (+ .%d)",
            risc_fw_ver[3], risc_fw_ver[2], risc_fw_ver[1], risc_fw_ver[0]);

  cli_trace(cli, "Reading SPECT FW version");
  uint8_t spect_fw_ver[LT_L2_GET_INFO_SPECT_FW_SIZE] = {0};
  ret = lt_get_info_spect_fw_ver(h, spect_fw_ver);

  if (ret != LT_OK) {
    cli_error(cli, CLI_ERROR, "Failed to get SPECT FW version, ret=%s",
              lt_ret_verbose(ret));
    goto cleanup;
  }

  cli_trace(cli, "Chip is executing SPECT FW version: %d.%d.%d (+ .%d)",
            spect_fw_ver[3], spect_fw_ver[2], spect_fw_ver[1], spect_fw_ver[0]);

  cli_ok(cli, "");

  return;

cleanup:
  tropic_deinit();
}

static void prodtest_tropic_stress_test(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  tropic_handshake_state = TROPIC_HANDSHAKE_STATE_0;

  lt_ret_t res = LT_FAIL;
  pkey_index_t pairing_key_index = -1;

  // Find which pairing key is available
  for (pkey_index_t i = TROPIC_FACTORY_PAIRING_KEY_SLOT;
       i <= TROPIC_PRIVILEGED_PAIRING_KEY_SLOT; i++) {
    res = tropic_custom_session_start(i);
    if (res == LT_OK) {
      pairing_key_index = i;
      break;
    }
    if (res != LT_L2_HSK_ERR) {
      cli_error(
          cli, CLI_ERROR,
          "`tropic_custom_session_start() for key %d failed with error %d", i,
          res);
      return;
    }
  }

  if (pairing_key_index == -1) {
    cli_error(cli, CLI_ERROR, "No pairing key is available");
    return;
  }

  // Test `lt_session_start`
  for (int i = 0; i < 10; i++) {
    res = tropic_session_invalidate();
    if (res != LT_OK) {
      cli_error(
          cli, CLI_ERROR,
          "`%d. repetition of tropic_session_invalidate() failed with error %d",
          i + 1, res);
      return;
    }
    res = tropic_custom_session_start(pairing_key_index);
    if (res != LT_OK) {
      cli_error(cli, CLI_ERROR,
                "%d. repetition of `tropic_custom_session_start() for key %d "
                "failed with error %d",
                i + 1, pairing_key_index, res);
      return;
    }
  }

  // Test `lt_mac_and_destroy`
  for (int slot_index = TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT;
       slot_index < TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT +
                        TROPIC_MAC_AND_DESTROY_SLOTS_COUNT;
       slot_index++) {
    for (int i = 0; i < 3; i++) {
      uint8_t buffer[TROPIC_MAC_AND_DESTROY_SIZE] = {0};
      rng_fill_buffer(buffer, sizeof(buffer));
      res = lt_mac_and_destroy(tropic_get_handle(), slot_index, buffer, buffer);
      if (res != LT_OK) {
        cli_error(cli, CLI_ERROR,
                  "%d. repetition of `lt_mac_and_destroy()` for slot %d failed "
                  "with error %d",
                  i + 1, slot_index, res);
        return;
      }
    }
  }

  // Test `lt_ecc_key_generate`
  uint8_t message[32] = {0};
  ed25519_signature signature = {0};
  ecc_slot_t ecc_slot = ECC_SLOT_31;
  res = lt_ecc_key_generate(tropic_get_handle(), ecc_slot, CURVE_ED25519);
  if (res != LT_OK) {
    cli_error(cli, CLI_ERROR, "`lt_ecc_key_generate()` failed with error %d",
              res);
    return;
  }
  for (int i = 0; i < 10; i++) {
    rng_fill_buffer(message, sizeof(message));
    res = lt_ecc_eddsa_sign(tropic_get_handle(), ecc_slot, message,
                            sizeof(message), signature);
    if (res != LT_OK) {
      cli_error(cli, CLI_ERROR,
                "%d. repetition of `lt_ecc_eddsa_sign()` failed with error %d",
                i + 1, res);
      lt_ecc_key_erase(tropic_get_handle(), ecc_slot);
      return;
    }
  }
  res = lt_ecc_key_erase(tropic_get_handle(), ecc_slot);
  if (res != LT_OK) {
    cli_error(cli, CLI_ERROR, "`lt_ecc_key_erase()` failed with error %d", res);
    return;
  }

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
  .name = "tropic-stress-test",
  .func = prodtest_tropic_stress_test,
  .info = "Run stress test for Tropic",
  .args = ""
);

#endif
