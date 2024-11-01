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

#ifndef TREZORHAL_OPTIGA_COMMANDS_H
#define TREZORHAL_OPTIGA_COMMANDS_H

#include <trezor_types.h>

#include "optiga_common.h"

// Data object identifiers.
typedef enum {
  OPTIGA_OID_COPROC_UID = 0xE0C2,      // Coprocessor UID.
  OPTIGA_OID_SEC = 0xE0C5,             // Security event counter.
  OPTIGA_OID_CERT = 0xE0E0,            // Public key certificates [1-4].
  OPTIGA_OID_CA_CERT = 0xE0E8,         // Root CA public key certificates [1-2].
  OPTIGA_OID_ECC_KEY = 0xE0F0,         // Private ECC keys [1-4].
  OPTIGA_OID_SESSION_CTX = 0xE100,     // Session contexts [1-4].
  OPTIGA_OID_COUNTER = 0xE120,         // Monotonic counters [1-4].
  OPTIGA_OID_PTFBIND_SECRET = 0xE140,  // Shared platform binding secret.
  OPTIGA_OID_SYM_KEY = 0xE200,         // Device symmetric key.
  OPTIGA_OID_ERROR_CODE = 0xF1C2,      // Command error code.
  OPTIGA_OID_DATA = 0xF1D0,            // Arbitrary 140 B data objects [1-12].
  OPTIGA_OID_BIG_DATA = 0xF1E0,        // Arbitrary 1500 B data objects [1-2].
} optiga_oid;

// ECC curve identifiers.
typedef enum {
  OPTIGA_CURVE_P256 = 0x03,  // NIST P256 ECC key.
  OPTIGA_CURVE_P384 = 0x04,  // NIST P384 ECC key.
  OPTIGA_CURVE_P521 = 0x05,  // NIST P521 ECC key.
} optiga_curve;

// AES algorithm identifiers.
typedef enum {
  OPTIGA_AES_128 = 0x81,  // AES-128 key.
  OPTIGA_AES_192 = 0x82,  // AES-192 key.
  OPTIGA_AES_256 = 0x83,  // AES-256 key.
} optiga_aes;

// Key usage identifiers.
typedef enum {
  OPTIGA_KEY_USAGE_AUTH = 0x01,      // Authentication.
  OPTIGA_KEY_USAGE_ENC = 0x02,       // Encryption, decryption, key transport.
  OPTIGA_KEY_USAGE_SIGN = 0x10,      // Signature calculation and verification.
  OPTIGA_KEY_USAGE_KEYAGREE = 0x20,  // Key agreement.
} optiga_key_usage;

// Key derivation methods.
typedef enum {
  OPTIGA_DERIV_TLS_PRF_SHA256 = 0x01,
  OPTIGA_DERIV_TLS_PRF_SHA384 = 0x02,
  OPTIGA_DERIV_TLS_PRF_SHA512 = 0x03,
  OPTIGA_DERIV_HKDF_SHA256 = 0x08,
  OPTIGA_DERIV_HKDF_SHA384 = 0x09,
  OPTIGA_DERIV_HKDF_SHA512 = 0x0a,
} optiga_key_derivation;

// Symmetric modes of operation.
typedef enum {
  OPTIGA_SYM_MODE_ECB = 0x08,      // Input must be padded.
  OPTIGA_SYM_MODE_CBC_MAC = 0x0A,  // Input must be padded.
  OPTIGA_SYM_MODE_CMAC = 0x0B,
  OPTIGA_SYM_MODE_HMAC_SHA256 = 0x20,
  OPTIGA_SYM_MODE_HMAC_SHA384 = 0x21,
  OPTIGA_SYM_MODE_HMAC_SHA512 = 0x22,
} optiga_sym_mode;

// Data object types.
typedef enum {
  OPTIGA_DATA_TYPE_BSTR = 0x00,      // Byte string.
  OPTIGA_DATA_TYPE_UPCTR = 0x01,     // Monotonic up-counter.
  OPTIGA_DATA_TYPE_TA = 0x11,        // Trust anchor.
  OPTIGA_DATA_TYPE_DEVCERT = 0x12,   // Device identity certificate.
  OPTIGA_DATA_TYPE_PRESSEC = 0x21,   // Secret for HMAC computation.
  OPTIGA_DATA_TYPE_PTFBIND = 0x22,   // Secret for platform binding.
  OPTIGA_DATA_TYPE_UPDATSEC = 0x23,  // Secret for confidential object update.
  OPTIGA_DATA_TYPE_AUTOREF = 0x31,   // Secret for verifying external entity.
} optiga_data_type;

