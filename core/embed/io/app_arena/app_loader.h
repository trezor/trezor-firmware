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

#include <trezor_types.h>

#include <io/app_header.h>
#include <sys/applet.h>

/**
 * @brief Verifies the payload of an application image for integrity and
 * correctness.
 *
 * Verifies the payload of the image if it is a valid application image (e.g.
 * correct offsets, sizes, etc.)
 *
 * @param header Pointer to the header of the application image
 * @param payload Pointer to the payload of the application image
 * @param payload_size Size of the payload in bytes
 *
 * @return ts_t Status code indicating success or failure
 *         TS_EBADMSG - Invalid payload (e.g. incorrect sizes, offsets, etc.)
 *         TS_ENOMEM - Not enough memory to load the applet
 */

ts_t app_loader_verify_payload(const app_header_t* header, const void* payload,
                               size_t payload_size);

/**
 * @brief Initializes an applet structure for an application image
 *
 * Clears all applet rw memory and initializes .data section.
 *
 * @param header Pointer to the verified application header
 * @param payload Pointer to the payload of the application image
 * @param rwmem Pointer to the memory allocated for the applet's RW section
 * @param rwmem_size Size of the allocated RW memory
 * @param applet Pointer to the applet structure to initialize
 *
 * @return ts_t Status code indicating success or failure
 *         TS_EBADMSG if the image payload is invalid
 *         TS_ENOMEM if there is not enough memory to initialize the applet
 */
ts_t app_loader_prepare_applet(const app_header_t* header, void* payload,
                               void* rwmem, size_t rwmem_size,
                               applet_t* applet);
