/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include "py/objstr.h"
#include "py/objint.h"
#include "py/mpz.h"

#include "monero/monero.h"
#include "bignum.h"

/// package: trezorcrypto.monero



typedef struct _mp_obj_hasher_t {
    mp_obj_base_t base;
    Hasher h;
} mp_obj_hasher_t;

typedef struct _mp_obj_ge25519_t {
    mp_obj_base_t base;
    ge25519 p;
} mp_obj_ge25519_t;

typedef struct _mp_obj_bignum256modm_t {
    mp_obj_base_t base;
    bignum256modm p;
} mp_obj_bignum256modm_t;


//
// Helpers
//

STATIC const mp_obj_type_t mod_trezorcrypto_monero_ge25519_type;
STATIC const mp_obj_type_t mod_trezorcrypto_monero_bignum256modm_type;
STATIC const mp_obj_type_t mod_trezorcrypto_monero_hasher_type;

#define MP_OBJ_IS_GE25519(o) MP_OBJ_IS_TYPE((o), &mod_trezorcrypto_monero_ge25519_type)
#define MP_OBJ_IS_SCALAR(o) MP_OBJ_IS_TYPE((o), &mod_trezorcrypto_monero_bignum256modm_type)
#define MP_OBJ_PTR_MPC_GE25519(o) ((const mp_obj_ge25519_t*) (o))
#define MP_OBJ_PTR_MPC_SCALAR(o) ((const mp_obj_bignum256modm_t*) (o))
#define MP_OBJ_PTR_MP_GE25519(o) ((mp_obj_ge25519_t*) (o))
#define MP_OBJ_PTR_MP_SCALAR(o) ((mp_obj_bignum256modm_t*) (o))
#define MP_OBJ_C_GE25519(o) (MP_OBJ_PTR_MPC_GE25519(o)->p)
#define MP_OBJ_GE25519(o) (MP_OBJ_PTR_MP_GE25519(o)->p)
#define MP_OBJ_C_SCALAR(o) (MP_OBJ_PTR_MPC_SCALAR(o)->p)
#define MP_OBJ_SCALAR(o) (MP_OBJ_PTR_MP_SCALAR(o)->p)

STATIC inline void assert_ge25519(const mp_obj_t o){
    if (!MP_OBJ_IS_GE25519(o)){
        mp_raise_ValueError("ge25519 expected");
    }
}

STATIC inline void assert_scalar(const mp_obj_t o){
    if (!MP_OBJ_IS_SCALAR(o)){
        mp_raise_ValueError("scalar expected");
    }
}


static uint64_t mp_obj_uint64_get_checked(mp_const_obj_t self_in) {
#if MICROPY_LONGINT_IMPL != MICROPY_LONGINT_IMPL_MPZ
#  error "MPZ supported only"
#endif

    if (MP_OBJ_IS_SMALL_INT(self_in)) {
        return MP_OBJ_SMALL_INT_VALUE(self_in);
    } else {
        byte buff[8];
        uint64_t res = 0;
        mp_obj_t * o = MP_OBJ_TO_PTR(self_in);

        mp_obj_int_to_bytes_impl(o, true, 8, buff);
        for (int i = 0; i<8; i++){
            res <<= i > 0 ? 8 : 0;
            res |= (uint64_t)(buff[i] & 0xff);
        }
        return res;
    }
}

static uint64_t mp_obj_get_uint64(mp_const_obj_t arg) {
    if (arg == mp_const_false) {
        return 0;
    } else if (arg == mp_const_true) {
        return 1;
    } else if (MP_OBJ_IS_SMALL_INT(arg)) {
        return MP_OBJ_SMALL_INT_VALUE(arg);
    } else if (MP_OBJ_IS_TYPE(arg, &mp_type_int)) {
        return mp_obj_uint64_get_checked(arg);
    } else {
        if (MICROPY_ERROR_REPORTING == MICROPY_ERROR_REPORTING_TERSE) {
            mp_raise_TypeError("can't convert to int");
        } else {
            nlr_raise(mp_obj_new_exception_msg_varg(&mp_type_TypeError,
                                                    "can't convert %s to int", mp_obj_get_type_str(arg)));
        }
    }
}

STATIC mp_obj_t mp_obj_new_scalar(){
  mp_obj_bignum256modm_t *o = m_new_obj(mp_obj_bignum256modm_t);
  o->base.type = &mod_trezorcrypto_monero_bignum256modm_type;
  set256_modm(o->p, 0);
  return MP_OBJ_FROM_PTR(o);
}

STATIC mp_obj_t mp_obj_new_scalar_r(mp_obj_t r){
    if (r == mp_const_none){
        return mp_obj_new_scalar();
    }

    assert_scalar(r);
    return r;
}

STATIC mp_obj_t mp_obj_new_ge25519(){
    mp_obj_ge25519_t *o = m_new_obj(mp_obj_ge25519_t);
    o->base.type = &mod_trezorcrypto_monero_ge25519_type;
    ge25519_set_neutral(&o->p);
    return MP_OBJ_FROM_PTR(o);
}

STATIC mp_obj_t mp_obj_new_ge25519_r(mp_obj_t r){
    if (r == mp_const_none){
        return mp_obj_new_ge25519();
    }

    assert_ge25519(r);
    return r;
}

STATIC void mp_unpack_ge25519(ge25519 * r, const mp_obj_t arg, mp_int_t offset){
    mp_buffer_info_t buff;
    mp_get_buffer_raise(arg, &buff, MP_BUFFER_READ);
    if (buff.len < 32 + offset) {
        mp_raise_ValueError("Invalid length of the EC point");
    }

    const int res = ge25519_unpack_vartime(r, ((uint8_t*)buff.buf) + offset);
    if (res != 1){
        mp_raise_ValueError("Point decoding error");
    }
}

STATIC void mp_unpack_scalar(bignum256modm r, const mp_obj_t arg, mp_int_t offset){
    mp_buffer_info_t buff;
    mp_get_buffer_raise(arg, &buff, MP_BUFFER_READ);
    if (buff.len < 32 + offset) {
        mp_raise_ValueError("Invalid length of secret key");
    }
    expand256_modm(r, ((uint8_t*)buff.buf) + offset, 32);
}



