// generated from `tropic_configs.json` by `tropic_configs.c.mako`
// (by running `make templates` in `core`)
// Do not edit manually!

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

#include <sec/tropic_configs.h>
<%
def all_except(selected_bits: list[int]) -> str:
    result = 0xFFFFFFFF
    for bit in selected_bits:
        result &= ~(1 << bit)
    return f"0x{result:08X}U,"

def bits(selected_bits: list[int]) -> str:
    result = 0
    for bit in selected_bits:
        result |= (1 << bit)
    return f"0x{result:08X}U," if result != 0 else "0,"

def uap_all_except(configs, category):
    selected_bits = []
    config = configs["config"]
    for key in range(4):
        for details in config[category]['setting'][f'pairing_key_{key}'].values():
            if not details['value']:
                selected_bits.append(details['bit'])
    return all_except(selected_bits)

def uap_bits(configs, category):
    selected_bits = []
    config = configs["config"]
    for key in range(4):
        for details in config[category]['setting'][f'pairing_key_{key}'].values():
            if details['value']:
                selected_bits.append(details['bit'])
    return bits(selected_bits)

import json
in_filename = ROOT / "core" / "embed" / "sec" / "tropic" / "config" / "tropic_configs.json"
with open(in_filename, "r") as f:
    configs = json.load(f)
reversible_configs = configs["reversible_configurations"]
irreversible_configs = configs["irreversible_configurations"]
i_names = [category for category in irreversible_configs[0]['config'].keys() if not('uap' in category)]
r_names = [category for category in reversible_configs[0]['config'].keys() if not('uap' in category)]

i_uap_names = [category for category in irreversible_configs[0]['config'].keys() if 'uap' in category]
r_uap_names = [category for category in reversible_configs[0]['config'].keys() if 'uap' in category]

# Verify that category addresses are strictly ascending in every version.
# The count against LT_CONFIG_OBJ_CNT is checked at C compile time via #if below.
for _cfg_name, _cfg_list in [("irreversible", irreversible_configs), ("reversible", reversible_configs)]:
    for _cfg_version in _cfg_list:
        _prev_addr = -1
        for _cat, _cat_data in _cfg_version['config'].items():
            _addr = int(_cat_data['address'], 16)
            if _addr <= _prev_addr:
                raise ValueError(
                    f"{_cfg_name} config v{_cfg_version['version']}: "
                    f"category '{_cat}' at address {hex(_addr)} is not in strictly "
                    "ascending order — categories must match TROPIC_CONFIG_ADDRS ordering"
                )
            _prev_addr = _addr

_i_obj_cnt = len(irreversible_configs[0]['config'])
_r_obj_cnt = len(reversible_configs[0]['config'])

%>
// See the documentation of Tropic configurations in
// `docs/core/misc/tropic_configs.md` for more details.

// clang-format off
// Count check: the compiler resolves LT_CONFIG_OBJ_CNT; the numbers on the left
// are computed from tropic_configs.json at template generation time.
// This catches a missing category in the JSON (too-few silently zero-fills in
// C).
#if ${_i_obj_cnt} != LT_CONFIG_OBJ_CNT
#error "irreversible_configurations category count in tropic_configs.json does not match LT_CONFIG_OBJ_CNT"
#endif
#if ${_r_obj_cnt} != LT_CONFIG_OBJ_CNT
#error "reversible_configurations category count in tropic_configs.json does not match LT_CONFIG_OBJ_CNT"
#endif

const tropic_versioned_config_t tropic_irreversible_configs[] = {
% for cfg_version in irreversible_configs:
    {
        .version = ${cfg_version["version"]},
        .config = {
            .obj = {
% for category in i_names:
                ${all_except([c['bit'] for c in cfg_version["config"][category]["setting"].values() if not(c['value'])])}
% endfor
% for category in i_uap_names:
                ${uap_all_except(cfg_version, category)}
% endfor
            }
        },
    },
% endfor
};

const tropic_versioned_config_t tropic_reversible_configs[] = {
% for cfg_version in reversible_configs:
    {
        .version = ${cfg_version["version"]},
        .config = {
            .obj = {
% for category in r_names:
                ${bits([c['bit'] for c in cfg_version["config"][category]["setting"].values() if c['value']])}
% endfor
% for category in r_uap_names:
                ${uap_bits(cfg_version, category)}
% endfor
            }
        },
    },
% endfor
};

// TODO: This is hardcoded for now. We should generate it from a JSON file in the future.

const tropic_config_distribution_t tropic_config_distributions[] = {
    {
        .distribution_version = 0,
        .min_reversible_version = 0,
        .max_reversible_version = 1,
        .irreversible_version = 0,
    },
    {
        .distribution_version = 1,
        .min_reversible_version = 1,
        .max_reversible_version = 1,
        .irreversible_version = 1,
    },
};

const uint32_t tropic_prodtest_config_distribution_version = 0;

// clang-format on

const size_t tropic_reversible_config_count =
    sizeof(tropic_reversible_configs) / sizeof(tropic_reversible_configs[0]);

const size_t tropic_irreversible_config_count =
    sizeof(tropic_irreversible_configs) /
    sizeof(tropic_irreversible_configs[0]);

const size_t tropic_config_distribution_count =
    sizeof(tropic_config_distributions) /
    sizeof(tropic_config_distributions[0]);
