#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
use ufmt::derive::uDebug;

/// FFI type definitions that mirror the C API without requiring bindgen.
/// These must stay in sync with the actual C types in core/embed/sys/ipc/api.h

/// Function pointer type for getting the API of a requested version.
/// This is passed to applet_main by the firmware.
/// Returns a non-null opaque pointer on success; null if the requested version is unsupported.
pub type trezor_api_getter_t = unsafe extern "C" fn(u32) -> *const core::ffi::c_void;
pub type ipc_fn_t = u32;

/// Current API version numbers
pub const TREZOR_API_VERSION_1: u32 = 1;

/// Maximum IPC message payload size in bytes
// pub const IPC_MSG_PAYLOAD_SIZE: usize = 256;

// pub const SYSHANDLE_SYSCALL: syshandle_t = 10;
pub const SYSHANDLE_IPC0: syshandle_t = 11;
// pub const SYSHANDLE_IPC1: syshandle_t = 12;
// pub const SYSHANDLE_IPC2: syshandle_t = 13;

/// IPC message structure
#[repr(C)]
#[derive(uDebug, Copy, Clone)]
pub struct ipc_message_t {
    pub remote: systask_id_t,
    pub fn_: ipc_fn_t,
    pub data: *const ::core::ffi::c_void,
    pub size: usize,
}

impl Default for ipc_message_t {
    fn default() -> Self {
        Self {
            remote: 0,
            fn_: 0,
            data: core::ptr::null(),
            size: 0,
        }
    }
}

/// System events structure with read/write ready masks
#[repr(C)]
#[derive(uDebug, Default, Copy, Clone)]
pub struct sysevents_t {
    /// Bitmask of handles ready for reading
    pub read_ready: u32,
    /// Bitmask of handles ready for writing
    pub write_ready: u32,
}

/// System handle type
pub type syshandle_t = u32;

/// Zero-based task ID (up to SYSTASK_MAX_TASKS - 1)
pub type systask_id_t = u8;

/// Trezor API v1 function pointers
#[repr(C)]
pub struct trezor_api_v1_t {
    pub system_exit: unsafe extern "C" fn(exitcode: core::ffi::c_int) -> !,
    pub system_exit_error: unsafe extern "C" fn(
        title: *const core::ffi::c_char,
        message: *const core::ffi::c_char,
        footer: *const core::ffi::c_char,
    ) -> !,

    pub system_exit_error_ex: unsafe extern "C" fn(
        title: *const core::ffi::c_char,
        title_len: usize,
        message: *const core::ffi::c_char,
        message_len: usize,
        footer: *const core::ffi::c_char,
        footer_len: usize,
    ) -> !,
    pub system_exit_fatal: unsafe extern "C" fn(
        message: *const core::ffi::c_char,
        file: *const core::ffi::c_char,
        line: core::ffi::c_int,
    ) -> !,
    pub system_exit_fatal_ex: unsafe extern "C" fn(
        message: *const core::ffi::c_char,
        message_len: usize,
        file: *const core::ffi::c_char,
        file_len: usize,
        line: core::ffi::c_int,
    ) -> !,
    pub dbg_console_write: unsafe extern "C" fn(data: *const core::ffi::c_void, size: usize),
    pub systick_ms: unsafe extern "C" fn() -> u32,
    pub sysevents_poll: unsafe extern "C" fn(
        awaited: *const sysevents_t,
        signalled: *mut sysevents_t,
        deadline: u32,
    ),
    pub syshandle_read: unsafe extern "C" fn(
        handle: syshandle_t,
        buffer: *mut core::ffi::c_void,
        buffer_size: usize,
    ) -> isize,

    pub ipc_register: unsafe extern "C" fn(
        remote: systask_id_t,
        buffer: *mut core::ffi::c_void,
        size: usize,
    ) -> bool,
    pub ipc_unregister: unsafe extern "C" fn(remote: systask_id_t),
    pub ipc_try_receive: unsafe extern "C" fn(msg: *mut ipc_message_t) -> bool,
    pub ipc_message_free: unsafe extern "C" fn(msg: *mut ipc_message_t),
    pub ipc_send: unsafe extern "C" fn(
        remote: systask_id_t,
        fn_: u32,
        data: *const core::ffi::c_void,
        data_size: usize,
    ) -> bool,
    pub trezor_crypto_v1_t: *const trezor_crypto_v1_t,
}

