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

// See the documentation of Tropic configurations in
// `docs/core/misc/tropic_configs.md` for more details.

// clang-format off
// Count check: the compiler resolves LT_CONFIG_OBJ_CNT; the numbers on the left
// are computed from tropic_configs.json at template generation time.
// This catches a missing category in the JSON (too-few silently zero-fills in
// C).
#if 27 != LT_CONFIG_OBJ_CNT
#error "irreversible_configurations category count in tropic_configs.json does not match LT_CONFIG_OBJ_CNT"
#endif
#if 27 != LT_CONFIG_OBJ_CNT
#error "reversible_configurations category count in tropic_configs.json does not match LT_CONFIG_OBJ_CNT"
#endif

const tropic_versioned_config_t tropic_irreversible_configs[] = {
    {
        .version = 0,
        .config = {
            .obj = {
                0xFFFFFFF9U,
                0xFFFFFFFFU,
                0xFFFFFFFEU,
                0xFFFFFFFFU,
                0xFFFFFFFFU,
                0xFCFCFCFCU,
                0xFEFEFEFEU,
                0xFEFEFEFEU,
                0xFFFFFFFCU,
                0xFFFFFEFEU,
                0xFFFFFEFEU,
                0xFFFFFEFEU,
                0xFFFFFFFEU,
                0xFEFEFCFCU,
                0xFEFEFCFEU,
                0xFEFEFCFEU,
                0xFFFFFFFEU,
                0xFEFEFEFCU,
                0xFEFEFEFCU,
                0xFEFEFEFEU,
                0xFEFEFEFEU,
                0xFEFEFEFCU,
                0xFEFEFEFCU,
                0xFEFEFEFCU,
                0xFEFEFEFEU,
                0xFEFEFEFEU,
                0xFEFEFCFCU,
            }
        },
    },
    {
        .version = 1,
        .config = {
            .obj = {
                0xFFFFFFF9U,
                0xFFFC0000U,
                0xFFFFFFFEU,
                0xFFFFFFFFU,
                0xFFFFFFFFU,
                0xFCFCFCFCU,
                0xFEFEFEFEU,
                0xFEFEFEFEU,
                0xFFFFFFFCU,
                0xFFFFFEFEU,
                0xFFFFFEFEU,
                0xFFFFFEFEU,
                0xFFFFFFFEU,
                0xFEFEFCFCU,
                0xFEFEFCFEU,
                0xFEFEFCFEU,
                0xFFFFFFFEU,
                0xFEFEFEFCU,
                0xFEFEFEFCU,
                0xFEFEFEFEU,
                0xFEFEFEFEU,
                0xFEFEFEFCU,
                0xFEFEFEFCU,
                0xFEFEFEFCU,
                0xFEFEFEFEU,
                0xFEFEFEFEU,
                0xFEFEFCFCU,
            }
        },
    },
};

const tropic_versioned_config_t tropic_reversible_configs[] = {
    {
        .version = 0,
        .config = {
            .obj = {
                0x00000009U,
                0,
                0,
                0,
                0x00000001U,
                0x04040404U,
                0x06060606U,
                0x06060606U,
                0x00000004U,
                0x00000606U,
                0x00000606U,
                0x00000606U,
                0x00000006U,
                0x06060404U,
                0x06060406U,
                0x06060406U,
                0x00000006U,
                0x06060604U,
                0x06060604U,
                0x06060606U,
                0x06060606U,
                0x06060604U,
                0x06060604U,
                0x06060604U,
                0x06060606U,
                0x06060606U,
                0x06060404U,
            }
        },
    },
    {
        .version = 1,
        .config = {
            .obj = {
                0x00000001U,
                0,
                0,
                0,
                0x00000001U,
                0x04040404U,
                0x06060606U,
                0x06060606U,
                0x00000004U,
                0x00000606U,
                0x00000606U,
                0x00000606U,
                0x00000006U,
                0x06060404U,
                0x06060406U,
                0x06060406U,
                0x00000006U,
                0x06060604U,
                0x06060604U,
                0x06060606U,
                0x06060606U,
                0x06060604U,
                0x06060604U,
                0x06060604U,
                0x06060606U,
                0x06060606U,
                0x06060404U,
            }
        },
    },
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
