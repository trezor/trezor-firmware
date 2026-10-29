/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../thp_vault.h"
/* Device identity is independent of wallet sessions. This applet-bound root
 * is shared by ciphertext records and revoked on VM reset. */
static uint32_t thp_secret_owner;
typedef struct {
  uint32_t owner;
  vault_blob_t blob;
} thp_vault_key_t;
_Static_assert(sizeof(thp_vault_key_t) <= THP_VAULT_KEY_SIZE,
               "THP descriptor capacity");

/// package: trezorcrypto.__init__
/// def thp_device_secret() -> secbytes:
///     """Read or create the device secret directly into a device-owned vault
///     record."""
static mp_obj_t thp_device_secret(void) {
  if (!secret_owner_find(thp_secret_owner))
    thp_secret_owner = secret_owner_create(0);
  if (!thp_secret_owner) mp_raise_ValueError(MP_ERROR_TEXT("No device owner"));
  mp_obj_secbytes_t *seed = secbytes_new(16);
  vault_request_t r = {.op = VAULT_THP_STORAGE, .owner = thp_secret_owner};
  vault_response_t out = {0};
  vault_raise(&r, &out);
  secbytes_set_blob(seed, &out.blob);
  memzero(&out, sizeof(out));
  return MP_OBJ_FROM_PTR(seed);
}
static MP_DEFINE_CONST_FUN_OBJ_0(thp_device_secret_obj, thp_device_secret);

bool trezorcrypto_thp_prepare(mp_obj_t seed, uint8_t key[THP_VAULT_KEY_SIZE],
                              uint8_t public_key[32]) {
  memzero(key, THP_VAULT_KEY_SIZE);
  memzero(public_key, 32);
  if (!mp_obj_is_type(seed, &mod_trezorcrypto_secbytes_type)) return false;
  mp_obj_secbytes_t *object = MP_OBJ_TO_PTR(seed);
  if (object->capacity != 16 || !thp_secret_owner) return false;
  vault_request_t r = {.op = VAULT_THP_DERIVE,
                       .owner = thp_secret_owner,
                       .blob = secbytes_blob(object)};
  vault_response_t out = {0};
  bool ok = secret_rpc(&r, &out);
  thp_vault_key_t descriptor = {.owner = thp_secret_owner, .blob = out.blob};
  if (ok) {
    r = (vault_request_t){.op = VAULT_THP_PUBLIC,
                          .owner = descriptor.owner,
                          .blob = descriptor.blob};
    ok = secret_rpc(&r, &out);
  }
  if (ok) {
    memcpy(key, &descriptor, sizeof(descriptor));
    memcpy(public_key, out.signature, 32);
  }
  memzero(&descriptor, sizeof(descriptor));
  memzero(&out, sizeof(out));
  return ok;
}
bool trezorcrypto_thp_dh(const uint8_t key[THP_VAULT_KEY_SIZE],
                         const uint8_t peer[32], uint8_t output[32]) {
  thp_vault_key_t descriptor = {0};
  memcpy(&descriptor, key, sizeof(descriptor));
  vault_request_t r = {.op = VAULT_THP_DH,
                       .owner = descriptor.owner,
                       .blob = descriptor.blob,
                       .length = 32};
  memcpy(r.data, peer, 32);
  vault_response_t out = {0};
  bool ok = descriptor.owner == thp_secret_owner && secret_rpc(&r, &out);
  memzero(output, 32);
  if (ok) memcpy(output, out.signature, 32);
  memzero(&r, sizeof(r));
  memzero(&out, sizeof(out));
  memzero(&descriptor, sizeof(descriptor));
  return ok;
}

/// def thp_credential_mac(counter: AnyBytes, data: AnyBytes) -> bytes:
///     """Authenticate a credential without exposing its SLIP-21 key."""
static mp_obj_t thp_credential_mac(mp_obj_t counter, mp_obj_t data) {
  mp_buffer_info_t count = {0}, message = {0};
  mp_get_buffer_raise(counter, &count, MP_BUFFER_READ);
  mp_get_buffer_raise(data, &message, MP_BUFFER_READ);
  if (count.len != 4 || message.len > VAULT_DATA_SIZE)
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid credential parameters"));
  mp_obj_t seed = thp_device_secret();
  vault_request_t r = {.op = VAULT_SLIP21,
                       .owner = thp_secret_owner,
                       .arg = VAULT_SLIP21_ROOT | VAULT_SLIP21_KEY,
                       .blob = secbytes_blob(MP_OBJ_TO_PTR(seed))};
  static const uint8_t path[] =
      "\006TREZOR\041THP credential authentication key\004";
  memcpy(r.data, path, sizeof(path) - 1);
  memcpy(r.data + sizeof(path) - 1, count.buf, 4);
  r.length = sizeof(path) - 1 + 4;
  vault_response_t out = {0};
  vault_raise(&r, &out);
  r = (vault_request_t){.op = VAULT_HMAC_TAG,
                        .owner = thp_secret_owner,
                        .arg = 256,
                        .blob = out.blob,
                        .length = message.len};
  memcpy(r.data, message.buf, message.len);
  vault_raise(&r, &out);
  mp_obj_t result = mp_obj_new_bytes(out.signature, 32);
  memzero(&out, sizeof(out));
  return result;
}
static MP_DEFINE_CONST_FUN_OBJ_2(thp_credential_mac_obj, thp_credential_mac);

/// def thp_reset_storage() -> None:
///     """Wipe storage, preserve the THP seed natively and revoke all vault
///     records."""
static mp_obj_t thp_reset_storage(void) {
  vault_request_t r = {.op = VAULT_THP_RESET, .owner = thp_secret_owner};
  vault_response_t out = {0};
  vault_raise(&r, &out);
  thp_secret_owner = 0;
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(thp_reset_storage_obj, thp_reset_storage);
