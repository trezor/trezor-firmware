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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include "protob.h"
#include "workflow.h"

workflow_result_t workflow_ping(protob_iface_t *iface, uint32_t msg_size,
                                uint8_t *buf) {
  Ping msg_recv;
  if (sectrue != recv_msg_ping(iface, &msg_recv, buf, msg_size)) {
    return WF_STAY;
  }
  send_msg_success(iface, msg_recv.message);
  return WF_STAY;
}
