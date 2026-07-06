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

#include <io/app_header.h>

const app_header_t* app_header_verify(const void* header_ptr,
                                      size_t header_size) {
  TSH_DECLARE;
  const app_header_t* retval = NULL;

  TSH_CHECK(header_ptr != NULL, TS_EINVAL);
  TSH_CHECK(header_size >= sizeof(app_header_t), TS_EINVAL);

  const app_header_t* header = (const app_header_t*)header_ptr;

  TSH_CHECK(header->magic == APP_HEADER_MAGIC, TS_EBADMSG);
  TSH_CHECK(header->header_size == header_size, TS_EBADMSG);
  TSH_CHECK(header->abi_version == 1, TS_EBADMSG);

  retval = header;

cleanup:
  return retval;
}
