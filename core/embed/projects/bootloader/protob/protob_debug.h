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

#include <trezor_types.h>

#include "pb/messages-debug.pb.h"
#include "protob/protob.h"

secbool recv_msg_debug_link_decision(protob_io_t *iface,
                                     DebugLinkDecision *msg);

secbool recv_msg_debug_link_screen_record(protob_io_t *iface,
                                          DebugLinkRecordScreen *msg,
                                          uint8_t *buffer, size_t buffer_size);

secbool recv_msg_debug_link_get_state(protob_io_t *iface,
                                      DebugLinkGetState *msg);

secbool send_msg_debug_link_state(protob_io_t *iface);
