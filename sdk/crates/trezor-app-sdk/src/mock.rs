//! Mock implementations for unit testing only.
//!
//! This module provides stub implementations of the Trezor crypto and API interfaces
//! intended exclusively for use in unit tests. It must **not** be used in production builds.
//!
//! Each implementation is explicitly marked as either:
//! - **Functional** — delegates to a real software implementation via a third-party crate.
//! - **Stub** — always returns a fixed error value, zero, `false`, or `null`; does not perform
//!   any real computation.

use mock_hmac_sha256::{HMAC as HMAC256_impl, Hash as Sha256_impl};
use mock_hmac_sha512::{HMAC as HMAC512_impl, Hash as Sha512_impl};
use mock_sha3::digest::FixedOutput;
use mock_sha3::{
    Digest, Keccak256 as Keccak256_impl, Sha3_256 as Sha3_256_impl, Sha3_512 as Sha3_512_impl,
};

use super::crypto::Hasher;
use crate::low_level_api::ffi::*;

static SECP256K1: ecdsa_curve = ecdsa_curve {
    prime: bignum256 {
        val: [
            0x1ffffc2f, 0x1ffffff7, 0x1fffffff, 0x1fffffff, 0x1fffffff, 0x1fffffff, 0x1fffffff,
            0x1fffffff, 0xffffff,
        ],
    },
    G: curve_point {
        x: bignum256 {
            val: [
                0x16f81798, 0x0f940ad8, 0x138a3656, 0x17f9b65b, 0x10b07029, 0x114ae743, 0x0eb15681,
                0x0fdf3b97, 0x79be66,
            ],
        },
        y: bignum256 {
            val: [
                0x1b10d4b8, 0x023e847f, 0x01550667, 0x0f68914d, 0x108a8fd1, 0x1dfe0708, 0x11957693,
                0x0ee4d478, 0x483ada,
            ],
        },
    },
    order: bignum256 {
        val: [
            0x10364141, 0x1e92f466, 0x12280eef, 0x1db9cd5e, 0x1fffebaa, 0x1fffffff, 0x1fffffff,
            0x1fffffff, 0xffffff,
        ],
    },
    order_half: bignum256 {
        val: [
            0x081b20a0, 0x1f497a33, 0x09140777, 0x0edce6af, 0x1ffff5d5, 0x1fffffff, 0x1fffffff,
            0x1fffffff, 0x7fffff,
        ],
    },
    a: 0,
    b: bignum256 {
        val: [7, 0, 0, 0, 0, 0, 0, 0, 0],
    },
};

static NIST256P1: ecdsa_curve = ecdsa_curve {
    prime: bignum256 {
        val: [
            0x1fffffff, 0x1fffffff, 0x1fffffff, 0x000001ff, 0x00000000, 0x00000000, 0x00040000,
            0x1fe00000, 0xffffff,
        ],
    },
    G: curve_point {
        x: bignum256 {
            val: [
                0x1898c296, 0x0509ca2e, 0x1acce83d, 0x06fb025b, 0x040f2770, 0x1372b1d2, 0x091fe2f3,
                0x1e5c2588, 0x6b17d1,
            ],
        },
        y: bignum256 {
            val: [
                0x17bf51f5, 0x1db20341, 0x0c57b3b2, 0x1c66aed6, 0x19e162bc, 0x15a53e07, 0x1e6e3b9f,
                0x1c5fc34f, 0x4fe342,
            ],
        },
    },
    order: bignum256 {
        val: [
            0x1c632551, 0x1dce5617, 0x05e7a13c, 0x0df55b4e, 0x1ffffbce, 0x1fffffff, 0x0003ffff,
            0x1fe00000, 0xffffff,
        ],
    },
    order_half: bignum256 {
        val: [
            0x1e3192a8, 0x0ee72b0b, 0x02f3d09e, 0x06faada7, 0x1ffffde7, 0x1fffffff, 0x0001ffff,
            0x1ff00000, 0x7fffff,
        ],
    },
    a: -3,
    b: bignum256 {
        val: [
            0x07d2604b, 0x1e71e1f1, 0x14ec3d8e, 0x1a0d6198, 0x086bc651, 0x1eaabb4c, 0x0f9ecfae,
            0x1b154752, 0x005ac635,
        ],
    },
};

