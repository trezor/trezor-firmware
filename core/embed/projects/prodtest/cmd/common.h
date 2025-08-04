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

#pragma once

#include <rtl/cli.h>

#define CHALLENGE_SIZE 16

bool check_cert_chain(cli_t* cli, const uint8_t* chain, size_t chain_size,
                      const uint8_t* sig, size_t sig_size,
                      const uint8_t challenge[CHALLENGE_SIZE]);

void binary_update(cli_t* cli, bool (*finalize)(uint8_t* data, size_t len));
