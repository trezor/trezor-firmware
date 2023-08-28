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

#ifndef TREZORHAL_OPTIGA_TRANSPORT_H
#define TREZORHAL_OPTIGA_TRANSPORT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "optiga_common.h"

// Maximum data register length supported by OPTIGA.
#define OPTIGA_DATA_REG_LEN 277

optiga_result optiga_init(void);
optiga_result optiga_execute_command(const uint8_t *command_data,
                                     size_t command_size,
                                     uint8_t *response_data,
                                     size_t max_response_size,
                                     size_t *response_size);

optiga_result optiga_resync(void);
optiga_result optiga_soft_reset(void);
optiga_result optiga_set_data_reg_len(size_t size);

#ifndef NDEBUG
typedef void (*optiga_log_hex_t)(const char *prefix, const uint8_t *data,
                                 size_t data_size);
void optiga_set_log_hex(optiga_log_hex_t f);
#endif

#endif
