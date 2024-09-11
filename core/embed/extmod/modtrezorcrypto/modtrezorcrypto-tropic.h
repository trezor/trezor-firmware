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

#if USE_TROPIC

// Default initial Tropic handshake keys
#define PKEY_INDEX_BYTE   PAIRING_KEY_SLOT_INDEX_0
#define SHiPRIV_BYTES    {0xf0,0xc4,0xaa,0x04,0x8f,0x00,0x13,0xa0,0x96,0x84,0xdf,0x05,0xe8,0xa2,0x2e,0xf7,0x21,0x38,0x98,0x28,0x2b,0xa9,0x43,0x12,0xf3,0x13,0xdf,0x2d,0xce,0x8d,0x41,0x64};
#define SHiPUB_BYTES     {0x84,0x2f,0xe3,0x21,0xa8,0x24,0x74,0x08,0x37,0x37,0xff,0x2b,0x9b,0x88,0xa2,0xaf,0x42,0x44,0x2d,0xb0,0xd8,0xaa,0xcc,0x6d,0xc6,0x9e,0x99,0x53,0x33,0x44,0xb2,0x46};

#include "libtropic.h"

/// package: trezorcrypto.tropic

/// class TropicError(Exception):
///     """Error returned by the Tropic Square chip."""
MP_DEFINE_EXCEPTION(TropicError, Exception)


void bytes_to_chars(uint8_t const *key, char *buffer, uint16_t len)
{
    uint16_t offset = 0;
    memset(buffer, 0, len);

    for (size_t i = 0; i < len; i++)
    {
        offset += sprintf(buffer + offset, "%02X", key[i]);
    }
    sprintf(buffer + offset, "%c", '\0');
}

#define PING_MSG "Hello!"
#define PING_MSG_LEN 6
/// mock:global
/// def ping() -> bool:
///     """
///     Test the session by pinging the chip.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_ping() {
    lt_handle_t handle = {0};
    lt_ret_t ret = LT_FAIL;

    ret = lt_init(&handle);

    uint8_t X509_cert[LT_L2_GET_INFO_REQ_CERT_SIZE] = {0};

    ret = lt_get_info_cert(&handle, X509_cert, LT_L2_GET_INFO_REQ_CERT_SIZE);

    uint8_t stpub[32] = {0};
    ret = lt_cert_verify_and_parse(X509_cert, 512, stpub);

    uint8_t pkey_index  = PKEY_INDEX_BYTE;
    uint8_t shipriv[]   = SHiPRIV_BYTES;
    uint8_t shipub[]    = SHiPUB_BYTES;

    ret = lt_handshake(&handle, stpub, pkey_index, shipriv, shipub);

    uint8_t msg_out[PING_MSG_LEN] = {0};
    uint8_t msg_in[PING_MSG_LEN]  = {0};
    uint16_t len_ping = PING_MSG_LEN;

    memcpy(msg_out, PING_MSG, PING_MSG_LEN);

    ret = lt_ping(&handle, (uint8_t *)msg_out, (uint8_t *)msg_in, len_ping);

    return mp_obj_new_bool(ret == LT_OK && !memcmp(msg_out, msg_in, PING_MSG_LEN));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypto_tropic_ping_obj,
                                 mod_trezorcrypto_tropic_ping);

/// mock:global
/// def get_certificate() -> bytes:
///     """
///     Return the chip's certificate.
///     """
STATIC mp_obj_t mod_trezorcrypto_tropic_get_certificate() {
    lt_handle_t handle = {0};
    lt_ret_t ret = LT_FAIL;

    ret = lt_init(&handle);

    uint8_t X509_cert[512] = {0};

    ret = lt_get_info_cert(&handle, X509_cert, 512);

    if (ret != LT_OK) {
        mp_raise_msg(&mp_type_TropicError, "Failed to read certificate.");
    }

    vstr_t vstr = {0};
    vstr_init_len(&vstr, 1024);

    bytes_to_chars(X509_cert, vstr.buf, 512);

    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypto_tropic_get_certificate_obj,
                                 mod_trezorcrypto_tropic_get_certificate);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_tropic_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_tropic)},
    {MP_ROM_QSTR(MP_QSTR_get_certificate),
     MP_ROM_PTR(&mod_trezorcrypto_tropic_get_certificate_obj)},
    {MP_ROM_QSTR(MP_QSTR_ping), MP_ROM_PTR(&mod_trezorcrypto_tropic_ping_obj)},
    {MP_ROM_QSTR(MP_QSTR_TropicError), MP_ROM_PTR(&mp_type_TropicError)}};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_tropic_globals,
                            mod_trezorcrypto_tropic_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_tropic_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_tropic_globals,
};

#endif