// Access conditions.
typedef enum {
  OPTIGA_ACCESS_COND_ALW = 0x00,   // Always.
  OPTIGA_ACCESS_COND_CONF = 0x20,  // Confidentiality protection required.
  OPTIGA_ACCESS_COND_INT = 0x21,   // Integrity protection required.
  OPTIGA_ACCESS_COND_AUTO = 0x23,  // Authorization required.
  OPTIGA_ACCESS_COND_LUC = 0x40,   // Usage limited by counter.
  OPTIGA_ACCESS_COND_NEV = 0xFF,   // Never.
} optiga_access_cond;

// Life cycle status.
typedef enum {
  OPTIGA_LCS_CR = 0x01,  // Creation state.
  OPTIGA_LCS_IN = 0x03,  // Initialization state.
  OPTIGA_LCS_OP = 0x07,  // Operational state.
  OPTIGA_LCS_TE = 0x0f,  // Termination state.
} optiga_lcs;

// Error codes returned by optiga_get_error_code().
typedef enum {
  OPTIGA_ERR_CODE_NONE = 0x00,             // No Error.
  OPTIGA_ERR_CODE_INVAL_OID = 0x01,        // Invalid OID.
  OPTIGA_ERR_CODE_INVAL_CMD_PARAM = 0x03,  // Invalid param field in command.
  OPTIGA_ERR_CODE_INVAL_CMD_LEN = 0x04,    // Invalid length field in command.
  OPTIGA_ERR_CODE_INVAL_CMD_DATA = 0x05,   // Invalid parameter in command data.
  OPTIGA_ERR_CODE_PROCESS = 0x06,          // Internal process error.
  OPTIGA_ERR_CODE_ACCESS_COND = 0x07,      // Access conditions not satisfied.
  OPTIGA_ERR_CODE_OBJ_BOUNDARY = 0x08,     // Data object boundary exceeded.
  OPTIGA_ERR_CODE_META_TRUNC = 0x09,       // Metadata truncation error.
  OPTIGA_ERR_CODE_INVAL_CMD_FIELD = 0x0A,  // Invalid command field.
  OPTIGA_ERR_CODE_CMD_SEQ = 0x0B,          // Command out of sequence.
  OPTIGA_ERR_CODE_CMD_UNAVAIL = 0x0C,      // Command not available.
  OPTIGA_ERR_CODE_MEMORY = 0x0D,           // Insufficient memory to process the
                                           // command.
  OPTIGA_ERR_CODE_CTR_LIMIT = 0x0E,        // Counter threshold limit exceeded.
  OPTIGA_ERR_CODE_INVAL_MANIFEST = 0x0F,   // Invalid manifest.
  OPTIGA_ERR_CODE_PAYLOAD_VER = 0x10,      // Wrong payload version.
  OPTIGA_ERR_CODE_INVAL_OBJ_META = 0x11,   // Invalid data object metadata.
  OPTIGA_ERR_CODE_UNSUP_EXT_ID = 0x24,     // Unsupported key usage, extension
                                           // or algorithm identifier.
  OPTIGA_ERR_CODE_UNSUP_PARAM = 0x25,      // Unsupported parameters in
                                           // handshake or command APDU InData.
  OPTIGA_ERR_CODE_INVAL_CERT = 0x29,       // Invalid certificate format or
                                           // signature.
  OPTIGA_ERR_CODE_UNSUP_CERT = 0x2A,       // Unsupported certificate.
  OPTIGA_ERR_CODE_SIG_FAIL = 0x2C,         // Signature verification failure.
  OPTIGA_ERR_CODE_INT_FAIL = 0x2D,      // Message integrity validation failed
                                        // (e.g. during CCM decryption).
  OPTIGA_ERR_CODE_DECRYPT_FAIL = 0x2E,  // Decryption failure
  OPTIGA_ERR_CODE_AUTH_FAIL = 0x2F,     // Authorization failure
} optiga_err_code;

typedef struct {
  const uint8_t *ptr;
  uint16_t len;
} optiga_metadata_item;

typedef struct {
  optiga_metadata_item lcso;         // C0 - Life cycle state of data object.
  optiga_metadata_item version;      // C1 - Version information of data object.
  optiga_metadata_item max_size;     // C4 - Maximum size of the data object.
  optiga_metadata_item used_size;    // C5 - Used size of the data object.
  optiga_metadata_item change;       // D0 - Change access conditions.
  optiga_metadata_item read;         // D1 - Read access conditions.
  optiga_metadata_item execute;      // D3 - Execute access conditions.
  optiga_metadata_item meta_update;  // D8 - Metadata update descriptor.
  optiga_metadata_item algorithm;    // E0 - Algorithm associated with the key.
  optiga_metadata_item key_usage;    // E1 - Key usage associated with the key.
  optiga_metadata_item data_type;    // E8 - Data object type.
  optiga_metadata_item reset_type;   // F0 - Factory reset type.
} optiga_metadata;