// Sha3 functions
// All four functions below are **stubs** — they do nothing and return no output.
// The actual SHA-3 / Keccak logic is provided by the [`Keccak256`], [`Sha3_256`],
// and [`Sha3_512`] structs further down in this file.
unsafe extern "C" fn dummy_sha3_256_init(_ctx: *mut SHA3_CTX) {}
unsafe extern "C" fn dummy_sha3_512_init(_ctx: *mut SHA3_CTX) {}
unsafe extern "C" fn dummy_sha3_update(_ctx: *mut SHA3_CTX, _msg: *const u8, _size: usize) {}
unsafe extern "C" fn dummy_keccak_final(_ctx: *mut SHA3_CTX, _result: *mut u8) {}
unsafe extern "C" fn dummy_sha3_final(_ctx: *mut SHA3_CTX, _result: *mut u8) {}

// Sha functions
// All six functions below are **stubs** — they do nothing and write no digest output.
// The actual SHA-256 / SHA-512 logic is provided by the [`Sha256`] and [`Sha512`]
// structs further down in this file.
unsafe extern "C" fn dummy_sha256_init(_ctx: *mut SHA256_CTX) {}
unsafe extern "C" fn dummy_sha256_update(_ctx: *mut SHA256_CTX, _msg: *const u8, _size: usize) {}
unsafe extern "C" fn dummy_sha256_final(_ctx: *mut SHA256_CTX, _digest: *mut u8) {}
unsafe extern "C" fn dummy_sha512_init(_ctx: *mut SHA512_CTX) {}
unsafe extern "C" fn dummy_sha512_update(_ctx: *mut SHA512_CTX, _msg: *const u8, _size: usize) {}
unsafe extern "C" fn dummy_sha512_final(_ctx: *mut SHA512_CTX, _digest: *mut u8) {}

// HMAC functions
// All three functions below are **stubs** — they do nothing and write no HMAC output.
// The actual HMAC-SHA-256 logic is provided by the [`HmacSha256`] struct further down.
unsafe extern "C" fn dummy_hmac_sha256_init(
    _hctx: *mut HMAC_SHA256_CTX,
    _key: *const u8,
    _keylen: u32,
) {
}
unsafe extern "C" fn dummy_hmac_sha256_update(
    _hctx: *mut HMAC_SHA256_CTX,
    _msg: *const u8,
    _msglen: u32,
) {
}
unsafe extern "C" fn dummy_hmac_sha256_final(_hctx: *mut HMAC_SHA256_CTX, _hmac: *mut u8) {}

// ECDSA functions

/// **Stub** — always returns `1` (failure). Does not perform any signature recovery.
unsafe extern "C" fn dummy_ecdsa_recover_pub_from_sig(
    _curve: *const ecdsa_curve,
    _pub_key: *mut u8,
    _sig: *const u8,
    _digest: *const u8,
    _recid: core::ffi::c_int,
) -> core::ffi::c_int {
    1
}

/// **Stub** — always returns `1` (failure). Does not perform any signature verification.
unsafe extern "C" fn dummy_ecdsa_verify_digest(
    _curve: *const ecdsa_curve,
    _pub_key: *const u8,
    _sig: *const u8,
    _digest: *const u8,
) -> core::ffi::c_int {
    1
}

// ED25519 functions

/// **Stub** — always returns `0` (success) without combining any public keys.
unsafe extern "C" fn dummy_ed25519_cosi_combine_publickeys(
    _res: *mut core::ffi::c_uchar,
    _pks: *const ed25519_public_key,
    _n: usize,
) -> core::ffi::c_int {
    0
}

/// **Stub** — always returns `0` (success) without verifying any signature.
unsafe extern "C" fn dummy_ed25519_sign_open(
    _m: *const u8,
    _mlen: usize,
    _pk: *const u8,
    _rs: *const u8,
) -> core::ffi::c_int {
    0
}

pub static DUMMY_TREZOR_CRYPTO_V1: trezor_crypto_v1_t = trezor_crypto_v1_t {
    ed25519_cosi_combine_publickeys: Some(dummy_ed25519_cosi_combine_publickeys),
    ed25519_sign_open: Some(dummy_ed25519_sign_open),
    sha3_256_Init: Some(dummy_sha3_256_init),
    sha3_512_Init: Some(dummy_sha3_512_init),
    sha3_Update: Some(dummy_sha3_update),
    sha3_Final: Some(dummy_sha3_final),
    keccak_Final: Some(dummy_keccak_final),
    sha256_Init: Some(dummy_sha256_init),
    sha256_Update: Some(dummy_sha256_update),
    sha256_Final: Some(dummy_sha256_final),
    sha512_Init: Some(dummy_sha512_init),
    sha512_Update: Some(dummy_sha512_update),
    sha512_Final: Some(dummy_sha512_final),
    hmac_sha256_Init: Some(dummy_hmac_sha256_init),
    hmac_sha256_Update: Some(dummy_hmac_sha256_update),
    hmac_sha256_Final: Some(dummy_hmac_sha256_final),
    ecdsa_recover_pub_from_sig: Some(dummy_ecdsa_recover_pub_from_sig),
    ecdsa_verify_digest: Some(dummy_ecdsa_verify_digest),
    secp256k1: &SECP256K1 as *const ecdsa_curve,
    nist256p1: &NIST256P1 as *const ecdsa_curve,
};