//
// Constructors
//

/// class Ge25519:
///     '''
///     EC point on ED25519
///     '''
///
///     def __init__(x: Optional[Union[Ge25519, bytes]] = None):
///         '''
///         Constructor
///         '''

STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 1, false);
    mp_obj_ge25519_t *o = m_new_obj(mp_obj_ge25519_t);
    o->base.type = type;

    if (n_args == 0 || args[0] == mp_const_none) {
        ge25519_set_neutral(&o->p);
    } else if (n_args == 1 && MP_OBJ_IS_GE25519(args[0])) {
        ge25519_copy(&o->p, &MP_OBJ_C_GE25519(args[0]));
    } else if (n_args == 1 && MP_OBJ_IS_STR_OR_BYTES(args[0])) {
        mp_unpack_ge25519(&o->p, args[0], 0);
    } else {
        mp_raise_ValueError("Invalid ge25519 constructor");
    }

    return MP_OBJ_FROM_PTR(o);
}

STATIC mp_obj_t mod_trezorcrypto_monero_ge25519___del__(mp_obj_t self) {
    mp_obj_ge25519_t *o = MP_OBJ_TO_PTR(self);
    memzero(&(o->p), sizeof(ge25519));
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_monero_ge25519___del___obj, mod_trezorcrypto_monero_ge25519___del__);


/// class Sc25519:
///     '''
///     EC scalar on SC25519
///     '''
///
///     def __init__(x: Optional[Union[Sc25519, bytes, int]] = None):
///         '''
///         Constructor
///         '''
///
///
STATIC mp_obj_t mod_trezorcrypto_monero_bignum256modm_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 1, false);
    mp_obj_bignum256modm_t *o = m_new_obj(mp_obj_bignum256modm_t);
    o->base.type = type;

    if (n_args == 0 || args[0] == mp_const_none) {
        set256_modm(o->p, 0);
    } else if (n_args == 1 && MP_OBJ_IS_SCALAR(args[0])) {
        copy256_modm(o->p, MP_OBJ_C_SCALAR(args[0]));
    } else if (n_args == 1 && MP_OBJ_IS_STR_OR_BYTES(args[0])) {
        mp_unpack_scalar(o->p, args[0], 0);
    } else if (n_args == 1 && mp_obj_is_integer(args[0])) {
        uint64_t v = mp_obj_get_uint64(args[0]);
        set256_modm(o->p, v);
    } else {
        mp_raise_ValueError("Invalid scalar constructor");
    }

    return MP_OBJ_FROM_PTR(o);
}

STATIC mp_obj_t mod_trezorcrypto_monero_bignum256modm___del__(mp_obj_t self) {
    mp_obj_bignum256modm_t *o = MP_OBJ_TO_PTR(self);
    memzero(o->p, sizeof(bignum256modm));
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_monero_bignum256modm___del___obj, mod_trezorcrypto_monero_bignum256modm___del__);


/// class Hasher:
///     '''
///     XMR hasher
///     '''
///
///     def __init__(x: Optional[bytes] = None):
///         '''
///         Constructor
///         '''
///
///    def update(buffer: bytes):
///         '''
///         Update hasher
///         '''
///
///    def digest() -> bytes:
///         '''
///         Computes digest
///         '''
///
///    def copy() -> Hasher:
///         '''
///         Creates copy of the hasher, preserving the state
///         '''
///
///
STATIC mp_obj_t mod_trezorcrypto_monero_hasher_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 0, 1, false);
  mp_obj_hasher_t *o = m_new_obj(mp_obj_hasher_t);
  o->base.type = type;
  xmr_hasher_init(&(o->h));

  if (n_args == 1 && MP_OBJ_IS_STR_OR_BYTES(args[0])) {
    mp_buffer_info_t buff;
    mp_get_buffer_raise(args[0], &buff, MP_BUFFER_READ);
    xmr_hasher_update(&o->h, buff.buf, buff.len);
  }

  return MP_OBJ_FROM_PTR(o);
}

STATIC mp_obj_t mod_trezorcrypto_monero_hasher___del__(mp_obj_t self) {
  mp_obj_hasher_t *o = MP_OBJ_TO_PTR(self);
  memzero(&(o->h), sizeof(Hasher));
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_monero_hasher___del___obj, mod_trezorcrypto_monero_hasher___del__);


//
// Scalar defs
//

/// mock:global

/// def init256_modm(dst: Optional[Sc25519], val: Union[int, bytes, Sc25519]) -> Sc25519:
///     '''
///     Initializes Sc25519 scalar
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_init256_modm(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 2;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);

    if (n_args == 0 || args[0] == mp_const_none) {
        set256_modm(MP_OBJ_SCALAR(res), 0);
    } else if (n_args > 0 && MP_OBJ_IS_SCALAR(args[1+off])) {
        copy256_modm(MP_OBJ_SCALAR(res), MP_OBJ_C_SCALAR(args[1+off]));
    } else if (n_args > 0 && MP_OBJ_IS_STR_OR_BYTES(args[1+off])) {
        mp_unpack_scalar(MP_OBJ_SCALAR(res), args[1+off], 0);
    } else if (n_args > 0 && mp_obj_is_integer(args[1+off])) {
        uint64_t v = mp_obj_get_uint64(args[1+off]);
        set256_modm(MP_OBJ_SCALAR(res), v);
    } else {
        mp_raise_ValueError("Invalid scalar def");
    }
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_init256_modm_obj, 0, 2, mod_trezorcrypto_monero_init256_modm);

