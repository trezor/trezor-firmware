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

#ifdef SECURE_MODE

#include <trezor_rtl.h>

#include <sec/mldsa44.h>

#include <mldsa_native.h>

_Static_assert(MLDSA44_PUBLICKEY_SIZE ==
                   MLDSA_PUBLICKEYBYTES(MLD_CONFIG_API_PARAMETER_SET),
               "MLDSA44_PUBLICKEY_SIZE mismatch");

_Static_assert(MLDSA44_SIGNATURE_SIZE ==
                   MLDSA_BYTES(MLD_CONFIG_API_PARAMETER_SET),
               "MLDSA44_SIGNATURE_SIZE mismatch");

ts_t mldsa44_verify(const mldsa44_signature_t *sig, const void *m, size_t mlen,
                    const mldsa44_public_key_t *pk, secbool *valid) {
  TSH_DECLARE;

  TSH_CHECK_ARG(valid != NULL);
  *valid = secfalse;

  TSH_CHECK_ARG(sig != NULL);
  TSH_CHECK_ARG(m != NULL);
  TSH_CHECK_ARG(pk != NULL);

  if (mldsa_verify(sig->bytes, MLDSA44_SIGNATURE_SIZE, m, mlen,
                   (const uint8_t *)"", 0, pk->bytes) == 0) {
    *valid = sectrue;
  }

cleanup:
  TSH_RETURN;
}

#endif  // SECURE_MODE
