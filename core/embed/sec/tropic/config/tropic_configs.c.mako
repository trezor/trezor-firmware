// generated from `tropic_configs.json` by `tropic_configs.c.mako`
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
def all_except(selected_bits: list[int]) -> str:
    if len(selected_bits) == 0:
        return "~0U,"
    else:
        return f"~0U & " + " & ".join(f"~BIT({b})" for b in sorted(selected_bits)) + ","

def bits(selected_bits: list[int]) -> str:
    if len(selected_bits) == 0:
        return "0,"
    else:
        return " | ".join(f"BIT({b})" for b in sorted(selected_bits)) + ","

def get_uap_all_except(configs, category):
    selected_bits = []
    config = configs["irreversible_configuration"]
    for key in range(4):
        for details in config['uap'][f'pairing_key_{key}'][category]['setting'].values():
            if not details['value']:
                selected_bits.append(details['bit'])
    return all_except(selected_bits)

def get_uap_bits(configs, category):
    selected_bits = []
    config = configs["reversible_configuration"]
    for key in range(4):
        for details in config['uap'][f'pairing_key_{key}'][category]['setting'].values():
            if details['value']:
                selected_bits.append(details['bit'])
    return bits(selected_bits)

import json
in_filename = ROOT / "core" / "embed" / "sec" / "tropic" / "config" / "tropic_configs.json"
with open(in_filename, "r") as f:
    configs = json.load(f)
reversible_config = configs["reversible_configuration"]
irreversible_config = configs["irreversible_configuration"]
i_names = list(irreversible_config.keys())
r_names = list(reversible_config.keys())
%>
// clang-format off
const struct lt_config_t g_irreversible_configuration = {
    .obj = {
% for category in i_names[:-1]:
        ${all_except([c['bit'] for c in irreversible_config[category]["setting"].values() if not(c['value'])])}
% endfor
% for category in irreversible_config['uap']['pairing_key_0'].keys():
        ${get_uap_all_except(configs, category)}
%endfor
    }
};

const struct lt_config_t g_reversible_configuration = {
    .obj = {
% for category in r_names[:-1]:
        ${bits([c['bit'] for c in reversible_config[category]["setting"].values() if c['value']])}
% endfor
% for category in reversible_config['uap']['pairing_key_0'].keys():
        ${get_uap_bits(configs, category)}
%endfor
    }
};
// clang-format on