/// def check256_modm(val: Sc25519):
///     '''
///     Throws exception if scalar is invalid
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_check256_modm(const mp_obj_t arg){
    assert_scalar(arg);
    if (check256_modm(MP_OBJ_C_SCALAR(arg)) != 1){
        mp_raise_ValueError("Ed25519 scalar invalid");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_monero_check256_modm_obj, mod_trezorcrypto_monero_check256_modm);

/// def iszero256_modm(val: Sc25519) -> bool:
///     '''
///     Returns False if the scalar is zero
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_iszero256_modm(const mp_obj_t arg){
    assert_scalar(arg);
    const int r = iszero256_modm(MP_OBJ_C_SCALAR(arg));
    return mp_obj_new_int(r);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_monero_iszero256_modm_obj, mod_trezorcrypto_monero_iszero256_modm);

/// def eq256_modm(a: Sc25519, b: Sc25519) -> int:
///     '''
///     Compares scalars, returns 1 on the same value
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_eq256_modm(const mp_obj_t a, const mp_obj_t b){
    assert_scalar(a);
    assert_scalar(b);
    int r = eq256_modm(MP_OBJ_C_SCALAR(a), MP_OBJ_C_SCALAR(b));
    return MP_OBJ_NEW_SMALL_INT(r);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_monero_eq256_modm_obj, mod_trezorcrypto_monero_eq256_modm);


/// def get256_modm(a: Sc25519) -> int:
///     '''
///     Extracts 64bit integer from the scalar. Raises exception if scalar is bigger than 2^64
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_get256_modm(const mp_obj_t arg){
    assert_scalar(arg);
    uint64_t v;
    if (!get256_modm(&v, MP_OBJ_C_SCALAR(arg))){
        mp_raise_ValueError("Ed25519 scalar too big");
    }
    return mp_obj_new_int_from_ull(v);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_monero_get256_modm_obj, mod_trezorcrypto_monero_get256_modm);


/// def add256_modm(r: Optional[Sc25519], a: Sc25519, b: Sc25519) -> Sc25519:
///     '''
///     Scalar addition
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_add256_modm(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 3;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);

    assert_scalar(args[1+off]);
    assert_scalar(args[2+off]);
    add256_modm(MP_OBJ_SCALAR(res), MP_OBJ_C_SCALAR(args[1+off]), MP_OBJ_C_SCALAR(args[2+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_add256_modm_obj, 2, 3, mod_trezorcrypto_monero_add256_modm);

/// def sub256_modm(r: Optional[Sc25519], a: Sc25519, b: Sc25519) -> Sc25519:
///     '''
///     Scalar subtraction
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_sub256_modm(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 3;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);

    assert_scalar(args[1+off]);
    assert_scalar(args[2+off]);
    sub256_modm(MP_OBJ_SCALAR(res), MP_OBJ_C_SCALAR(args[1+off]), MP_OBJ_C_SCALAR(args[2+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_sub256_modm_obj, 2, 3, mod_trezorcrypto_monero_sub256_modm);

/// def mul256_modm(r: Optional[Sc25519], a: Sc25519, b: Sc25519) -> Sc25519:
///     '''
///     Scalar multiplication
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_mul256_modm(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 3;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);

    assert_scalar(args[1+off]);
    assert_scalar(args[2+off]);
    mul256_modm(MP_OBJ_SCALAR(res), MP_OBJ_C_SCALAR(args[1+off]), MP_OBJ_C_SCALAR(args[2+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_mul256_modm_obj, 2, 3, mod_trezorcrypto_monero_mul256_modm);

/// def mulsub256_modm(r: Optional[Sc25519], a: Sc25519, b: Sc25519, c: Sc25519) -> Sc25519:
///     '''
///     c - a*b
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_mulsub256_modm(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 4;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);

    assert_scalar(args[1+off]);
    assert_scalar(args[2+off]);
    assert_scalar(args[3+off]);
    mulsub256_modm(MP_OBJ_SCALAR(res), MP_OBJ_C_SCALAR(args[1+off]), MP_OBJ_C_SCALAR(args[2+off]), MP_OBJ_C_SCALAR(args[3+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_mulsub256_modm_obj, 3, 4, mod_trezorcrypto_monero_mulsub256_modm);

/// def muladd256_modm(r: Optional[Sc25519], a: Sc25519, b: Sc25519, c: Sc25519) -> Sc25519:
///     '''
///     c + a*b
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_muladd256_modm(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 4;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);

    assert_scalar(args[1+off]);
    assert_scalar(args[2+off]);
    assert_scalar(args[3+off]);
    muladd256_modm(MP_OBJ_SCALAR(res), MP_OBJ_C_SCALAR(args[1+off]), MP_OBJ_C_SCALAR(args[2+off]), MP_OBJ_C_SCALAR(args[3+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_muladd256_modm_obj, 3, 4, mod_trezorcrypto_monero_muladd256_modm);

/// def inv256_modm(r: Optional[Sc25519], a: Sc25519) -> Sc25519:
///     '''
///     Scalar modular inversion
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_inv256_modm(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 2;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);
    assert_scalar(args[1+off]);

    // bn_prime = curve order, little endian encoded
    bignum256 bn_prime = {.val={0x1cf5d3ed, 0x20498c69, 0x2f79cd65, 0x37be77a8, 0x14, 0x0, 0x0, 0x0, 0x1000}};
    bignum256 bn_x;

    memcpy(&bn_x.val, MP_OBJ_C_SCALAR(args[1+off]), sizeof(bignum256modm));
    bn_inverse(&bn_x, &bn_prime);
    memcpy(MP_OBJ_SCALAR(res), bn_x.val, sizeof(bignum256modm));

    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_inv256_modm_obj, 1, 2, mod_trezorcrypto_monero_inv256_modm);

/// def pack256_modm(r: Optional[bytes], a: Sc25519, offset: Optional[int] = 0) -> bytes:
///     '''
///     Scalar compression
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_pack256_modm(size_t n_args, const mp_obj_t *args){
    if (n_args == 1 || args[0] == mp_const_none){
        assert_scalar(args[0]);
        uint8_t buff[32];
        contract256_modm(buff, MP_OBJ_C_SCALAR(args[0]));
        return mp_obj_new_bytes(buff, 32);

    } else {
        mp_buffer_info_t bufm;
        mp_get_buffer_raise(args[0], &bufm, MP_BUFFER_WRITE);
        const mp_int_t offset = n_args >= 3 ?  mp_obj_get_int(args[2]) : 0;
        if (bufm.len < 32 + offset) {
            mp_raise_ValueError("Buffer too small");
        }

        contract256_modm(((uint8_t*)bufm.buf) + offset, MP_OBJ_C_SCALAR(args[1]));
        return args[0];
    }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_pack256_modm_obj, 1, 3, mod_trezorcrypto_monero_pack256_modm);

/// def unpack256_modm(r: Optional[Sc25519], a: bytes, offset: int = 0) -> Sc25519:
///     '''
///     Scalar decompression
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_unpack256_modm(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args >= 2;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);
    const mp_int_t offset = n_args >= 3 ?  mp_obj_get_int(args[2]) : 0;
    mp_unpack_scalar(MP_OBJ_SCALAR(res), args[1+off], offset);
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_unpack256_modm_obj, 1, 3, mod_trezorcrypto_monero_unpack256_modm);

/// def unpack256_modm_noreduce(r: Optional[Sc25519], a: bytes, offset: int = 0) -> Sc25519:
///     '''
///     Scalar decompression, raw, without modular reduction
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_unpack256_modm_noreduce(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args >= 2;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);
    const mp_int_t offset = n_args >= 3 ?  mp_obj_get_int(args[2]) : 0;

    mp_buffer_info_t buff;
    mp_get_buffer_raise(args[1+off], &buff, MP_BUFFER_READ);
    if (buff.len != 32 + offset) {
        mp_raise_ValueError("Invalid length of secret key");
    }

    expand_raw256_modm(MP_OBJ_SCALAR(res), ((uint8_t*)buff.buf) + offset);
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_unpack256_modm_noreduce_obj, 1, 3, mod_trezorcrypto_monero_unpack256_modm_noreduce);

//
// GE25519 Defs
//

/// def ge25519_set_neutral(r: Optional[Ge25519]) -> Ge25519:
///     '''
///     Sets neutral point
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_set_neutral(size_t n_args, const mp_obj_t *args){
    mp_obj_t res = mp_obj_new_ge25519_r(n_args == 1 ? args[0] : mp_const_none);
    ge25519_set_neutral(&MP_OBJ_GE25519(res));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_set_neutral_obj, 0, 1, mod_trezorcrypto_monero_ge25519_set_neutral);

/// def ge25519_set_xmr_h(r: Optional[Ge25519]) -> Ge25519:
///     '''
///     Sets H point
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_set_xmr_h(size_t n_args, const mp_obj_t *args){
    mp_obj_t res = mp_obj_new_ge25519_r(n_args == 1 ? args[0] : mp_const_none);
    ge25519_set_xmr_h(&MP_OBJ_GE25519(res));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_set_xmr_h_obj, 0, 1, mod_trezorcrypto_monero_ge25519_set_xmr_h);

/// def ge25519_check(r: Ge25519):
///     '''
///     Checks point, throws if not on curve
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_check(const mp_obj_t arg){
  assert_ge25519(arg);
  if (ge25519_check(&MP_OBJ_C_GE25519(arg)) != 1){
    mp_raise_ValueError("Ed25519 point not on curve");
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_monero_ge25519_check_obj, mod_trezorcrypto_monero_ge25519_check);

/// def ge25519_eq(a: Ge25519, b: Ge25519) -> bool:
///     '''
///     Compares EC points
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_eq(const mp_obj_t a, const mp_obj_t b){
    assert_ge25519(a);
    assert_ge25519(b);
    int r = ge25519_eq(&MP_OBJ_C_GE25519(a), &MP_OBJ_C_GE25519(b));
    return MP_OBJ_NEW_SMALL_INT(r);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_monero_ge25519_eq_obj, mod_trezorcrypto_monero_ge25519_eq);

/// def ge25519_add(r: Optional[Ge25519], a: Ge25519, b: Ge25519) -> Ge25519:
///     '''
///     Adds EC points
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_add(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 3;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);

    assert_ge25519(args[1+off]);
    assert_ge25519(args[2+off]);
    ge25519_add(&MP_OBJ_GE25519(res), &MP_OBJ_C_GE25519(args[1+off]), &MP_OBJ_C_GE25519(args[2+off]), 0);
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_add_obj, 2, 3, mod_trezorcrypto_monero_ge25519_add);

/// def ge25519_sub(r: Optional[Ge25519], a: Ge25519, b: Ge25519) -> Ge25519:
///     '''
///     Subtracts EC points
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_sub(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 3;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);

    assert_ge25519(args[1+off]);
    assert_ge25519(args[2+off]);
    ge25519_add(&MP_OBJ_GE25519(res), &MP_OBJ_C_GE25519(args[1+off]), &MP_OBJ_C_GE25519(args[2+off]), 1);
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_sub_obj, 2, 3, mod_trezorcrypto_monero_ge25519_sub);

/// def ge25519_double(r: Optional[Ge25519], p: Ge25519) -> Ge25519:
///     '''
///     EC point doubling
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_double(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 2;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    mp_obj_t src = res_arg ? args[1] : args[0];
    assert_ge25519(src);
    ge25519_double(&MP_OBJ_GE25519(res), &MP_OBJ_C_GE25519(src));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_double_obj, 1, 2, mod_trezorcrypto_monero_ge25519_double);

/// def ge25519_mul8(r: Optional[Ge25519], p: Ge25519) -> Ge25519:
///     '''
///     EC point * 8
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_mul8(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 2;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    mp_obj_t src = res_arg ? args[1] : args[0];
    assert_ge25519(src);
    ge25519_mul8(&MP_OBJ_GE25519(res), &MP_OBJ_C_GE25519(src));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_mul8_obj, 1, 2, mod_trezorcrypto_monero_ge25519_mul8);

/// def ge25519_double_scalarmult_vartime(r: Optional[Ge25519], p1: Ge25519, s1: Sc25519, s2: Sc25519) -> Ge25519:
///     '''
///     s1 * G + s2 * p1
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_double_scalarmult_vartime(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 4;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    assert_ge25519(args[1+off]);
    assert_scalar(args[2+off]);
    assert_scalar(args[3+off]);

    ge25519_double_scalarmult_vartime(&MP_OBJ_GE25519(res), &MP_OBJ_C_GE25519(args[1+off]),
                                      MP_OBJ_C_SCALAR(args[2+off]), MP_OBJ_C_SCALAR(args[3+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_double_scalarmult_vartime_obj, 3, 4, mod_trezorcrypto_monero_ge25519_double_scalarmult_vartime);

/// def ge25519_double_scalarmult_vartime2(r: Optional[Ge25519], p1: Ge25519, s1: Sc25519, p2: Ge25519, s2: Sc25519) -> Ge25519:
///     '''
///     s1 * p1 + s2 * p2
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_double_scalarmult_vartime2(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 5;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);

    assert_ge25519(args[1+off]);
    assert_scalar(args[2+off]);
    assert_ge25519(args[3+off]);
    assert_scalar(args[4+off]);

    ge25519_double_scalarmult_vartime2(&MP_OBJ_GE25519(res), &MP_OBJ_C_GE25519(args[1+off]),  MP_OBJ_C_SCALAR(args[2+off]),
                                       &MP_OBJ_C_GE25519(args[3+off]), MP_OBJ_C_SCALAR(args[4+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_double_scalarmult_vartime2_obj, 4, 5, mod_trezorcrypto_monero_ge25519_double_scalarmult_vartime2);

/// def ge25519_scalarmult_base(r: Optional[Ge25519], s: Union[Sc25519, int]) -> Ge25519:
///     '''
///     s * G
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_scalarmult_base(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 2;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);

    if (MP_OBJ_IS_SCALAR(args[1+off])){
        ge25519_scalarmult_base_wrapper(&MP_OBJ_GE25519(res), MP_OBJ_C_SCALAR(args[1+off]));
    } else if (mp_obj_is_integer(args[1+off])){
        bignum256modm mlt;
        set256_modm(mlt, mp_obj_get_int(args[1+off]));
        ge25519_scalarmult_base_wrapper(&MP_OBJ_GE25519(res), mlt);
    } else {
        mp_raise_ValueError("unknown base mult type");
    }

    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_scalarmult_base_obj, 1, 2, mod_trezorcrypto_monero_ge25519_scalarmult_base);

/// def ge25519_scalarmult(r: Optional[Ge25519], p: Ge25519, s: Union[Sc25519, int]) -> Ge25519:
///     '''
///     s * p
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_scalarmult(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 3;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    assert_ge25519(args[1+off]);

    if (MP_OBJ_IS_SCALAR(args[2+off])){
        ge25519_scalarmult(&MP_OBJ_GE25519(res), &MP_OBJ_C_GE25519(args[1+off]), MP_OBJ_C_SCALAR(args[2+off]));
    } else if (mp_obj_is_integer(args[2+off])){
        bignum256modm mlt;
        set256_modm(mlt, mp_obj_get_int(args[2+off]));
        ge25519_scalarmult(&MP_OBJ_GE25519(res), &MP_OBJ_C_GE25519(args[1+off]), mlt);
    } else {
        mp_raise_ValueError("unknown mult type");
    }

    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_scalarmult_obj, 2, 3, mod_trezorcrypto_monero_ge25519_scalarmult);

/// def ge25519_pack(r: bytes, p: Ge25519, offset: int = 0) -> bytes:
///     '''
///     Point compression
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_pack(size_t n_args, const mp_obj_t *args){
    if (n_args == 1 || args[0] == mp_const_none){
        assert_ge25519(args[0]);
        uint8_t buff[32];
        ge25519_pack(buff, &MP_OBJ_C_GE25519(args[0]));
        return mp_obj_new_bytes(buff, 32);

    } else {
        mp_buffer_info_t bufm;
        mp_get_buffer_raise(args[0], &bufm, MP_BUFFER_WRITE);
        const mp_int_t offset = n_args >= 3 ?  mp_obj_get_int(args[2]) : 0;
        if (bufm.len < 32 + offset) {
            mp_raise_ValueError("Buffer too small");
        }

        ge25519_pack(((uint8_t*)bufm.buf) + offset, &MP_OBJ_C_GE25519(args[1]));
        return args[0];
    }

}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_pack_obj, 1, 3, mod_trezorcrypto_monero_ge25519_pack);

/// def ge25519_unpack_vartime(r: Optional[Ge25519], buff: bytes, offset: int = 0) -> Ge25519:
///     '''
///     Point decompression
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_ge25519_unpack_vartime(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args >= 2;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    const mp_int_t offset = n_args >= 3 ?  mp_obj_get_int(args[2]) : 0;
    mp_unpack_ge25519(&MP_OBJ_GE25519(res), args[1+off], offset);
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_ge25519_unpack_vartime_obj, 1, 3, mod_trezorcrypto_monero_ge25519_unpack_vartime);

//
// XMR defs
//

/// def base58_addr_encode_check(tag: int, buff: bytes) -> bytes:
///     '''
///     Monero block base 58 encoding
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_base58_addr_encode_check(size_t n_args, const mp_obj_t *args){
    uint8_t out[128];
    mp_buffer_info_t data;
    mp_get_buffer_raise(args[1], &data, MP_BUFFER_READ);

    int sz = xmr_base58_addr_encode_check(mp_obj_get_int(args[0]), data.buf, data.len, (char *)out, sizeof(out));
    if (sz == 0){
        mp_raise_ValueError("b58 encoding error");
    }

    return mp_obj_new_bytes(out, sz);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_base58_addr_encode_check_obj, 2, 2, mod_trezorcrypto_monero_xmr_base58_addr_encode_check);

/// def base58_addr_decode_check(buff: bytes) -> Tuple[bytes, int]:
///     '''
///     Monero block base 58 decoding, returning (decoded, tag) or raising on error.
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_base58_addr_decode_check(size_t n_args, const mp_obj_t *args){
    uint8_t out[128];
    uint64_t tag;

    mp_buffer_info_t data;
    mp_get_buffer_raise(args[0], &data, MP_BUFFER_READ);

    int sz = xmr_base58_addr_decode_check(data.buf, data.len, &tag, out, sizeof(out));
    if (sz == 0){
        mp_raise_ValueError("b58 decoding error");
    }

    mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
    tuple->items[0] = mp_obj_new_bytes(out, sz);
    tuple->items[1] = mp_obj_new_int_from_ull(tag);
    return MP_OBJ_FROM_PTR(tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_base58_addr_decode_check_obj, 1, 1, mod_trezorcrypto_monero_xmr_base58_addr_decode_check);

/// def xmr_random_scalar(r: Optional[Sc25519] = None) -> Sc25519:
///     '''
///     Generates a random scalar
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_random_scalar(size_t n_args, const mp_obj_t *args){
    mp_obj_t res = mp_obj_new_scalar_r(n_args == 1 ? args[0] : mp_const_none);
    xmr_random_scalar(MP_OBJ_SCALAR(res));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_random_scalar_obj, 0, 1, mod_trezorcrypto_monero_xmr_random_scalar);

/// def xmr_fast_hash(r: Optional[bytes], buff: bytes) -> bytes:
///     '''
///     XMR fast hash
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_fast_hash(size_t n_args, const mp_obj_t *args){
    const int off = n_args == 2 ? 0 : -1;
    uint8_t buff[32];
    uint8_t * buff_use = buff;
    if (n_args > 1){
        mp_buffer_info_t odata;
        mp_get_buffer_raise(args[0], &odata, MP_BUFFER_WRITE);
        if (odata.len < 32){
            mp_raise_ValueError("Output buffer too small");
        }
        buff_use = odata.buf;
    }

    mp_buffer_info_t data;
    mp_get_buffer_raise(args[1+off], &data, MP_BUFFER_READ);
    xmr_fast_hash(buff_use, data.buf, data.len);
    return n_args == 2 ? args[0] : mp_obj_new_bytes(buff, 32);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_fast_hash_obj, 1, 2, mod_trezorcrypto_monero_xmr_fast_hash);

/// def xmr_hash_to_ec(r: Optional[Ge25519], buff: bytes) -> Ge25519:
///     '''
///     XMR hashing to EC point
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_hash_to_ec(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 2;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    mp_buffer_info_t data;
    mp_get_buffer_raise(args[1+off], &data, MP_BUFFER_READ);
    xmr_hash_to_ec(&MP_OBJ_GE25519(res), data.buf, data.len);
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_hash_to_ec_obj, 1, 2, mod_trezorcrypto_monero_xmr_hash_to_ec);

/// def xmr_hash_to_scalar(r: Optional[Sc25519], buff: bytes) -> Sc25519:
///     '''
///     XMR hashing to EC scalar
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_hash_to_scalar(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 2;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);
    mp_buffer_info_t data;
    mp_get_buffer_raise(args[1+off], &data, MP_BUFFER_READ);
    xmr_hash_to_scalar(MP_OBJ_SCALAR(res), data.buf, data.len);
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_hash_to_scalar_obj, 1, 2, mod_trezorcrypto_monero_xmr_hash_to_scalar);

/// def xmr_derivation_to_scalar(r: Optional[Sc25519], p: Ge25519, output_index: int) -> Sc25519:
///     '''
///     H_s(derivation || varint(output_index))
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_derivation_to_scalar(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 3;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);
    assert_ge25519(args[1+off]);
    xmr_derivation_to_scalar(MP_OBJ_SCALAR(res), &MP_OBJ_C_GE25519(args[1+off]), mp_obj_get_int(args[2+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_derivation_to_scalar_obj, 2, 3, mod_trezorcrypto_monero_xmr_derivation_to_scalar);

/// def xmr_generate_key_derivation(r: Optional[Ge25519], A: Ge25519, b: Sc25519) -> Ge25519:
///     '''
///     8*(key2*key1)
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_generate_key_derivation(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 3;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    assert_ge25519(args[1+off]);
    assert_scalar(args[2+off]);
    xmr_generate_key_derivation(&MP_OBJ_GE25519(res), &MP_OBJ_C_GE25519(args[1+off]), MP_OBJ_C_SCALAR(args[2+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_generate_key_derivation_obj, 2, 3, mod_trezorcrypto_monero_xmr_generate_key_derivation);

/// def xmr_derive_private_key(r: Optional[Sc25519], deriv: Ge25519, idx: int, base: Sc25519) -> Sc25519:
///     '''
///     base + H_s(derivation || varint(output_index))
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_derive_private_key(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 4;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);
    assert_ge25519(args[1+off]);
    assert_scalar(args[3+off]);
    xmr_derive_private_key(MP_OBJ_SCALAR(res), &MP_OBJ_C_GE25519(args[1+off]), mp_obj_get_int(args[2+off]), MP_OBJ_C_SCALAR(args[3+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_derive_private_key_obj, 3, 4, mod_trezorcrypto_monero_xmr_derive_private_key);

/// def xmr_derive_public_key(r: Optional[Ge25519], deriv: Ge25519, idx: int, base: Ge25519) -> Ge25519:
///     '''
///     H_s(derivation || varint(output_index))G + base
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_derive_public_key(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 4;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    assert_ge25519(args[1+off]);
    assert_ge25519(args[3+off]);
    xmr_derive_public_key(&MP_OBJ_GE25519(res), &MP_OBJ_C_GE25519(args[1+off]), mp_obj_get_int(args[2+off]), &MP_OBJ_C_GE25519(args[3+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_derive_public_key_obj, 3, 4, mod_trezorcrypto_monero_xmr_derive_public_key);

/// def xmr_add_keys2(r: Optional[Ge25519], a: Sc25519, b: Sc25519, B: Ge25519) -> Ge25519:
///     '''
///     aG + bB, G is basepoint
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_add_keys2(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 4;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    assert_scalar(args[1+off]);
    assert_scalar(args[2+off]);
    assert_ge25519(args[3+off]);
    xmr_add_keys2(&MP_OBJ_GE25519(res), MP_OBJ_SCALAR(args[1+off]), MP_OBJ_SCALAR(args[2+off]), &MP_OBJ_C_GE25519(args[3+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_add_keys2_obj, 3, 4, mod_trezorcrypto_monero_xmr_add_keys2);

/// def xmr_add_keys2_vartime(r: Optional[Ge25519], a: Sc25519, b: Sc25519, B: Ge25519) -> Ge25519:
///     '''
///     aG + bB, G is basepoint
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_add_keys2_vartime(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 4;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    assert_scalar(args[1+off]);
    assert_scalar(args[2+off]);
    assert_ge25519(args[3+off]);
    xmr_add_keys2_vartime(&MP_OBJ_GE25519(res), MP_OBJ_SCALAR(args[1+off]), MP_OBJ_SCALAR(args[2+off]), &MP_OBJ_C_GE25519(args[3+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_add_keys2_vartime_obj, 3, 4, mod_trezorcrypto_monero_xmr_add_keys2_vartime);

/// def xmr_add_keys3(r: Optional[Ge25519], a: Sc25519, A: Ge25519, b: Sc25519, B: Ge25519) -> Ge25519:
///     '''
///     aA + bB
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_add_keys3(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 5;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    assert_scalar(args[1+off]);
    assert_ge25519(args[2+off]);
    assert_scalar(args[3+off]);
    assert_ge25519(args[4+off]);
    xmr_add_keys3(&MP_OBJ_GE25519(res),
                  MP_OBJ_SCALAR(args[1+off]), &MP_OBJ_C_GE25519(args[2+off]),
                  MP_OBJ_SCALAR(args[3+off]), &MP_OBJ_C_GE25519(args[4+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_add_keys3_obj, 4, 5, mod_trezorcrypto_monero_xmr_add_keys3);

/// def xmr_add_keys3_vartime(r: Optional[Ge25519], a: Sc25519, A: Ge25519, b: Sc25519, B: Ge25519) -> Ge25519:
///     '''
///     aA + bB
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_add_keys3_vartime(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 5;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    assert_scalar(args[1+off]);
    assert_ge25519(args[2+off]);
    assert_scalar(args[3+off]);
    assert_ge25519(args[4+off]);
    xmr_add_keys3_vartime(&MP_OBJ_GE25519(res),
                          MP_OBJ_SCALAR(args[1+off]), &MP_OBJ_C_GE25519(args[2+off]),
                          MP_OBJ_SCALAR(args[3+off]), &MP_OBJ_C_GE25519(args[4+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_add_keys3_vartime_obj, 4, 5, mod_trezorcrypto_monero_xmr_add_keys3_vartime);

/// def xmr_get_subaddress_secret_key(r: Optional[Sc25519], major: int, minor: int, m: Sc25519) -> Sc25519:
///     '''
///     Hs(SubAddr || a || index_major || index_minor)
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_get_subaddress_secret_key(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 4;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_scalar_r(res_arg ? args[0] : mp_const_none);
    assert_scalar(args[3+off]);
    xmr_get_subaddress_secret_key(MP_OBJ_SCALAR(res), mp_obj_get_int(args[1+off]), mp_obj_get_int(args[2+off]), MP_OBJ_C_SCALAR(args[3+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_get_subaddress_secret_key_obj, 3, 4, mod_trezorcrypto_monero_xmr_get_subaddress_secret_key);

/// def xmr_gen_c(r: Optional[Ge25519], a: Sc25519, amount: int) -> Ge25519:
///     '''
///     aG + amount * H
///     '''
STATIC mp_obj_t mod_trezorcrypto_monero_xmr_gen_c(size_t n_args, const mp_obj_t *args){
    const bool res_arg = n_args == 3;
    const int off = res_arg ? 0 : -1;
    mp_obj_t res = mp_obj_new_ge25519_r(res_arg ? args[0] : mp_const_none);
    assert_scalar(args[1+off]);
    xmr_gen_c(&MP_OBJ_GE25519(res), MP_OBJ_C_SCALAR(args[1+off]), mp_obj_get_uint64(args[2+off]));
    return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_xmr_gen_c_obj, 2, 3, mod_trezorcrypto_monero_xmr_gen_c);

/// def ct_equals(a: bytes, b: bytes) -> bool:
///     '''
///     Constant time buffer comparison
///     '''
STATIC mp_obj_t mod_trezorcrypto_ct_equals(const mp_obj_t a, const mp_obj_t b){
    mp_buffer_info_t buff_a, buff_b;
    mp_get_buffer_raise(a, &buff_a, MP_BUFFER_READ);
    mp_get_buffer_raise(b, &buff_b, MP_BUFFER_READ);

    if (buff_a.len != buff_b.len) {
      return MP_OBJ_NEW_SMALL_INT(0);
    }

    int r = ed25519_verify(buff_a.buf, buff_b.buf, buff_a.len);
    return MP_OBJ_NEW_SMALL_INT(r);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_ct_equals_obj, mod_trezorcrypto_ct_equals);

// Hasher
STATIC mp_obj_t mod_trezorcrypto_monero_hasher_update(mp_obj_t self, const mp_obj_t arg){
    mp_obj_hasher_t *o = MP_OBJ_TO_PTR(self);
    mp_buffer_info_t buff;
    mp_get_buffer_raise(arg, &buff, MP_BUFFER_READ);
    if (buff.len > 0) {
      xmr_hasher_update(&o->h, buff.buf, buff.len);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_monero_hasher_update_obj, mod_trezorcrypto_monero_hasher_update);

STATIC mp_obj_t mod_trezorcrypto_monero_hasher_digest(size_t n_args, const mp_obj_t *args){
    mp_obj_hasher_t *o = MP_OBJ_TO_PTR(args[0]);

    Hasher ctx;
    memcpy(&ctx, &(o->h), sizeof(Hasher));

    uint8_t out[SHA3_256_DIGEST_LENGTH];
    xmr_hasher_final(&ctx, out);
    memset(&ctx, 0, sizeof(SHA3_CTX));

    if (n_args == 1 || args[1] == mp_const_none){
      return mp_obj_new_bytes(out, sizeof(out));

    } else {
      mp_buffer_info_t bufm;
      mp_get_buffer_raise(args[1], &bufm, MP_BUFFER_WRITE);
      const mp_int_t offset = n_args >= 3 ?  mp_obj_get_int(args[2]) : 0;
      if (bufm.len < 32 + offset) {
        mp_raise_ValueError("Buffer too small");
      }

      memcpy((uint8_t*)bufm.buf + offset, out, SHA3_256_DIGEST_LENGTH);
      return args[1];
    }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_monero_hasher_digest_obj, 1, 3, mod_trezorcrypto_monero_hasher_digest);

STATIC mp_obj_t mod_trezorcrypto_monero_hasher_copy(mp_obj_t self){
    mp_obj_hasher_t *o = MP_OBJ_TO_PTR(self);
    mp_obj_hasher_t *cp = m_new_obj(mp_obj_hasher_t);
    cp->base.type = o->base.type;
    memcpy(&(cp->h), &(o->h), sizeof(Hasher));
    return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_monero_hasher_copy_obj, mod_trezorcrypto_monero_hasher_copy);


//
// Type defs
//

STATIC const mp_rom_map_elem_t mod_trezorcrypto_monero_ge25519_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519___del___obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_monero_ge25519_locals_dict, mod_trezorcrypto_monero_ge25519_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_monero_ge25519_type = {
    { &mp_type_type },
    .name = MP_QSTR_Ge25519,
    .make_new = mod_trezorcrypto_monero_ge25519_make_new,
    .locals_dict = (void*)&mod_trezorcrypto_monero_ge25519_locals_dict,
};

STATIC const mp_rom_map_elem_t mod_trezorcrypto_monero_bignum256modm_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_trezorcrypto_monero_bignum256modm___del___obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_monero_bignum256modm_locals_dict, mod_trezorcrypto_monero_bignum256modm_locals_dict_table);


STATIC const mp_obj_type_t mod_trezorcrypto_monero_bignum256modm_type = {
    { &mp_type_type },
    .name = MP_QSTR_Sc25519,
    .make_new = mod_trezorcrypto_monero_bignum256modm_make_new,
    .locals_dict = (void*)&mod_trezorcrypto_monero_bignum256modm_locals_dict,
};

STATIC const mp_rom_map_elem_t mod_trezorcrypto_monero_hasher_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&mod_trezorcrypto_monero_hasher_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_digest), MP_ROM_PTR(&mod_trezorcrypto_monero_hasher_digest_obj) },
    { MP_ROM_QSTR(MP_QSTR_copy), MP_ROM_PTR(&mod_trezorcrypto_monero_hasher_copy_obj) },
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_trezorcrypto_monero_hasher___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_block_size), MP_OBJ_NEW_SMALL_INT(SHA3_256_BLOCK_LENGTH) },
    { MP_ROM_QSTR(MP_QSTR_digest_size), MP_OBJ_NEW_SMALL_INT(SHA3_256_DIGEST_LENGTH) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_monero_hasher_locals_dict, mod_trezorcrypto_monero_hasher_locals_dict_table);


STATIC const mp_obj_type_t mod_trezorcrypto_monero_hasher_type = {
    { &mp_type_type },
    .name = MP_QSTR_hasher,
    .make_new = mod_trezorcrypto_monero_hasher_make_new,
    .locals_dict = (void*)&mod_trezorcrypto_monero_hasher_locals_dict,
};

STATIC const mp_rom_map_elem_t mod_trezorcrypto_monero_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_monero) },
    { MP_ROM_QSTR(MP_QSTR_init256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_init256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_check256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_check256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_iszero256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_iszero256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_eq256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_eq256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_get256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_get256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_add256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_add256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_sub256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_sub256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_mul256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_mul256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_mulsub256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_mulsub256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_muladd256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_muladd256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_inv256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_inv256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_pack256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_pack256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_unpack256_modm), MP_ROM_PTR(&mod_trezorcrypto_monero_unpack256_modm_obj) },
    { MP_ROM_QSTR(MP_QSTR_unpack256_modm_noreduce), MP_ROM_PTR(&mod_trezorcrypto_monero_unpack256_modm_noreduce_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_set_neutral), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_set_neutral_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_set_h), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_set_xmr_h_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_pack), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_pack_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_unpack_vartime), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_unpack_vartime_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_check), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_check_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_eq), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_eq_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_add), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_add_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_sub), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_sub_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_double), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_double_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_mul8), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_mul8_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_double_scalarmult_vartime), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_double_scalarmult_vartime_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_double_scalarmult_vartime2), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_double_scalarmult_vartime2_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_scalarmult_base), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_scalarmult_base_obj) },
    { MP_ROM_QSTR(MP_QSTR_ge25519_scalarmult), MP_ROM_PTR(&mod_trezorcrypto_monero_ge25519_scalarmult_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_base58_addr_encode_check), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_base58_addr_encode_check_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_base58_addr_decode_check), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_base58_addr_decode_check_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_random_scalar), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_random_scalar_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_fast_hash), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_fast_hash_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_hash_to_ec), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_hash_to_ec_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_hash_to_scalar), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_hash_to_scalar_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_derivation_to_scalar), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_derivation_to_scalar_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_generate_key_derivation), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_generate_key_derivation_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_derive_private_key), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_derive_private_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_derive_public_key), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_derive_public_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_add_keys2), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_add_keys2_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_add_keys2_vartime), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_add_keys2_vartime_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_add_keys3), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_add_keys3_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_add_keys3_vartime), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_add_keys3_vartime_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_get_subaddress_secret_key), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_get_subaddress_secret_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_xmr_gen_c), MP_ROM_PTR(&mod_trezorcrypto_monero_xmr_gen_c_obj) },
    { MP_ROM_QSTR(MP_QSTR_ct_equals), MP_ROM_PTR(&mod_trezorcrypto_ct_equals_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_monero_globals, mod_trezorcrypto_monero_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_monero_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mod_trezorcrypto_monero_globals,
};
