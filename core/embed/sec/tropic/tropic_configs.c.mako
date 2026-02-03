// generated from header_maker.py.mako
// (by running `make templates` in `core`)
// do not edit manually!

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

#include <libtropic.h>
<%
class Counter:
    def __init__(self):
        self.i = 0
        self.r = 0

def all_except(selected_bits: list[int], counter: Counter) -> str:
    counter.i += 1
    if len(selected_bits) == 0:
        return "~0U,"
    else:
        return f"~0U & " + " & ".join(f"~BIT({b})" for b in selected_bits) + ","

def bits(selceted_bits: list[int], counter: Counter) -> str:
    counter.r += 1
    if len(selceted_bits) == 0:
        return "0,"
    else:
        return " | ".join(f"BIT({b})" for b in selceted_bits) + ","

import json
in_filename = ROOT / "core" / "embed" / "sec" / "tropic" / "tropic_configs.json"
with open(in_filename, "r") as f:
    configs = json.load(f)
reversible_config = configs["reversible_configuration"]
irreversible_config = configs["irreversible_configuration"]
i_names = list(irreversible_config.keys())
r_names = list(reversible_config.keys())

counter = Counter()
%>
// TODO: Adjust the configuration to match the revision of the provisioned
// tropics.
// clang-format off
const struct lt_config_t g_irreversible_configuration = {
    .obj = {
        // # ${i_names[counter.i].upper()} (0x00)
        // | Setting                 | Value                   |
        // |-------------------------|-------------------------|
        // | RFU_1 (bit 0)           | 1                       |
        // | MBIST_DIS (bit 1)       | 0 (TEST_ON)             |
        // | RNGTEST_DIS (bit 2)     | 0 (TEST_ON)             |
        // | MAINTENANCE_ENA (bit 3) | 1 (MAINTENANCE_ALLOWED) |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x08)
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
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x10)
        // | Setting           | Value |
        // |-------------------|-------|
        // | FW_LOG_EN (bit 0) | 0     |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x14)
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x18)
        // | Setting               | Value |
        // |-----------------------|-------|
        // | SLEEP_MODE_EN (bit 0) | 1     |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x20)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | WRITE_PKEY_SLOT_0        | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | WRITE_PKEY_SLOT_1        | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | WRITE_PKEY_SLOT_2        | 0 (bit 16)    | 0 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | WRITE_PKEY_SLOT_3        | 0 (bit 24)    | 0 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x24)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_PKEY_SLOT_0         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | READ_PKEY_SLOT_1         | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | READ_PKEY_SLOT_2         | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | READ_PKEY_SLOT_3         | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x28)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | INVALIDATE_PKEY_SLOT_0   |   0 (bit 0)   |   1 (bit 1)   |   1 (bit 2)   |   1 (bit 3)   |
        // | INVALIDATE_PKEY_SLOT_1   |   0 (bit 8)   |   1 (bit 9)   |   1 (bit 10)  |   1 (bit 11)  |
        // | INVALIDATE_PKEY_SLOT_2   |   0 (bit 16)  |   1 (bit 17)  |   1 (bit 18)  |   1 (bit 19)  |
        // | INVALIDATE_PKEY_SLOT_3   |   0 (bit 24)  |   1 (bit 25)  |   1 (bit 26)  |   1 (bit 27)  |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x30)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | R_CONFIG_WRITE_ERASE     | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x34)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | R_CONFIG_READ_CFG        | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | R_CONFIG_READ_FUNC       | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x40)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | I_CONFIG_WRITE_CFG       | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | I_CONFIG_WRITE_FUNC      | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x44)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | I_CONFIG_READ_CFG        | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | I_CONFIG_READ_FUNC       | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x100)
        // | Setting | Pairing Key 0  | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |---------|----------------|---------------|---------------|---------------|
        // | PING    | 0 (bit 0)      | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x110)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | WRITE_UDATA_SLOT_0_127   | 0 (bit 0)   | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | WRITE_UDATA_SLOT_128_255 | 0 (bit 8)   | 0 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | WRITE_UDATA_SLOT_256_383 | 0 (bit 16)  | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | WRITE_UDATA_SLOT_384_511 | 0 (bit 24)  | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x114)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_UDATA_SLOT_0_127    | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | READ_UDATA_SLOT_128_255  | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | READ_UDATA_SLOT_256_383  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | READ_UDATA_SLOT_384_511  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x118)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ERASE_UDATA_SLOT_0_127   | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | ERASE_UDATA_SLOT_128_255 | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | ERASE_UDATA_SLOT_256_383 | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | ERASE_UDATA_SLOT_384_511 | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x120)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | RANDOM_VALUE_GET         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x130)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | GEN_ECCKEY_SLOT_0_7      | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | GEN_ECCKEY_SLOT_8_15     | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | GEN_ECCKEY_SLOT_16_23    | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | GEN_ECCKEY_SLOT_24_31    | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x134)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | STORE_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | STORE_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | STORE_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | STORE_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x138)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_ECCKEY_SLOT_0_7     | 0 (bit 0)    | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | READ_ECCKEY_SLOT_8_15    | 0 (bit 8)    | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | READ_ECCKEY_SLOT_16_23   | 0 (bit 16)   | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | READ_ECCKEY_SLOT_24_31   | 0 (bit 24)   | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x13c)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ERASE_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | ERASE_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | ERASE_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | ERASE_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x140)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ECDSA_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | ECDSA_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | ECDSA_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | ECDSA_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x144)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | EDDSA_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | EDDSA_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | EDDSA_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | EDDSA_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x150)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_INIT_0_3        | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | MCOUNTER_INIT_4_7        | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | MCOUNTER_INIT_8_11       | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | MCOUNTER_INIT_12_15      | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x154)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_GET_0_3         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | MCOUNTER_GET_4_7         | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | MCOUNTER_GET_8_11        | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | MCOUNTER_GET_12_15       | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x158)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_UPDATE_0_3      | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | MCOUNTER_UPDATE_4_7      | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | MCOUNTER_UPDATE_8_11     | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | MCOUNTER_UPDATE_12_15    | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
        // # ${i_names[counter.i].upper()} (0x160)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MACANDD_0_31             | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 1 (bit 3)     |
        // | MACANDD_32_63            | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 1 (bit 11)    |
        // | MACANDD_64_95            | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 1 (bit 19)    |
        // | MACANDD_96_127           | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 1 (bit 27)    |
        ${all_except(irreversible_config[i_names[counter.i]]["all_except"], counter)}
    }};

