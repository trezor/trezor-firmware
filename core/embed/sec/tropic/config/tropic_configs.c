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

// See the documentation of Tropic configurations in
// `docs/core/misc/tropic_configs.md` for more details.

// clang-format off
const struct lt_config_t g_irreversible_configuration = {
    .obj = {
        ~0U & ~BIT(1) & ~BIT(2),
        ~0U,
        ~0U & ~BIT(0),
        ~0U,
        ~0U,
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(9) & ~BIT(16) & ~BIT(17) & ~BIT(24) & ~BIT(25),
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(1),
        ~0U & ~BIT(0) & ~BIT(8),
        ~0U & ~BIT(0) & ~BIT(8),
        ~0U & ~BIT(0) & ~BIT(8),
        ~0U & ~BIT(0),
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(9) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(9) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(9) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0),
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(8) & ~BIT(16) & ~BIT(24),
        ~0U & ~BIT(0) & ~BIT(1) & ~BIT(8) & ~BIT(9) & ~BIT(16) & ~BIT(24),
    }
};

const struct lt_config_t g_reversible_configuration = {
    .obj = {
        BIT(0) | BIT(3),
        0,
        0,
        0,
        BIT(0),
        BIT(2) | BIT(10) | BIT(18) | BIT(26),
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(2),
        BIT(1) | BIT(2) | BIT(9) | BIT(10),
        BIT(1) | BIT(2) | BIT(9) | BIT(10),
        BIT(1) | BIT(2) | BIT(9) | BIT(10),
        BIT(1) | BIT(2),
        BIT(2) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(1) | BIT(2) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(1) | BIT(2) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(1) | BIT(2),
        BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(1) | BIT(2) | BIT(9) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
        BIT(2) | BIT(10) | BIT(17) | BIT(18) | BIT(25) | BIT(26),
    }
};
// clang-format on
