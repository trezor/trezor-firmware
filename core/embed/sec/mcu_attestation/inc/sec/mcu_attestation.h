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

#ifdef USE_MCU_ATTESTATION

#include <mldsa_native.h>
#include <trezor_model.h>
#include <trezor_types.h>

#define MCU_ATTESTATION_SIG_SIZE CRYPTO_BYTES
#define MCU_ATTESTATION_MAX_CERT_SIZE (SECRET_MCU_DEVICE_CERT_SIZE - 2)

/**
 * Get the size of the MCU device authentication certificate.
 *
 * @param cert_size Output parameter for certificate size.
 * @return sectrue on success, secfalse on failure.
 */
secbool mcu_attestation_cert_size(size_t *cert_size);

/**
 * Get the MCU device authentication certificate.
 *
 * @param cert Buffer to store the certificate.
 * @param max_cert_size Size of the certificate buffer.
 * @param cert_size Output parameter for actual certificate size.
 * @return sectrue on success, secfalse on failure.
 */
secbool mcu_attestation_cert_read(uint8_t *cert, size_t max_cert_size,
                                  size_t *cert_size);

/**
 * Sign a challenge with the MCU device authentication key (ML-DSA-44).
 *
 * @param challenge Challenge bytes to sign.
 * @param challenge_size Size of the challenge.
 * @param signature Output parameter for the signature (MCU_ATTESTATION_SIG_SIZE
 * bytes).
 * @return sectrue on success, secfalse on failure.
 */
secbool mcu_attestation_sign(const uint8_t *challenge, size_t challenge_size,
                             uint8_t signature[MCU_ATTESTATION_SIG_SIZE]);

#endif  // USE_MCU_ATTESTATION