// System / API stubs

/// **Stub** — does nothing. No process exit is performed.
unsafe extern "C" fn dummy_system_exit(_exitcode: core::ffi::c_int) {}

/// **Stub** — does nothing. No error screen is displayed.
unsafe extern "C" fn dummy_system_exit_error(
    _title: *const core::ffi::c_char,
    _message: *const core::ffi::c_char,
    _footer: *const core::ffi::c_char,
) {
}

/// **Stub** — does nothing. No error screen is displayed.
unsafe extern "C" fn dummy_system_exit_error_ex(
    _title: *const core::ffi::c_char,
    _title_len: usize,
    _message: *const core::ffi::c_char,
    _message_len: usize,
    _footer: *const core::ffi::c_char,
    _footer_len: usize,
) {
}

/// **Stub** — does nothing. No fatal error is reported.
unsafe extern "C" fn dummy_system_exit_fatal(
    _message: *const core::ffi::c_char,
    _file: *const core::ffi::c_char,
    _line: core::ffi::c_int,
) {
}

/// **Stub** — does nothing. No fatal error is reported.
unsafe extern "C" fn dummy_system_exit_fatal_ex(
    _message: *const core::ffi::c_char,
    _message_len: usize,
    _file: *const core::ffi::c_char,
    _file_len: usize,
    _line: core::ffi::c_int,
) {
}

/// **Stub** — does nothing and always returns `0`. No data is written to any console.
unsafe extern "C" fn dummy_dbg_console_write(
    _data: *const core::ffi::c_void,
    _size: usize,
) -> isize {
    0
}

/// **Stub** — always returns `0`. Does not read any real hardware tick counter.
unsafe extern "C" fn dummy_systick_ms() -> u32 {
    0
}

/// **Stub** — does nothing. No events are polled; `signalled` is left unmodified.
unsafe extern "C" fn dummy_sysevents_poll(
    _awaited: *const sysevents_t,
    _signalled: *mut sysevents_t,
    _deadline: u32,
) {
}

/// **Stub** — always returns `false`. No IPC inbox is registered.
unsafe extern "C" fn dummy_ipc_register(
    _remote: systask_id_t,
    _buffer: *mut core::ffi::c_void,
    _size: usize,
) -> bool {
    false
}

/// **Stub** — does nothing. No IPC inbox is unregistered.
unsafe extern "C" fn dummy_ipc_unregister(_remote: systask_id_t) {}

/// **Stub** — always returns `false`. No IPC message is ever available.
unsafe extern "C" fn dummy_ipc_try_receive(_msg: *mut ipc_message_t) -> bool {
    false
}

/// **Stub** — does nothing. No IPC message memory is freed.
unsafe extern "C" fn dummy_ipc_message_free(_msg: *mut ipc_message_t) {}

/// **Stub** — always returns `false`. No IPC message is sent.
unsafe extern "C" fn dummy_ipc_send(
    _remote: systask_id_t,
    _fn_: u32,
    _data: *const core::ffi::c_void,
    _data_size: usize,
) -> bool {
    false
}

pub static DUMMY_TREZOR_API_V1: trezor_api_v1_t = trezor_api_v1_t {
    system_exit: Some(dummy_system_exit),
    system_exit_error: Some(dummy_system_exit_error),
    system_exit_error_ex: Some(dummy_system_exit_error_ex),
    system_exit_fatal: Some(dummy_system_exit_fatal),
    system_exit_fatal_ex: Some(dummy_system_exit_fatal_ex),
    dbg_console_write: Some(dummy_dbg_console_write),
    systick_ms: Some(dummy_systick_ms),
    sysevents_poll: Some(dummy_sysevents_poll),
    ipc_register: Some(dummy_ipc_register),
    ipc_unregister: Some(dummy_ipc_unregister),
    ipc_try_receive: Some(dummy_ipc_try_receive),
    ipc_message_free: Some(dummy_ipc_message_free),
    ipc_send: Some(dummy_ipc_send),
    trezor_crypto_v1: &DUMMY_TREZOR_CRYPTO_V1,
};