// pub type ed25519_signature = [core::ffi::c_uchar; 64usize];
pub type ed25519_public_key = [core::ffi::c_uchar; 32usize];

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct _SHA256_CTX {
    pub state: [u32; 8usize],
    pub bitcount: u64,
    pub buffer: [u32; 16usize],
}
pub type SHA256_CTX = _SHA256_CTX;

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct _SHA512_CTX {
    pub state: [u64; 8usize],
    pub bitcount: [u64; 2usize],
    pub buffer: [u64; 16usize],
}
pub type SHA512_CTX = _SHA512_CTX;

#[repr(C)]
#[derive(Debug)]
pub struct _HMAC_SHA256_CTX {
    pub o_key_pad: [u8; 64usize],
    pub ctx: SHA256_CTX,
}
pub type HMAC_SHA256_CTX = _HMAC_SHA256_CTX;

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct bignum256 {
    pub val: [u32; 9usize],
}

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct curve_point {
    pub x: bignum256,
    pub y: bignum256,
}
#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct ecdsa_curve {
    pub prime: bignum256,
    pub G: curve_point,
    pub order: bignum256,
    pub order_half: bignum256,
    pub a: cty::c_int,
    pub b: bignum256,
}

unsafe extern "C" {
    pub fn ecdsa_recover_pub_from_sig(
        curve: *const ecdsa_curve,
        pub_key: *mut u8,
        sig: *const u8,
        digest: *const u8,
        recid: cty::c_int,
    ) -> cty::c_int;
}
unsafe extern "C" {
    pub static secp256k1: ecdsa_curve;
}



/// Trezor crypto v1 function pointers
#[repr(C)]
pub struct trezor_crypto_v1_t {
    pub ed25519_cosi_combine_publickeys: unsafe extern "C" fn(
        res: *mut core::ffi::c_uchar,
        pks: *const ed25519_public_key,
        n: usize,
    ) -> core::ffi::c_int,
    pub ed25519_sign_open: unsafe extern "C" fn(
        m: *const u8,
        mlen: usize,
        pk: *const u8,
        RS: *const u8,
    ) -> core::ffi::c_int,
    pub sha3_256: unsafe extern "C" fn(data: *const u8, len: usize, digest: *mut u8),
    pub keccak_256: unsafe extern "C" fn(data: *const u8, len: usize, digest: *mut u8),
    pub sha256_Init: unsafe extern "C" fn(arg1: *mut SHA256_CTX),
    pub sha256_Update: unsafe extern "C" fn(arg1: *mut SHA256_CTX, arg2: *const u8, arg3: usize),
    pub sha256_Final: unsafe extern "C" fn(arg1: *mut SHA256_CTX, arg2: *mut u8),
    pub sha512_Init: unsafe extern "C" fn(arg1: *mut SHA512_CTX),
    pub sha512_Update: unsafe extern "C" fn(arg1: *mut SHA512_CTX, arg2: *const u8, arg3: usize),
    pub sha512_Final: unsafe extern "C" fn(arg1: *mut SHA512_CTX, arg2: *mut u8),
    pub hmac_sha256_Init:
        unsafe extern "C" fn(hctx: *mut HMAC_SHA256_CTX, key: *const u8, keylen: u32),
    pub hmac_sha256_Update:
        unsafe extern "C" fn(hctx: *mut HMAC_SHA256_CTX, msg: *const u8, msglen: u32),
    pub hmac_sha256_Final: unsafe extern "C" fn(hctx: *mut HMAC_SHA256_CTX, hmac: *mut u8),
    pub ecdsa_recover_pub_from_sig: unsafe extern "C" fn(
        curve: *const ecdsa_curve,
        pub_key: *mut u8,
        sig: *const u8,
        digest: *const u8,
        recid: cty::c_int,
    ) -> cty::c_int,
    pub secp256k1: *const ecdsa_curve,
}

unsafe impl Sync for trezor_api_v1_t {}
unsafe impl Sync for trezor_crypto_v1_t {}
