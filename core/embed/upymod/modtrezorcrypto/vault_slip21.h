/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef TREZOR_VAULT_SLIP21_H
#define TREZOR_VAULT_SLIP21_H
#include "hmac.h"
#include "memzero.h"
#include "slip21.h"

static bool slip21_export_allowed(const uint8_t *data, size_t length) {
  static const uint8_t evolu[] = "\006TREZOR\005Evolu";
  static const uint8_t index[] = "\006TREZOR\013Evolu Index";
  const size_t n = sizeof(index) - 1;
  return (length == sizeof(evolu) - 1 && !memcmp(data, evolu, length)) ||
         (length > n + 1 && !memcmp(data, index, n) &&
          data[n] == length - n - 1);
}

static bool vault_slip21_call(const vault_request_t *r, vault_response_t *out) {
  memset(out, 0, sizeof(*out));
  if (r->abi != VAULT_ABI || r->length > VAULT_DATA_SIZE ||
      (r->op != VAULT_SLIP21 && r->op != VAULT_HMAC_TAG))
    return false;
  bool root = r->arg & VAULT_SLIP21_ROOT;
  uint32_t output = r->arg & ~(uint32_t)VAULT_SLIP21_ROOT;
  if (r->op == VAULT_SLIP21 &&
      (output != VAULT_SLIP21_NODE && output != VAULT_SLIP21_KEY &&
       output != VAULT_SLIP21_EXPORT))
    return false;
  if (r->op == VAULT_SLIP21 && output == VAULT_SLIP21_EXPORT &&
      !(root && slip21_export_allowed(r->data, r->length)))
    return false;
  vault_request_t request = {.abi = VAULT_ABI,
                             .op = VAULT_OPEN_NATIVE,
                             .owner = r->owner,
                             .arg = SECRET_BYTES,
                             .blob = r->blob};
  vault_response_t opened = {0};
  uint8_t node[64] = {0};
  bool ok = vault_call(&request, &opened);
  if (!ok) goto cleanup;
  if (r->op == VAULT_HMAC_TAG) {
    if (r->arg == 256)
      hmac_sha256(opened.opened, opened.value, r->data, r->length,
                  out->signature);
    else if (r->arg == 512)
      hmac_sha512(opened.opened, opened.value, r->data, r->length,
                  out->signature);
    else
      ok = false;
    goto cleanup;
  }
  if (root)
    slip21_from_seed(opened.opened, opened.value, node);
  else if (opened.value == sizeof(node))
    memcpy(node, opened.opened, sizeof(node));
  else {
    ok = false;
    goto cleanup;
  }
  ok = slip21_derive_path(node, r->data, r->length);
  if (!ok) goto cleanup;
  if (output == VAULT_SLIP21_EXPORT)
    memcpy(out->signature, node, sizeof(node));
  else {
    request = (vault_request_t){.abi = VAULT_ABI,
                                .op = VAULT_IMPORT_BYTES,
                                .owner = r->owner,
                                .length = output == VAULT_SLIP21_KEY ? 32 : 64,
                                .child_num = 1};
    memcpy(request.data, node + (output == VAULT_SLIP21_KEY ? 32 : 0),
           request.length);
    ok = vault_call(&request, out);
  }
cleanup:
  memzero(&request, sizeof(request));
  memzero(&opened, sizeof(opened));
  memzero(node, sizeof(node));
  if (!ok) memzero(out, sizeof(*out));
  return ok;
}
#endif