pub unsafe extern "C" fn dummy_trezor_api_getter_t(version: u32) -> *mut core::ffi::c_void {
    if version == 1 {
        &DUMMY_TREZOR_API_V1 as *const _ as *mut _
    } else {
        core::ptr::null_mut()
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn sdk_init(
    api_get: crate::low_level_api::ffi::trezor_api_getter_t,
) -> core::ffi::c_int {
    // SAFETY: trusting the caller of applet_main to provide us with a valid getter
    unsafe { crate::low_level_api::init(api_get) };
    0
}

// ============================================================================
// Functional hash / HMAC implementations (via third-party crates)
// ============================================================================
//
// All structs below delegate to real software implementations and produce
// correct cryptographic output. They are safe to use in unit tests that
// need to verify hash or HMAC correctness.

// Sha functions

/// **Functional** — delegates to `mock_hmac_sha256::Hash` (software SHA-256).
pub struct Sha256 {
    ctx: Sha256_impl,
}

impl Sha256 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Sha256_impl::new();
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        self.ctx.clone().finalize()
    }
}

impl Drop for Sha256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

impl Hasher for Sha256 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        let digest = self.ctx.clone().finalize();
        output.copy_from_slice(digest.as_slice());
    }
}

/// **Functional** — delegates to `mock_hmac_sha512::Hash` (software SHA-512).
pub struct Sha512 {
    ctx: Sha512_impl,
}

impl Sha512 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Sha512_impl::new();
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 64] {
        self.ctx.clone().finalize()
    }
}

impl Drop for Sha512 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

impl Hasher for Sha512 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        let digest = Sha512::digest(self);
        output.copy_from_slice(digest.as_slice());
    }
}
// Sha3 functions

/// **Functional** — delegates to `mock_sha3::Keccak256` (software Keccak-256).
pub struct Keccak256 {
    ctx: Keccak256_impl,
}

impl Keccak256 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Keccak256_impl::new();
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut out = [0u8; 32];
        Self::finalize(self, &mut out);
        out
    }
}

impl Hasher for Keccak256 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        output.copy_from_slice(self.ctx.clone().finalize_fixed().as_slice());
    }
}

impl Drop for Keccak256 {
    fn drop(&mut self) {
        self.ctx.reset();
    }
}

/// **Functional** — delegates to `mock_sha3::Sha3_256` (software SHA3-256).
pub struct Sha3_256 {
    ctx: Sha3_256_impl,
}

impl Sha3_256 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Sha3_256_impl::new();
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut digest = [0u8; 32];
        Self::finalize(self, &mut digest);
        digest
    }
}

impl Hasher for Sha3_256 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        output.copy_from_slice(self.ctx.clone().finalize_fixed().as_slice());
    }
}

impl Drop for Sha3_256 {
    fn drop(&mut self) {
        self.ctx.reset();
    }
}

/// **Functional** — delegates to `mock_sha3::Sha3_512` (software SHA3-512).
pub struct Sha3_512 {
    ctx: Sha3_512_impl,
}

impl Sha3_512 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Sha3_512_impl::new();
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 64] {
        let mut digest = [0u8; 64];
        Self::finalize(self, &mut digest);
        digest
    }
}

impl Drop for Sha3_512 {
    fn drop(&mut self) {
        self.ctx.reset();
    }
}

impl Hasher for Sha3_512 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        output.copy_from_slice(self.ctx.clone().finalize_fixed().as_slice());
    }
}

// HMAC functions

/// **Functional** — delegates to `mock_hmac_sha256::HMAC` (software HMAC-SHA-256).
pub struct HmacSha256 {
    ctx: HMAC256_impl,
}

impl HmacSha256 {
    pub fn new(key: &[u8], data: Option<&[u8]>) -> Self {
        let ctx = HMAC256_impl::new(key);
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut digest = [0u8; 32];
        Self::finalize(self, &mut digest);
        digest
    }
}

impl Hasher for HmacSha256 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        output.copy_from_slice(self.ctx.clone().finalize().as_slice());
    }
}

impl Drop for HmacSha256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

/// **Functional** — delegates to `mock_hmac_sha512::HMAC` (software HMAC-SHA-512).
pub struct HmacSha512 {
    ctx: HMAC512_impl,
}

impl HmacSha512 {
    pub fn new(key: &[u8], data: Option<&[u8]>) -> Self {
        let ctx = HMAC512_impl::new(key);
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 64] {
        let mut digest = [0u8; 64];
        Self::finalize(self, &mut digest);
        digest
    }
}

impl Hasher for HmacSha512 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        // output.copy_from_slice(self.ctx.clone().finalize().as_slice());
        let ctx = core::mem::replace(&mut self.ctx, HMAC512_impl::new(&[]));
        let digest = ctx.finalize();
        output.copy_from_slice(&digest);
    }
}

impl Drop for HmacSha512 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}
