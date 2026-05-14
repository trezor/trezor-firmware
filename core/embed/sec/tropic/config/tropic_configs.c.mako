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

#include <libtropic.h>
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
    config = configs["irreversible_configuration"]
    for key in range(4):
        for details in config[category]['setting'][f'pairing_key_{key}'].values():
            if not details['value']:
                selected_bits.append(details['bit'])
    return all_except(selected_bits)

def uap_bits(configs, category):
    selected_bits = []
    config = configs["reversible_configuration"]
    for key in range(4):
        for details in config[category]['setting'][f'pairing_key_{key}'].values():
            if details['value']:
                selected_bits.append(details['bit'])
    return bits(selected_bits)

import json
in_filename = ROOT / "core" / "embed" / "sec" / "tropic" / "config" / "tropic_configs.json"
with open(in_filename, "r") as f:
    configs = json.load(f)
reversible_config = configs["reversible_configuration"]
irreversible_config = configs["irreversible_configuration"]
i_names = [category for category in irreversible_config.keys() if not('uap' in category)]
r_names = [category for category in reversible_config.keys() if not('uap' in category)]

i_uap_names = [category for category in irreversible_config.keys() if 'uap' in category]
r_uap_names = [category for category in reversible_config.keys() if 'uap' in category]

%>
// See the documentation of Tropic configurations in
// `docs/core/misc/tropic_configs.md` for more details.

// clang-format off
const struct lt_config_t tropic_configs_irreversible = {
    .obj = {
% for category in i_names:
        ${all_except([c['bit'] for c in irreversible_config[category]["setting"].values() if not(c['value'])])}
% endfor
% for category in i_uap_names:
        ${uap_all_except(configs, category)}
%endfor
    }
};

const struct lt_config_t tropic_configs_reversible = {
    .obj = {
% for category in r_names:
        ${bits([c['bit'] for c in reversible_config[category]["setting"].values() if c['value']])}
% endfor
% for category in r_uap_names:
        ${uap_bits(configs, category)}
%endfor
    }
};
// clang-format on
