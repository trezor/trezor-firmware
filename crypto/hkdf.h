/**
 * HKDF-SHA256 implementation (RFC 5869)
 *
 * Used for quantum-safe key derivation in SPHINCS+ (FIPS 205).
 */

#ifndef __HKDF_H__
#define __HKDF_H__

#include <stddef.h>
#include <stdint.h>

/**
 * HKDF-Extract: PRK = HMAC-SHA256(salt, IKM)
 *
 * @param salt     Optional salt (if NULL, uses 32 zero bytes)
 * @param salt_len Length of salt
 * @param ikm      Input keying material
 * @param ikm_len  Length of IKM
 * @param prk      Output pseudorandom key (32 bytes)
 */
void hkdf_sha256_extract(const uint8_t *salt, size_t salt_len,
                         const uint8_t *ikm, size_t ikm_len,
                         uint8_t prk[32]);

/**
 * HKDF-Expand: OKM = T(1) || T(2) || ... || T(N) truncated to okm_len
 * where T(i) = HMAC-SHA256(PRK, T(i-1) || info || i)
 *
 * @param prk      Pseudorandom key (32 bytes, from Extract)
 * @param info     Context and application specific information
 * @param info_len Length of info
 * @param okm      Output keying material
 * @param okm_len  Length of OKM (max 255 * 32 = 8160 bytes)
 * @return         0 on success, -1 if okm_len too large
 */
int hkdf_sha256_expand(const uint8_t prk[32],
                       const uint8_t *info, size_t info_len,
                       uint8_t *okm, size_t okm_len);

/**
 * HKDF one-shot: Extract-then-Expand
 *
 * @param salt     Optional salt (if NULL, uses 32 zero bytes)
 * @param salt_len Length of salt
 * @param ikm      Input keying material
 * @param ikm_len  Length of IKM
 * @param info     Context info
 * @param info_len Length of info
 * @param okm      Output keying material
 * @param okm_len  Length of OKM
 * @return         0 on success, -1 if okm_len too large
 */
int hkdf_sha256(const uint8_t *salt, size_t salt_len,
                const uint8_t *ikm, size_t ikm_len,
                const uint8_t *info, size_t info_len,
                uint8_t *okm, size_t okm_len);

#endif
