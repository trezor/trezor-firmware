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

#include <trezor_types.h>

#include "optiga_common.h"

// Maximum data register length supported by OPTIGA.
#define OPTIGA_DATA_REG_LEN 277

// Maximum command and response APDU size supported by OPTIGA.
#define OPTIGA_MAX_APDU_SIZE 1557

optiga_result optiga_init(void);
void optiga_deinit(void);

optiga_result optiga_sec_chan_handshake(const uint8_t *secret,
                                        size_t secret_size);
optiga_result optiga_execute_command(const uint8_t *command_data,
                                     size_t command_size,
                                     uint8_t *response_data,
                                     size_t max_response_size,
                                     size_t *response_size);

optiga_result optiga_resync(void);
optiga_result optiga_soft_reset(void);
optiga_result optiga_set_data_reg_len(size_t size);

void optiga_set_ui_progress(optiga_ui_progress_t f);

#if !PRODUCTION
void optiga_transport_set_log_hex(optiga_log_hex_t f);
#endif

#endif