#define OPTIGA_ECC_KEY_COUNT 4
#define OPTIGA_CERT_COUNT 4
#define OPTIGA_MAX_METADATA_SIZE 44
#define OPTIGA_RANDOM_MIN_SIZE 8
#define OPTIGA_RANDOM_MAX_SIZE 256
#define OPTIGA_MAX_CERT_SIZE 1728

#define OPTIGA_ACCESS_CONDITION(ac_id, oid)           \
  (const optiga_metadata_item) {                      \
    (const uint8_t[]){ac_id, oid >> 8, oid & 0xff}, 3 \
  }

// Single-byte value of optiga_metadata_item.
#define OPTIGA_META_VALUE(val) \
  (const optiga_metadata_item) { (const uint8_t[]){val}, 1 }

// Commonly used data object access conditions.
extern const optiga_metadata_item OPTIGA_META_LCS_OPERATIONAL;
extern const optiga_metadata_item OPTIGA_META_ACCESS_ALWAYS;
extern const optiga_metadata_item OPTIGA_META_ACCESS_NEVER;
extern const optiga_metadata_item OPTIGA_META_KEY_USE_ENC;
extern const optiga_metadata_item OPTIGA_META_KEY_USE_KEYAGREE;
extern const optiga_metadata_item OPTIGA_META_VERSION_DEFAULT;

optiga_result optiga_parse_metadata(const uint8_t *serialized,
                                    size_t serialized_size,
                                    optiga_metadata *metadata);
optiga_result optiga_serialize_metadata(const optiga_metadata *metadata,
                                        uint8_t *serialized,
                                        size_t max_serialized,
                                        size_t *serialized_size);
bool optiga_compare_metadata(const optiga_metadata *expected,
                             const optiga_metadata *stored);

optiga_result optiga_open_application(void);
optiga_result optiga_get_error_code(uint8_t *error_code);
optiga_result optiga_get_data_object(uint16_t oid, bool get_metadata,
                                     uint8_t *data, size_t max_data_size,
                                     size_t *data_size);
optiga_result optiga_set_data_object(uint16_t oid, bool set_metadata,
                                     const uint8_t *data, size_t data_size);
optiga_result optiga_count_data_object(uint16_t oid, uint8_t count);
optiga_result optiga_get_random(uint8_t *random, size_t random_size);
optiga_result optiga_encrypt_sym(optiga_sym_mode mode, uint16_t oid,
                                 const uint8_t *input, size_t input_size,
                                 uint8_t *output, size_t max_output_size,
                                 size_t *output_size);
optiga_result optiga_set_auto_state(uint16_t nonce_oid, uint16_t key_oid,
                                    const uint8_t *key, size_t key_size);
optiga_result optiga_clear_auto_state(uint16_t key_oid);
optiga_result optiga_calc_sign(uint16_t oid, const uint8_t *digest,
                               size_t digest_size, uint8_t *signature,
                               size_t max_sig_size, size_t *sig_size);
optiga_result optiga_verify_sign(optiga_curve curve, const uint8_t *public_key,
                                 size_t public_key_size, const uint8_t *digest,
                                 size_t digest_size, const uint8_t *signature,
                                 size_t sig_size);
optiga_result optiga_gen_key_pair(optiga_curve curve, optiga_key_usage usage,
                                  uint16_t oid, uint8_t *public_key,
                                  size_t max_public_key_size,
                                  size_t *public_key_size);
optiga_result optiga_gen_sym_key(optiga_aes algorithm, optiga_key_usage usage,
                                 uint16_t oid);
optiga_result optiga_calc_ssec(optiga_curve curve, uint16_t oid,
                               const uint8_t *public_key,
                               size_t public_key_size, uint8_t *secret,
                               size_t max_secret_size, size_t *secret_size);
optiga_result optiga_derive_key(optiga_key_derivation deriv, uint16_t oid,
                                const uint8_t *salt, size_t salt_size,
                                uint8_t *info, size_t info_size, uint8_t *key,
                                size_t key_size);
optiga_result optiga_set_trust_anchor(void);
optiga_result optiga_set_priv_key(uint16_t oid, const uint8_t priv_key[32]);

#if !PRODUCTION
void optiga_command_set_log_hex(optiga_log_hex_t f);
#endif

#endif