// TODO: Adjust the configuration to match the revision of the provisioned
// tropics.
const struct lt_config_t g_reversible_configuration = {
    .obj = {
        // # ${r_names[counter.r].upper()} (0x00)
        // | Setting                 | Value                   |
        // |-------------------------|-------------------------|
        // | RFU_1 (bit 0)           | 1                       |
        // | MBIST_DIS (bit 1)       | 0 (TEST_ON)             |
        // | RNGTEST_DIS (bit 2)     | 0 (TEST_ON)             |
        // | MAINTENANCE_ENA (bit 3) | 1 (MAINTENANCE_ALLOWED) |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x08)
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
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x10)
        // | Setting           | Value |
        // |-------------------|-------|
        // | FW_LOG_EN (bit 0) | 0     |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x14)
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x18)
        // | Setting               | Value |
        // |-----------------------|-------|
        // | SLEEP_MODE_EN (bit 0) | 1     |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x20)
        // | Target                   | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | WRITE_PKEY_SLOT_0        | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | WRITE_PKEY_SLOT_1        | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | WRITE_PKEY_SLOT_2        | 0 (bit 16)    | 0 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | WRITE_PKEY_SLOT_3        | 0 (bit 24)    | 0 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x24)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_PKEY_SLOT_0         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | READ_PKEY_SLOT_1         | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | READ_PKEY_SLOT_2         | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | READ_PKEY_SLOT_3         | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x28)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | INVALIDATE_PKEY_SLOT_0   |   0 (bit 0)   |   1 (bit 1)   |   1 (bit 2)   |   0 (bit 3)   |
        // | INVALIDATE_PKEY_SLOT_1   |   0 (bit 8)   |   1 (bit 9)   |   1 (bit 10)  |   0 (bit 11)  |
        // | INVALIDATE_PKEY_SLOT_2   |   0 (bit 16)  |   1 (bit 17)  |   1 (bit 18)  |   0 (bit 19)  |
        // | INVALIDATE_PKEY_SLOT_3   |   0 (bit 24)  |   1 (bit 25)  |   1 (bit 26)  |   0 (bit 27)  |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x30)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | R_CONFIG_WRITE_ERASE     | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x34)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | R_CONFIG_READ_CFG        | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | R_CONFIG_READ_FUNC       | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x40)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | I_CONFIG_WRITE_CFG       | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | I_CONFIG_WRITE_FUNC      | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x44)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | I_CONFIG_READ_CFG        | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | I_CONFIG_READ_FUNC       | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x100)
        // | Setting | Pairing Key 0  | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |---------|----------------|---------------|---------------|---------------|
        // | PING    | 0 (bit 0)      | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x110)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | WRITE_UDATA_SLOT_0_127   | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | WRITE_UDATA_SLOT_128_255 | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | WRITE_UDATA_SLOT_256_383 | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | WRITE_UDATA_SLOT_384_511 | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x114)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_UDATA_SLOT_0_127    | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | READ_UDATA_SLOT_128_255  | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | READ_UDATA_SLOT_256_383  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | READ_UDATA_SLOT_384_511  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x118)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ERASE_UDATA_SLOT_0_127   | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | ERASE_UDATA_SLOT_128_255 | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | ERASE_UDATA_SLOT_256_383 | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | ERASE_UDATA_SLOT_384_511 | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x120)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | RANDOM_VALUE_GET         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x130)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | GEN_ECCKEY_SLOT_0_7      | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | GEN_ECCKEY_SLOT_8_15     | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | GEN_ECCKEY_SLOT_16_23    | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | GEN_ECCKEY_SLOT_24_31    | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x134)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | STORE_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | STORE_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | STORE_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | STORE_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x138)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | READ_ECCKEY_SLOT_0_7     | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | READ_ECCKEY_SLOT_8_15    | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | READ_ECCKEY_SLOT_16_23   | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | READ_ECCKEY_SLOT_24_31   | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x13c)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ERASE_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | ERASE_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | ERASE_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | ERASE_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x140)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | ECDSA_ECCKEY_SLOT_0_7    | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | ECDSA_ECCKEY_SLOT_8_15   | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | ECDSA_ECCKEY_SLOT_16_23  | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | ECDSA_ECCKEY_SLOT_24_31  | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x144)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | EDDSA_ECCKEY_0_7         | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | EDDSA_ECCKEY_8_15        | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | EDDSA_ECCKEY_16_23       | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | EDDSA_ECCKEY_24_31       | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x148)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_INIT_0_3        | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | MCOUNTER_INIT_4_7        | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | MCOUNTER_INIT_8_11       | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | MCOUNTER_INIT_12_15      | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x154)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_GET_0_3         | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | MCOUNTER_GET_4_7         | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | MCOUNTER_GET_8_11        | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | MCOUNTER_GET_12_15       | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x158)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MCOUNTER_UPDATE_0_3      | 0 (bit 0)     | 1 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | MCOUNTER_UPDATE_4_7      | 0 (bit 8)     | 1 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | MCOUNTER_UPDATE_8_11     | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | MCOUNTER_UPDATE_12_15    | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
        // # ${r_names[counter.r].upper()} (0x160)
        // | Setting                  | Pairing Key 0 | Pairing Key 1 | Pairing Key 2 | Pairing Key 3 |
        // |--------------------------|---------------|---------------|---------------|---------------|
        // | MACANDD_0_31             | 0 (bit 0)     | 0 (bit 1)     | 1 (bit 2)     | 0 (bit 3)     |
        // | MACANDD_32_63            | 0 (bit 8)     | 0 (bit 9)     | 1 (bit 10)    | 0 (bit 11)    |
        // | MACANDD_64_95            | 0 (bit 16)    | 1 (bit 17)    | 1 (bit 18)    | 0 (bit 19)    |
        // | MACANDD_96_127           | 0 (bit 24)    | 1 (bit 25)    | 1 (bit 26)    | 0 (bit 27)    |
        ${bits(reversible_config[r_names[counter.r]]["bits"], counter)}
    }};
// clang-format on
