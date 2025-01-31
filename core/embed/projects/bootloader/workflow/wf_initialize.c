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

workflow_result_t workflow_initialize(protob_io_t *iface,
                                      const vendor_header *const vhdr,
                                      const image_header *const hdr) {
  Initialize msg_recv;
  recv_msg_initialize(iface, &msg_recv);
  send_msg_features(iface, vhdr, hdr);
  return WF_OK;
}
