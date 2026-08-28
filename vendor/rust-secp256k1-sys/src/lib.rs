// SPDX-License-Identifier: CC0-1.0

//! # secp256k1-sys FFI bindings
//! Direct bindings to the underlying C library functions. These should
//! not be needed for most users.

// Coding conventions
#![deny(non_upper_case_globals, non_camel_case_types, non_snake_case, unused_mut)]

#![cfg_attr(all(not(test), not(feature = "std")), no_std)]
#![cfg_attr(docsrs, feature(doc_auto_cfg))]

#[cfg(any(test, feature = "std"))]
extern crate core;

#[cfg(feature = "alloc")]
extern crate alloc;

#[cfg(secp256k1_fuzz)]
const THIS_UNUSED_CONSTANT_IS_YOUR_WARNING_THAT_ALL_THE_CRYPTO_IN_THIS_LIB_IS_DISABLED_FOR_FUZZING: usize = 0;

mod macros;
pub mod types;

#[cfg(feature = "recovery")]
pub mod recovery;

use core::{slice, ptr};
use core::ptr::NonNull;
use types::*;

/// Flag for context to enable no precomputation
pub const SECP256K1_START_NONE: c_uint = 1;
/// Flag for context to enable verification precomputation
pub const SECP256K1_START_VERIFY: c_uint = 1 | (1 << 8);
/// Flag for context to enable signing precomputation
pub const SECP256K1_START_SIGN: c_uint = 1 | (1 << 9);
/// Flag for keys to indicate uncompressed serialization format
#[allow(unused_parens)]
pub const SECP256K1_SER_UNCOMPRESSED: c_uint = (1 << 1);
/// Flag for keys to indicate compressed serialization format
pub const SECP256K1_SER_COMPRESSED: c_uint = (1 << 1) | (1 << 8);

/// A nonce generation function. Ordinary users of the library
/// never need to see this type; only if you need to control
/// nonce generation do you need to use it. I have deliberately
/// made this hard to do: you have to write your own wrapper
/// around the FFI functions to use it. And it's an unsafe type.
/// Nonces are generated deterministically by RFC6979 by
/// default; there should be no need to ever change this.
pub type NonceFn = Option<unsafe extern "C" fn(
    nonce32: *mut c_uchar,
    msg32: *const c_uchar,
    key32: *const c_uchar,
    algo16: *const c_uchar,
    data: *mut c_void,
    attempt: c_uint,
) -> c_int>;

/// Hash function to use to post-process an ECDH point to get
/// a shared secret.
pub type EcdhHashFn = Option<unsafe extern "C" fn(
    output: *mut c_uchar,
    x: *const c_uchar,
    y: *const c_uchar,
    data: *mut c_void,
) -> c_int>;

///  Same as secp256k1_nonce function with the exception of accepting an
///  additional pubkey argument and not requiring an attempt argument. The pubkey
///  argument can protect signature schemes with key-prefixed challenge hash
///  inputs against reusing the nonce when signing with the wrong precomputed
///  pubkey.
pub type SchnorrNonceFn = Option<unsafe extern "C" fn(
    nonce32: *mut c_uchar,
    msg32: *const c_uchar,
    msg_len: size_t,
    key32: *const c_uchar,
    xonly_pk32: *const c_uchar,
    algo16: *const c_uchar,
    algo_len: size_t,
    data: *mut c_void,
) -> c_int>;

/// A hash function used by `ellswift_ecdh` to hash the final ECDH shared secret.
pub type EllswiftEcdhHashFn = Option<unsafe extern "C" fn(
    output: *mut c_uchar,
    x32: *const c_uchar,
    ell_a64: *const c_uchar,
    ell_b64: *const c_uchar,
    data: *mut c_void,
) -> c_int>;

/// Data structure that contains additional arguments for schnorrsig_sign_custom.
#[repr(C)]
pub struct SchnorrSigExtraParams {
    magic: [c_uchar; 4],
    nonce_fp: SchnorrNonceFn,
    ndata: *const c_void,
}

impl SchnorrSigExtraParams {
    /// Create a new SchnorrSigExtraParams properly initialized.
    ///
    /// `nonce_fp`: pointer to a nonce generation function. If NULL
    /// rustsecp256k1_v0_5_0_nonce_function_bip340 is used
    ///
    /// `ndata`: pointer to arbitrary data used by the nonce generation function
    /// (can be NULL). If it is non-NULL and
    /// rustsecp256k1_v0_5_0_nonce_function_bip340 is used,
    /// then ndata must be a pointer to 32-byte auxiliary randomness as per
    /// BIP-340.
    pub fn new(nonce_fp: SchnorrNonceFn, ndata: *const c_void) -> Self {
        SchnorrSigExtraParams {
            magic: [0xda, 0x6f, 0xb3, 0x8c],
            nonce_fp,
            ndata,
        }
    }
}

/// A Secp256k1 context, containing various precomputed values and such
/// needed to do elliptic curve computations. If you create one of these
/// with `secp256k1_context_create` you MUST destroy it with
/// `secp256k1_context_destroy`, or else you will have a memory leak.
#[derive(Clone, Debug)]
#[repr(C)] pub struct Context(c_int);

/// Library-internal representation of a Secp256k1 public key
#[repr(C)]
#[derive(Copy, Clone)]
#[cfg_attr(secp256k1_fuzz, derive(PartialEq, Eq, PartialOrd, Ord, Hash))]
pub struct PublicKey([c_uchar; 64]);
impl_array_newtype!(PublicKey, c_uchar, 64);
impl_raw_debug!(PublicKey);

impl PublicKey {
    /// Creates an "uninitialized" FFI public key which is zeroed out
    ///
    /// # Safety
    ///
    /// If you pass this to any FFI functions, except as an out-pointer,
    /// the result is likely to be an assertation failure and process
    /// termination.
    pub unsafe fn new() -> Self {
        Self::from_array_unchecked([0; 64])
    }

    /// Create a new public key usable for the FFI interface from raw bytes
    ///
    /// # Safety
    ///
    /// Does not check the validity of the underlying representation. If it is
    /// invalid the result may be assertation failures (and process aborts) from
    /// the underlying library. You should not use this method except with data
    /// that you obtained from the FFI interface of the same version of this
    /// library.
    pub unsafe fn from_array_unchecked(data: [c_uchar; 64]) -> Self {
        PublicKey(data)
    }

    /// Returns the underlying FFI opaque representation of the public key
    ///
    /// You should not use this unless you really know what you are doing. It is
    /// essentially only useful for extending the FFI interface itself.
    pub fn underlying_bytes(self) -> [c_uchar; 64] {
        self.0
    }

    /// Serializes this public key as a byte-encoded pair of values, in compressed form.
    fn serialize(&self) -> [u8; 33] {
        let mut buf = [0u8; 33];
        let mut len = 33;
        unsafe {
            let ret = secp256k1_ec_pubkey_serialize(
                secp256k1_context_no_precomp,
                buf.as_mut_c_ptr(),
                &mut len,
                self,
                SECP256K1_SER_COMPRESSED,
            );
            debug_assert_eq!(ret, 1);
            debug_assert_eq!(len, 33);
        };
        buf
    }
}

#[cfg(not(secp256k1_fuzz))]
impl PartialOrd for PublicKey {
    fn partial_cmp(&self, other: &PublicKey) -> Option<core::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

#[cfg(not(secp256k1_fuzz))]
impl Ord for PublicKey {
    fn cmp(&self, other: &PublicKey) -> core::cmp::Ordering {
        let ret = unsafe {
            secp256k1_ec_pubkey_cmp(secp256k1_context_no_precomp, self, other)
        };
        ret.cmp(&0i32)
    }
}

#[cfg(not(secp256k1_fuzz))]
impl PartialEq for PublicKey {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == core::cmp::Ordering::Equal
    }
}

#[cfg(not(secp256k1_fuzz))]
impl Eq for PublicKey {}

#[cfg(not(secp256k1_fuzz))]
impl core::hash::Hash for PublicKey {
    fn hash<H: core::hash::Hasher>(&self, state: &mut H) {
        let ser = self.serialize();
        ser.hash(state);
    }
}

/// Library-internal representation of a Secp256k1 signature
#[repr(C)]
#[derive(Copy, Clone)]
#[cfg_attr(secp256k1_fuzz, derive(PartialEq, Eq, PartialOrd, Ord, Hash))]
pub struct Signature([c_uchar; 64]);
impl_array_newtype!(Signature, c_uchar, 64);
impl_raw_debug!(Signature);

impl Signature {
    /// Creates an "uninitialized" FFI signature which is zeroed out
    ///
    /// # Safety
    ///
    /// If you pass this to any FFI functions, except as an out-pointer,
    /// the result is likely to be an assertation failure and process
    /// termination.
    pub unsafe fn new() -> Self {
        Self::from_array_unchecked([0; 64])
    }

    /// Create a new signature usable for the FFI interface from raw bytes
    ///
    /// # Safety
    ///
    /// Does not check the validity of the underlying representation. If it is
    /// invalid the result may be assertation failures (and process aborts) from
    /// the underlying library. You should not use this method except with data
    /// that you obtained from the FFI interface of the same version of this
    /// library.
    pub unsafe fn from_array_unchecked(data: [c_uchar; 64]) -> Self {
        Signature(data)
    }

    /// Returns the underlying FFI opaque representation of the signature
    ///
    /// You should not use this unless you really know what you are doing. It is
    /// essentially only useful for extending the FFI interface itself.
    pub fn underlying_bytes(self) -> [c_uchar; 64] {
        self.0
    }

    /// Serializes the signature in compact format.
    fn serialize(&self) -> [u8; 64] {
        let mut buf = [0u8; 64];
        unsafe {
            let ret = secp256k1_ecdsa_signature_serialize_compact(
                secp256k1_context_no_precomp,
                buf.as_mut_c_ptr(),
                self,
            );
            debug_assert!(ret == 1);
        }
        buf
    }
}

#[cfg(not(secp256k1_fuzz))]
impl PartialOrd for Signature {
    fn partial_cmp(&self, other: &Signature) -> Option<core::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

#[cfg(not(secp256k1_fuzz))]
impl Ord for Signature {
    fn cmp(&self, other: &Signature) -> core::cmp::Ordering {
        let this = self.serialize();
        let that = other.serialize();
        this.cmp(&that)
    }
}

#[cfg(not(secp256k1_fuzz))]
impl PartialEq for Signature {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == core::cmp::Ordering::Equal
    }
}

#[cfg(not(secp256k1_fuzz))]
impl Eq for Signature {}

#[cfg(not(secp256k1_fuzz))]
impl core::hash::Hash for Signature {
    fn hash<H: core::hash::Hasher>(&self, state: &mut H) {
        let ser = self.serialize();
        ser.hash(state);
    }
}

#[repr(C)]
#[derive(Copy, Clone)]
#[cfg_attr(secp256k1_fuzz, derive(PartialEq, Eq, PartialOrd, Ord, Hash))]
pub struct XOnlyPublicKey([c_uchar; 64]);
impl_array_newtype!(XOnlyPublicKey, c_uchar, 64);
impl_raw_debug!(XOnlyPublicKey);

impl XOnlyPublicKey {
    /// Creates an "uninitialized" FFI x-only public key which is zeroed out
    ///
    /// # Safety
    ///
    /// If you pass this to any FFI functions, except as an out-pointer,
    /// the result is likely to be an assertation failure and process
    /// termination.
    pub unsafe fn new() -> Self {
        Self::from_array_unchecked([0; 64])
    }

    /// Create a new x-only public key usable for the FFI interface from raw bytes
    ///
    /// # Safety
    ///
    /// Does not check the validity of the underlying representation. If it is
    /// invalid the result may be assertation failures (and process aborts) from
    /// the underlying library. You should not use this method except with data
    /// that you obtained from the FFI interface of the same version of this
    /// library.
    pub unsafe fn from_array_unchecked(data: [c_uchar; 64]) -> Self {
        XOnlyPublicKey(data)
    }

    /// Returns the underlying FFI opaque representation of the x-only public key
    ///
    /// You should not use this unless you really know what you are doing. It is
    /// essentially only useful for extending the FFI interface itself.
    pub fn underlying_bytes(self) -> [c_uchar; 64] {
        self.0
    }

    /// Serializes this key as a byte-encoded x coordinate value (32 bytes).
    fn serialize(&self) -> [u8; 32] {
        let mut buf = [0u8; 32];
        unsafe {
            let ret = secp256k1_xonly_pubkey_serialize(
                secp256k1_context_no_precomp,
                buf.as_mut_c_ptr(),
                self,
            );
            assert_eq!(ret, 1);
        };
        buf
    }
}

#[cfg(not(secp256k1_fuzz))]
impl PartialOrd for XOnlyPublicKey {
    fn partial_cmp(&self, other: &XOnlyPublicKey) -> Option<core::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

#[cfg(not(secp256k1_fuzz))]
impl Ord for XOnlyPublicKey {
    fn cmp(&self, other: &XOnlyPublicKey) -> core::cmp::Ordering {
        let ret = unsafe {
            secp256k1_xonly_pubkey_cmp(secp256k1_context_no_precomp, self, other)
        };
        ret.cmp(&0i32)
    }
}

#[cfg(not(secp256k1_fuzz))]
impl PartialEq for XOnlyPublicKey {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == core::cmp::Ordering::Equal
    }
}

#[cfg(not(secp256k1_fuzz))]
impl Eq for XOnlyPublicKey {}

#[cfg(not(secp256k1_fuzz))]
impl core::hash::Hash for XOnlyPublicKey {
    fn hash<H: core::hash::Hasher>(&self, state: &mut H) {
        let ser = self.serialize();
        ser.hash(state);
    }
}

#[repr(C)]
#[derive(Copy, Clone)]
#[cfg_attr(secp256k1_fuzz, derive(PartialEq, Eq, PartialOrd, Ord, Hash))]
pub struct Keypair([c_uchar; 96]);
impl_array_newtype!(Keypair, c_uchar, 96);
impl_raw_debug!(Keypair);

impl Keypair {
    /// Creates an "uninitialized" FFI keypair which is zeroed out
    ///
    /// # Safety
    ///
    /// If you pass this to any FFI functions, except as an out-pointer,
    /// the result is likely to be an assertation failure and process
    /// termination.
    pub unsafe fn new() -> Self {
        Self::from_array_unchecked([0; 96])
    }

    /// Create a new keypair usable for the FFI interface from raw bytes
    ///
    /// # Safety
    ///
    /// Does not check the validity of the underlying representation. If it is
    /// invalid the result may be assertation failures (and process aborts) from
    /// the underlying library. You should not use this method except with data
    /// that you obtained from the FFI interface of the same version of this
    /// library.
    pub unsafe fn from_array_unchecked(data: [c_uchar; 96]) -> Self {
        Keypair(data)
    }

    /// Returns the underlying FFI opaque representation of the x-only public key
    ///
    /// You should not use this unless you really know what you are doing. It is
    /// essentially only useful for extending the FFI interface itself.
    pub fn underlying_bytes(self) -> [c_uchar; 96] {
        self.0
    }

    /// Creates a new compressed public key from this key pair.
    fn public_key(&self) -> PublicKey {
        unsafe {
            let mut pk = PublicKey::new();
            let ret = secp256k1_keypair_pub(
                secp256k1_context_no_precomp,
                &mut pk,
                self,
            );
            debug_assert_eq!(ret, 1);
            pk
        }
    }

    /// Attempts to erase the contents of the underlying array.
    ///
    /// Note, however, that the compiler is allowed to freely copy or move the
    /// contents of this array to other places in memory. Preventing this behavior
    /// is very subtle. For more discussion on this, please see the documentation
    /// of the [`zeroize`](https://docs.rs/zeroize) crate.
    #[inline]
    pub fn non_secure_erase(&mut self) {
        non_secure_erase_impl(&mut self.0, DUMMY_KEYPAIR);
    }
}

// DUMMY_KEYPAIR is the internal repr of a valid key pair with secret key `[1u8; 32]`
#[cfg(target_endian = "little")]
const DUMMY_KEYPAIR: [c_uchar; 96] = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 143, 7, 221, 213, 233, 245, 23, 156, 255, 25, 72, 96, 52, 24, 30, 215, 101, 5, 186, 170, 213, 62, 93, 153, 64, 100, 18, 123, 86, 197, 132, 27, 209, 232, 168, 105, 122, 212, 34, 81, 222, 57, 246, 167, 32, 129, 223, 223, 66, 171, 197, 66, 166, 214, 254, 7, 21, 84, 139, 88, 143, 175, 190, 112];
#[cfg(all(target_endian = "big", target_pointer_width = "32"))]
const DUMMY_KEYPAIR: [c_uchar; 96] = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 213, 221, 7, 143, 156, 23, 245, 233, 96, 72, 25, 255, 215, 30, 24, 52, 170, 186, 5, 101, 153, 93, 62, 213, 123, 18, 100, 64, 27, 132, 197, 86, 105, 168, 232, 209, 81, 34, 212, 122, 167, 246, 57, 222, 223, 223, 129, 32, 66, 197, 171, 66, 7, 254, 214, 166, 88, 139, 84, 21, 112, 190, 175, 143];
#[cfg(all(target_endian = "big", target_pointer_width = "64"))]
const DUMMY_KEYPAIR: [c_uchar; 96] = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 156, 23, 245, 233, 213, 221, 7, 143, 215, 30, 24, 52, 96, 72, 25, 255, 153, 93, 62, 213, 170, 186, 5, 101, 27, 132, 197, 86, 123, 18, 100, 64, 81, 34, 212, 122, 105, 168, 232, 209, 223, 223, 129, 32, 167, 246, 57, 222, 7, 254, 214, 166, 66, 197, 171, 66, 112, 190, 175, 143, 88, 139, 84, 21];

/// Does a best attempt at secure erasure using Rust intrinsics.
///
/// The implementation is based on the approach used by the [`zeroize`](https://docs.rs/zeroize) crate.
#[inline(always)]
pub fn non_secure_erase_impl<T>(dst: &mut T, src: T) {
    use core::sync::atomic;
    // overwrite using volatile value
    unsafe { ptr::write_volatile(dst, src); }

    // prevent future accesses from being reordered to before erasure
    atomic::compiler_fence(atomic::Ordering::SeqCst);
}

#[cfg(not(secp256k1_fuzz))]
impl PartialOrd for Keypair {
    fn partial_cmp(&self, other: &Keypair) -> Option<core::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

#[cfg(not(secp256k1_fuzz))]
impl Ord for Keypair {
    fn cmp(&self, other: &Keypair) -> core::cmp::Ordering {
        let this = self.public_key();
        let that = other.public_key();
        this.cmp(&that)
    }
}

#[cfg(not(secp256k1_fuzz))]
impl PartialEq for Keypair {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == core::cmp::Ordering::Equal
    }
}

#[cfg(not(secp256k1_fuzz))]
impl Eq for Keypair {}

#[cfg(not(secp256k1_fuzz))]
impl core::hash::Hash for Keypair {
    fn hash<H: core::hash::Hasher>(&self, state: &mut H) {
        // To hash the key pair we just hash the serialized public key. Since any change to the
        // secret key would also be a change to the public key this is a valid one way function from
        // the key pair to the digest.
        let pk = self.public_key();
        let ser = pk.serialize();
        ser.hash(state);
    }
}

/// Library-internal representation of a ElligatorSwift encoded group element.
#[repr(C)]
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ElligatorSwift([u8; 64]);

impl ElligatorSwift {
    pub fn from_array(arr: [u8; 64]) -> Self {
        ElligatorSwift(arr)
    }
    pub fn to_array(self) -> [u8; 64] {
        self.0
    }
}

impl_array_newtype!(ElligatorSwift, u8, 64);
impl_raw_debug!(ElligatorSwift);

extern "C" {
    /// Default ECDH hash function
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ecdh_hash_function_default")]
    pub static secp256k1_ecdh_hash_function_default: EcdhHashFn;

    /// Default ECDH hash function for BIP324 key establishment
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ellswift_xdh_hash_function_bip324")]
    pub static secp256k1_ellswift_xdh_hash_function_bip324: EllswiftEcdhHashFn;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_nonce_function_rfc6979")]
    pub static secp256k1_nonce_function_rfc6979: NonceFn;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_nonce_function_default")]
    pub static secp256k1_nonce_function_default: NonceFn;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_nonce_function_bip340")]
    pub static secp256k1_nonce_function_bip340: SchnorrNonceFn;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_context_no_precomp")]
    pub static secp256k1_context_no_precomp: *const Context;

    // Contexts
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_context_preallocated_destroy")]
    pub fn secp256k1_context_preallocated_destroy(cx: NonNull<Context>);

    // Signatures
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ecdsa_signature_parse_der")]
    pub fn secp256k1_ecdsa_signature_parse_der(cx: *const Context, sig: *mut Signature,
                                               input: *const c_uchar, in_len: size_t)
                                               -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ecdsa_signature_parse_compact")]
    pub fn secp256k1_ecdsa_signature_parse_compact(cx: *const Context, sig: *mut Signature,
                                                   input64: *const c_uchar)
                                                   -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ecdsa_signature_parse_der_lax")]
    pub fn ecdsa_signature_parse_der_lax(cx: *const Context, sig: *mut Signature,
                                         input: *const c_uchar, in_len: size_t)
                                         -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ecdsa_signature_serialize_der")]
    pub fn secp256k1_ecdsa_signature_serialize_der(cx: *const Context, output: *mut c_uchar,
                                                   out_len: *mut size_t, sig: *const Signature)
                                                   -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ecdsa_signature_serialize_compact")]
    pub fn secp256k1_ecdsa_signature_serialize_compact(cx: *const Context, output64: *mut c_uchar,
                                                       sig: *const Signature)
                                                       -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ecdsa_signature_normalize")]
    pub fn secp256k1_ecdsa_signature_normalize(cx: *const Context, out_sig: *mut Signature,
                                               in_sig: *const Signature)
                                               -> c_int;

    // Secret Keys
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_seckey_verify")]
    pub fn secp256k1_ec_seckey_verify(cx: *const Context,
                                      sk: *const c_uchar) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_seckey_negate")]
    pub fn secp256k1_ec_seckey_negate(cx: *const Context,
                                      sk: *mut c_uchar) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_seckey_tweak_add")]
    pub fn secp256k1_ec_seckey_tweak_add(cx: *const Context,
                                        sk: *mut c_uchar,
                                        tweak: *const c_uchar)
                                        -> c_int;
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_seckey_tweak_mul")]
    pub fn secp256k1_ec_seckey_tweak_mul(cx: *const Context,
                                        sk: *mut c_uchar,
                                        tweak: *const c_uchar)
                                        -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_keypair_sec")]
    pub fn secp256k1_keypair_sec(cx: *const Context,
                                 output_seckey: *mut c_uchar,
                                 keypair: *const Keypair)
                                 -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_keypair_pub")]
    pub fn secp256k1_keypair_pub(cx: *const Context,
                                 output_pubkey: *mut PublicKey,
                                 keypair: *const Keypair)
                                 -> c_int;
    // Elligator Swift
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ellswift_encode")]
    pub fn secp256k1_ellswift_encode(ctx: *const Context,
                                     ell64: *mut c_uchar,
                                     pubkey: *const PublicKey,
                                     rnd32: *const c_uchar)
                                     -> c_int;
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ellswift_decode")]
    pub fn secp256k1_ellswift_decode(ctx: *const Context,
                                     pubkey: *mut u8,
                                     ell64: *const c_uchar)
                                     -> c_int;
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ellswift_create")]
    pub fn secp256k1_ellswift_create(ctx: *const Context,
                                     ell64: *mut c_uchar,
                                     seckey32: *const c_uchar,
                                     aux_rand32: *const c_uchar)
                                     -> c_int;
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ellswift_xdh")]
    pub fn secp256k1_ellswift_xdh(ctx: *const Context,
                                  output: *mut c_uchar,
                                  ell_a64: *const c_uchar,
                                  ell_b64: *const c_uchar,
                                  seckey32: *const c_uchar,
                                  party: c_int,
                                  hashfp: EllswiftEcdhHashFn,
                                  data: *mut c_void)
                                  -> c_int;
}

#[cfg(not(secp256k1_fuzz))]
extern "C" {
    // Contexts
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_context_preallocated_size")]
    pub fn secp256k1_context_preallocated_size(flags: c_uint) -> size_t;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_context_preallocated_create")]
    pub fn secp256k1_context_preallocated_create(prealloc: NonNull<c_void>, flags: c_uint) -> NonNull<Context>;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_context_preallocated_clone_size")]
    pub fn secp256k1_context_preallocated_clone_size(cx: *const Context) -> size_t;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_context_preallocated_clone")]
    pub fn secp256k1_context_preallocated_clone(cx: *const Context, prealloc: NonNull<c_void>) -> NonNull<Context>;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_context_randomize")]
    pub fn secp256k1_context_randomize(cx: NonNull<Context>,
                                       seed32: *const c_uchar)
                                       -> c_int;
    // Pubkeys
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_pubkey_parse")]
    pub fn secp256k1_ec_pubkey_parse(cx: *const Context, pk: *mut PublicKey,
                                     input: *const c_uchar, in_len: size_t)
                                     -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_pubkey_serialize")]
    pub fn secp256k1_ec_pubkey_serialize(cx: *const Context, output: *mut c_uchar,
                                         out_len: *mut size_t, pk: *const PublicKey,
                                         compressed: c_uint)
                                         -> c_int;

    // EC
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_pubkey_create")]
    pub fn secp256k1_ec_pubkey_create(cx: *const Context, pk: *mut PublicKey,
                                      sk: *const c_uchar) -> c_int;


    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_pubkey_negate")]
    pub fn secp256k1_ec_pubkey_negate(cx: *const Context,
                                      pk: *mut PublicKey) -> c_int;


    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_pubkey_cmp")]
    pub fn secp256k1_ec_pubkey_cmp(cx: *const Context,
                                   pubkey1: *const PublicKey,
                                   pubkey2: *const PublicKey)
                                   -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_pubkey_tweak_add")]
    pub fn secp256k1_ec_pubkey_tweak_add(cx: *const Context,
                                         pk: *mut PublicKey,
                                         tweak: *const c_uchar)
                                         -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_pubkey_tweak_mul")]
    pub fn secp256k1_ec_pubkey_tweak_mul(cx: *const Context,
                                         pk: *mut PublicKey,
                                         tweak: *const c_uchar)
                                         -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ec_pubkey_combine")]
    pub fn secp256k1_ec_pubkey_combine(cx: *const Context,
                                       out: *mut PublicKey,
                                       ins: *const *const PublicKey,
                                       n: size_t)
                                       -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ecdh")]
    pub fn secp256k1_ecdh(
        cx: *const Context,
        output: *mut c_uchar,
        pubkey: *const PublicKey,
        seckey: *const c_uchar,
        hashfp: EcdhHashFn,
        data: *mut c_void,
    ) -> c_int;

    // ECDSA
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ecdsa_verify")]
    pub fn secp256k1_ecdsa_verify(cx: *const Context,
                                  sig: *const Signature,
                                  msg32: *const c_uchar,
                                  pk: *const PublicKey)
                                  -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_ecdsa_sign")]
    pub fn secp256k1_ecdsa_sign(cx: *const Context,
                                sig: *mut Signature,
                                msg32: *const c_uchar,
                                sk: *const c_uchar,
                                noncefn: NonceFn,
                                noncedata: *const c_void)
                                -> c_int;

    // Schnorr Signatures
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_schnorrsig_sign")]
    pub fn secp256k1_schnorrsig_sign(
        cx: *const Context,
        sig: *mut c_uchar,
        msg32: *const c_uchar,
        keypair: *const Keypair,
        aux_rand32: *const c_uchar
    ) -> c_int;

    // Schnorr Signatures with extra parameters (see [`SchnorrSigExtraParams`])
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_schnorrsig_sign_custom")]
    pub fn secp256k1_schnorrsig_sign_custom(
        cx: *const Context,
        sig: *mut c_uchar,
        msg: *const c_uchar,
        msg_len: size_t,
        keypair: *const Keypair,
        extra_params: *const SchnorrSigExtraParams,
    ) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_schnorrsig_verify")]
    pub fn secp256k1_schnorrsig_verify(
        cx: *const Context,
        sig64: *const c_uchar,
        msg32: *const c_uchar,
        msglen: size_t,
        pubkey: *const XOnlyPublicKey,
    ) -> c_int;

    // Extra keys
    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_keypair_create")]
    pub fn secp256k1_keypair_create(
        cx: *const Context,
        keypair: *mut Keypair,
        seckey: *const c_uchar,
    ) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_xonly_pubkey_parse")]
    pub fn secp256k1_xonly_pubkey_parse(
        cx: *const Context,
        pubkey: *mut XOnlyPublicKey,
        input32: *const c_uchar,
    ) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_xonly_pubkey_serialize")]
    pub fn secp256k1_xonly_pubkey_serialize(
        cx: *const Context,
        output32: *mut c_uchar,
        pubkey: *const XOnlyPublicKey,
    ) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_xonly_pubkey_from_pubkey")]
    pub fn secp256k1_xonly_pubkey_from_pubkey(
        cx: *const Context,
        xonly_pubkey: *mut XOnlyPublicKey,
        pk_parity: *mut c_int,
        pubkey: *const PublicKey,
    ) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_xonly_pubkey_cmp")]
    pub fn secp256k1_xonly_pubkey_cmp(
        cx: *const Context,
        pubkey1: *const XOnlyPublicKey,
        pubkey2: *const XOnlyPublicKey
    ) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_xonly_pubkey_tweak_add")]
    pub fn secp256k1_xonly_pubkey_tweak_add(
        cx: *const Context,
        output_pubkey: *mut PublicKey,
        internal_pubkey: *const XOnlyPublicKey,
        tweak32: *const c_uchar,
    ) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_keypair_xonly_pub")]
    pub fn secp256k1_keypair_xonly_pub(
        cx: *const Context,
        pubkey: *mut XOnlyPublicKey,
        pk_parity: *mut c_int,
        keypair: *const Keypair
    ) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_keypair_xonly_tweak_add")]
    pub fn secp256k1_keypair_xonly_tweak_add(
        cx: *const Context,
        keypair: *mut Keypair,
        tweak32: *const c_uchar,
    ) -> c_int;

    #[cfg_attr(not(rust_secp_no_symbol_renaming), link_name = "rustsecp256k1_v0_10_0_xonly_pubkey_tweak_add_check")]
    pub fn secp256k1_xonly_pubkey_tweak_add_check(
        cx: *const Context,
        tweaked_pubkey32: *const c_uchar,
        tweaked_pubkey_parity: c_int,
        internal_pubkey: *const XOnlyPublicKey,
        tweak32: *const c_uchar,
    ) -> c_int;
}

/// A reimplementation of the C function `secp256k1_context_create` in rust.
///
/// This function allocates memory, the pointer should be deallocated using
/// `secp256k1_context_destroy`. Failure to do so will result in a memory leak.
///
/// Input `flags` control which parts of the context to initialize.
///
/// # Safety
///
/// This function is unsafe because it calls unsafe functions however (assuming no bugs) no
/// undefined behavior is possible.
///
/// # Returns
///
/// The newly created secp256k1 raw context.
#[cfg(all(feature = "alloc", not(rust_secp_no_symbol_renaming)))]
pub unsafe fn secp256k1_context_create(flags: c_uint) -> NonNull<Context> {
    rustsecp256k1_v0_10_0_context_create(flags)
}

/// A reimplementation of the C function `secp256k1_context_create` in rust.
///
/// See [`secp256k1_context_create`] for documentation and safety constraints.
#[no_mangle]
#[allow(clippy::missing_safety_doc)] // Documented above.
#[cfg(all(feature = "alloc", not(rust_secp_no_symbol_renaming)))]
pub unsafe extern "C" fn rustsecp256k1_v0_10_0_context_create(flags: c_uint) -> NonNull<Context> {
    use core::mem;
    use crate::alloc::alloc;
    assert!(ALIGN_TO >= mem::align_of::<usize>());
    assert!(ALIGN_TO >= mem::align_of::<&usize>());
    assert!(ALIGN_TO >= mem::size_of::<usize>());

    // We need to allocate `ALIGN_TO` more bytes in order to write the amount of bytes back.
    let bytes = secp256k1_context_preallocated_size(flags) + ALIGN_TO;
    let layout = alloc::Layout::from_size_align(bytes, ALIGN_TO).unwrap();
    let ptr = alloc::alloc(layout);
    if ptr.is_null() {
        alloc::handle_alloc_error(layout);
    }
    (ptr as *mut usize).write(bytes);
    // We must offset a whole ALIGN_TO in order to preserve the same alignment
    // this means we "lose" ALIGN_TO-size_of(usize) for padding.
    let ptr = ptr.add(ALIGN_TO);
    let ptr = NonNull::new_unchecked(ptr as *mut c_void); // Checked above.
    secp256k1_context_preallocated_create(ptr, flags)
}

/// A reimplementation of the C function `secp256k1_context_destroy` in rust.
///
/// This function destroys and deallcates the context created by `secp256k1_context_create`.
///
/// The pointer shouldn't be used after passing to this function, consider it as passing it to `free()`.
///
/// # Safety
///
///  `ctx` must be a valid pointer to a block of memory created using [`secp256k1_context_create`].
#[cfg(all(feature = "alloc", not(rust_secp_no_symbol_renaming)))]
pub unsafe fn secp256k1_context_destroy(ctx: NonNull<Context>) {
    rustsecp256k1_v0_10_0_context_destroy(ctx)
}

#[no_mangle]
#[allow(clippy::missing_safety_doc)] // Documented above.
#[cfg(all(feature = "alloc", not(rust_secp_no_symbol_renaming)))]
pub unsafe extern "C" fn rustsecp256k1_v0_10_0_context_destroy(mut ctx: NonNull<Context>) {
    use crate::alloc::alloc;
    secp256k1_context_preallocated_destroy(ctx);
    let ctx: *mut Context = ctx.as_mut();
    let ptr = (ctx as *mut u8).sub(ALIGN_TO);
    let bytes = (ptr as *mut usize).read();
    let layout = alloc::Layout::from_size_align(bytes, ALIGN_TO).unwrap();
    alloc::dealloc(ptr, layout);
}

/// **This function is an override for the C function, this is the an edited version of the original description:**
///
/// A callback function to be called when an illegal argument is passed to
/// an API call. It will only trigger for violations that are mentioned
/// explicitly in the header. **This will cause a panic**.
///
/// The philosophy is that these shouldn't be dealt with through a
/// specific return value, as calling code should not have branches to deal with
/// the case that this code itself is broken.
///
/// On the other hand, during debug stage, one would want to be informed about
/// such mistakes, and the default (crashing) may be inadvisable.
/// When this callback is triggered, the API function called is guaranteed not
/// to cause a crash, though its return value and output arguments are
/// undefined.
///
/// See also secp256k1_default_error_callback_fn.
///
///
/// # Safety
///
/// `message` string should be a null terminated C string and, up to the first null byte, must be valid UTF8.
///
/// For exact safety constraints see [`std::slice::from_raw_parts`] and [`std::str::from_utf8_unchecked`].
#[no_mangle]
#[cfg(not(rust_secp_no_symbol_renaming))]
pub unsafe extern "C" fn rustsecp256k1_v0_10_0_default_illegal_callback_fn(message: *const c_char, _data: *mut c_void) {
    use core::str;
    let msg_slice = slice::from_raw_parts(message as *const u8, strlen(message));
    let msg = str::from_utf8_unchecked(msg_slice);
    panic!("[libsecp256k1] illegal argument. {}", msg);
}

/// **This function is an override for the C function, this is the an edited version of the original description:**
///
/// A callback function to be called when an internal consistency check
/// fails. **This will cause a panic**.
///
/// This can only trigger in case of a hardware failure, miscompilation,
/// memory corruption, serious bug in the library, or other error would can
/// otherwise result in undefined behaviour. It will not trigger due to mere
/// incorrect usage of the API (see secp256k1_default_illegal_callback_fn
/// for that). After this callback returns, anything may happen, including
/// crashing.
///
/// See also secp256k1_default_illegal_callback_fn.
///
/// # Safety
///
/// `message` string should be a null terminated C string and, up to the first null byte, must be valid UTF8.
///
/// For exact safety constraints see [`std::slice::from_raw_parts`] and [`std::str::from_utf8_unchecked`].
#[no_mangle]
#[cfg(not(rust_secp_no_symbol_renaming))]
pub unsafe extern "C" fn rustsecp256k1_v0_10_0_default_error_callback_fn(message: *const c_char, _data: *mut c_void) {
    use core::str;
    let msg_slice = slice::from_raw_parts(message as *const u8, strlen(message));
    let msg = str::from_utf8_unchecked(msg_slice);
    panic!("[libsecp256k1] internal consistency check failed {}", msg);
}

/// Returns the length of the `str_ptr` string.
///
/// # Safety
///
/// `str_ptr` must be valid pointer and point to a valid null terminated C string.
#[cfg(not(rust_secp_no_symbol_renaming))]
unsafe fn strlen(mut str_ptr: *const c_char) -> usize {
    let mut ctr = 0;
    while *str_ptr != '\0' as c_char {
        ctr += 1;
        str_ptr = str_ptr.offset(1);
    }
    ctr
}


/// A trait for producing pointers that will always be valid in C (assuming NULL pointer is a valid
/// no-op).
///
/// Rust does not guarantee pointers to Zero Sized Types
/// (<https://doc.rust-lang.org/nomicon/exotic-sizes.html#zero-sized-types-zsts>). In case the type
/// is empty this trait will return a NULL pointer, which should be handled in C.
pub trait CPtr {
    type Target;
    fn as_c_ptr(&self) -> *const Self::Target;
    fn as_mut_c_ptr(&mut self) -> *mut Self::Target;
}

impl<T> CPtr for [T] {
    type Target = T;
    fn as_c_ptr(&self) -> *const Self::Target {
        if self.is_empty() {
            ptr::null()
        } else {
            self.as_ptr()
        }
    }

    fn as_mut_c_ptr(&mut self) -> *mut Self::Target {
        if self.is_empty() {
            ptr::null_mut::<Self::Target>()
        } else {
            self.as_mut_ptr()
        }
    }
}

impl<T> CPtr for &[T] {
    type Target = T;
    fn as_c_ptr(&self) -> *const Self::Target {
        if self.is_empty() {
            ptr::null()
        } else {
            self.as_ptr()
        }
    }

    fn as_mut_c_ptr(&mut self) -> *mut Self::Target {
        if self.is_empty() {
            ptr::null_mut()
        } else {
            self.as_ptr() as *mut Self::Target
        }
    }

}

impl CPtr for [u8; 32] {
    type Target = u8;
    fn as_c_ptr(&self) -> *const Self::Target {
        self.as_ptr()
    }

    fn as_mut_c_ptr(&mut self) -> *mut Self::Target {
        self.as_mut_ptr()
    }
}

impl <T: CPtr> CPtr for Option<T> {
    type Target = T::Target;
    fn as_mut_c_ptr(&mut self) -> *mut Self::Target {
        match self {
            Some(contents) => contents.as_mut_c_ptr(),
            None => ptr::null_mut(),
        }
    }
    fn as_c_ptr(&self) -> *const Self::Target {
        match self {
            Some(content) => content.as_c_ptr(),
            None => ptr::null(),
        }
    }
}

#[cfg(secp256k1_fuzz)]
mod fuzz_dummy {
    use super::*;
    use core::sync::atomic::{AtomicUsize, Ordering};

    #[cfg(rust_secp_no_symbol_renaming)] compile_error!("We do not support fuzzing with rust_secp_no_symbol_renaming");

    extern "C" {
        fn rustsecp256k1_v0_10_0_context_preallocated_size(flags: c_uint) -> size_t;
        fn rustsecp256k1_v0_10_0_context_preallocated_create(prealloc: NonNull<c_void>, flags: c_uint) -> NonNull<Context>;
        fn rustsecp256k1_v0_10_0_context_preallocated_clone(cx: *const Context, prealloc: NonNull<c_void>) -> NonNull<Context>;
    }

    #[cfg(feature = "lowmemory")]
    const CTX_SIZE: usize = 1024 * 65;
    #[cfg(not(feature = "lowmemory"))]
    const CTX_SIZE: usize = 1024 * (1024 + 128);
    // Contexts
    pub unsafe fn secp256k1_context_preallocated_size(flags: c_uint) -> size_t {
        assert!(rustsecp256k1_v0_10_0_context_preallocated_size(flags) + std::mem::size_of::<c_uint>() <= CTX_SIZE);
        CTX_SIZE
    }

    static HAVE_PREALLOCATED_CONTEXT: AtomicUsize = AtomicUsize::new(0);
    const HAVE_CONTEXT_NONE: usize = 0;
    const HAVE_CONTEXT_WORKING: usize = 1;
    const HAVE_CONTEXT_DONE: usize = 2;
    static mut PREALLOCATED_CONTEXT: [u8; CTX_SIZE] = [0; CTX_SIZE];
    pub unsafe fn secp256k1_context_preallocated_create(prealloc: NonNull<c_void>, flags: c_uint) -> NonNull<Context> {
        // While applications should generally avoid creating too many contexts, sometimes fuzzers
        // perform tasks repeatedly which real applications may only do rarely. Thus, we want to
        // avoid being overly slow here. We do so by having a static context and copying it into
        // new buffers instead of recalculating it. Because we shouldn't rely on std, we use a
        // simple hand-written OnceFlag built out of an atomic to gate the global static.
        let mut have_ctx = HAVE_PREALLOCATED_CONTEXT.load(Ordering::Relaxed);
        while have_ctx != HAVE_CONTEXT_DONE {
            if have_ctx == HAVE_CONTEXT_NONE {
                have_ctx = HAVE_PREALLOCATED_CONTEXT.swap(HAVE_CONTEXT_WORKING, Ordering::AcqRel);
                if have_ctx == HAVE_CONTEXT_NONE {
                    assert!(rustsecp256k1_v0_10_0_context_preallocated_size(SECP256K1_START_SIGN | SECP256K1_START_VERIFY) + std::mem::size_of::<c_uint>() <= CTX_SIZE);
                    assert_eq!(rustsecp256k1_v0_10_0_context_preallocated_create(
                            NonNull::new_unchecked(PREALLOCATED_CONTEXT[..].as_mut_ptr() as *mut c_void),
                            SECP256K1_START_SIGN | SECP256K1_START_VERIFY),
                        NonNull::new_unchecked(PREALLOCATED_CONTEXT[..].as_mut_ptr() as *mut Context));
                    assert_eq!(HAVE_PREALLOCATED_CONTEXT.swap(HAVE_CONTEXT_DONE, Ordering::AcqRel),
                        HAVE_CONTEXT_WORKING);
                } else if have_ctx == HAVE_CONTEXT_DONE {
                    // Another thread finished while we were swapping.
                    HAVE_PREALLOCATED_CONTEXT.store(HAVE_CONTEXT_DONE, Ordering::Release);
                }
            } else {
                // Another thread is building, just busy-loop until they're done.
                assert_eq!(have_ctx, HAVE_CONTEXT_WORKING);
                have_ctx = HAVE_PREALLOCATED_CONTEXT.load(Ordering::Acquire);
                #[cfg(feature = "std")]
                std::thread::yield_now();
            }
        }
        ptr::copy_nonoverlapping(PREALLOCATED_CONTEXT[..].as_ptr(), prealloc.as_ptr() as *mut u8, CTX_SIZE);
        let ptr = (prealloc.as_ptr()).add(CTX_SIZE).sub(std::mem::size_of::<c_uint>());
        (ptr as *mut c_uint).write(flags);
        NonNull::new_unchecked(prealloc.as_ptr() as *mut Context)
    }
    pub unsafe fn secp256k1_context_preallocated_clone_size(_cx: *const Context) -> size_t { CTX_SIZE }
    pub unsafe fn secp256k1_context_preallocated_clone(cx: *const Context, prealloc: NonNull<c_void>) -> NonNull<Context> {
        let orig_ptr = (cx as *mut u8).add(CTX_SIZE).sub(std::mem::size_of::<c_uint>());
        let new_ptr = (prealloc.as_ptr() as *mut u8).add(CTX_SIZE).sub(std::mem::size_of::<c_uint>());
        let flags = (orig_ptr as *mut c_uint).read();
        (new_ptr as *mut c_uint).write(flags);
        rustsecp256k1_v0_10_0_context_preallocated_clone(cx, prealloc)
    }

    pub unsafe fn secp256k1_context_randomize(cx: NonNull<Context>,
                                              _seed32: *const c_uchar)
                                              -> c_int {
        // This function is really slow, and unsuitable for fuzzing
        check_context_flags(cx.as_ptr(), 0);
        1
    }

    unsafe fn check_context_flags(cx: *const Context, required_flags: c_uint) {
        assert!(!cx.is_null());
        let cx_flags = if cx == secp256k1_context_no_precomp {
            1
        } else {
            let ptr = (cx as *const u8).add(CTX_SIZE).sub(std::mem::size_of::<c_uint>());
            (ptr as *const c_uint).read()
        };
        assert_eq!(cx_flags & 1, 1); // SECP256K1_FLAGS_TYPE_CONTEXT
        assert_eq!(cx_flags & required_flags, required_flags);
    }

    /// Checks that pk != 0xffff...ffff and pk[1..32] == pk[33..64]
    unsafe fn test_pk_validate(cx: *const Context,
                               pk: *const PublicKey) -> c_int {
        check_context_flags(cx, 0);
        if (*pk).0[1..32] != (*pk).0[33..64] ||
           ((*pk).0[32] != 0 && (*pk).0[32] != 0xff) ||
           secp256k1_ec_seckey_verify(cx, (*pk).0[0..32].as_ptr()) == 0 {
            0
        } else {
            1
        }
    }
    unsafe fn test_cleanup_pk(pk: *mut PublicKey) {
        (*pk).0[32..].copy_from_slice(&(*pk).0[..32]);
        if (*pk).0[32] <= 0x7f {
            (*pk).0[32] = 0;
        } else {
            (*pk).0[32] = 0xff;
        }
    }

    // Pubkeys
    pub unsafe fn secp256k1_ec_pubkey_parse(cx: *const Context, pk: *mut PublicKey,
                                            input: *const c_uchar, in_len: size_t)
                                            -> c_int {
        check_context_flags(cx, 0);
        match in_len {
            33 => {
                if *input != 2 && *input != 3 {
                    0
                } else {
                    ptr::copy(input.offset(1), (*pk).0[0..32].as_mut_ptr(), 32);
                    ptr::copy(input.offset(2), (*pk).0[33..64].as_mut_ptr(), 31);
                    if *input == 3 {
                        (*pk).0[32] = 0xff;
                    } else {
                        (*pk).0[32] = 0;
                    }
                    test_pk_validate(cx, pk)
                }
            },
            65 => {
                if *input != 4 && *input != 6 && *input != 7 {
                    0
                } else {
                    ptr::copy(input.offset(1), (*pk).0.as_mut_ptr(), 64);
                    test_cleanup_pk(pk);
                    test_pk_validate(cx, pk)
                }
            },
            _ => 0
        }
    }

    /// Serialize PublicKey back to 33/65 byte pubkey
    pub unsafe fn secp256k1_ec_pubkey_serialize(cx: *const Context, output: *mut c_uchar,
                                                out_len: *mut size_t, pk: *const PublicKey,
                                                compressed: c_uint)
                                                -> c_int {
        check_context_flags(cx, 0);
        assert_eq!(test_pk_validate(cx, pk), 1);
        if compressed == SECP256K1_SER_COMPRESSED {
            assert_eq!(*out_len, 33);
            if (*pk).0[32] <= 0x7f {
                *output = 2;
            } else {
                *output = 3;
            }
            ptr::copy((*pk).0.as_ptr(), output.offset(1), 32);
        } else if compressed == SECP256K1_SER_UNCOMPRESSED {
            assert_eq!(*out_len, 65);
            *output = 4;
            ptr::copy((*pk).0.as_ptr(), output.offset(1), 64);
        } else {
            panic!("Bad flags");
        }
        1
     }

    // EC
    /// Sets pk to sk||sk
    pub unsafe fn secp256k1_ec_pubkey_create(cx: *const Context, pk: *mut PublicKey,
                                             sk: *const c_uchar) -> c_int {
        check_context_flags(cx, SECP256K1_START_SIGN);
        if secp256k1_ec_seckey_verify(cx, sk) != 1 { return 0; }
        ptr::copy(sk, (*pk).0[0..32].as_mut_ptr(), 32);
        test_cleanup_pk(pk);
        assert_eq!(test_pk_validate(cx, pk), 1);
        1
    }

    pub unsafe fn secp256k1_ec_pubkey_negate(cx: *const Context,
                                             pk: *mut PublicKey) -> c_int {
        check_context_flags(cx, 0);
        assert_eq!(test_pk_validate(cx, pk), 1);
        if secp256k1_ec_seckey_negate(cx, (*pk).0[..32].as_mut_ptr()) != 1 { return 0; }
        test_cleanup_pk(pk);
        assert_eq!(test_pk_validate(cx, pk), 1);
        1
    }

    /// The PublicKey equivalent of secp256k1_ec_privkey_tweak_add
    pub unsafe fn secp256k1_ec_pubkey_tweak_add(cx: *const Context,
                                                pk: *mut PublicKey,
                                                tweak: *const c_uchar)
                                                -> c_int {
        check_context_flags(cx, SECP256K1_START_VERIFY);
        assert_eq!(test_pk_validate(cx, pk), 1);
        if secp256k1_ec_seckey_tweak_add(cx, (*pk).0[..32].as_mut_ptr(), tweak) != 1 { return 0; }
        test_cleanup_pk(pk);
        assert_eq!(test_pk_validate(cx, pk), 1);
        1
    }

    /// The PublicKey equivalent of secp256k1_ec_privkey_tweak_mul
    pub unsafe fn secp256k1_ec_pubkey_tweak_mul(cx: *const Context,
                                                pk: *mut PublicKey,
                                                tweak: *const c_uchar)
                                                -> c_int {
        check_context_flags(cx, 0);
        assert_eq!(test_pk_validate(cx, pk), 1);
        if secp256k1_ec_seckey_tweak_mul(cx, (*pk).0[..32].as_mut_ptr(), tweak) != 1 { return 0; }
        test_cleanup_pk(pk);
        assert_eq!(test_pk_validate(cx, pk), 1);
        1
    }

    pub unsafe fn secp256k1_ec_pubkey_combine(cx: *const Context,
                                              out: *mut PublicKey,
                                              ins: *const *const PublicKey,
                                              n: size_t)
                                              -> c_int {
        check_context_flags(cx, 0);
        assert!(n >= 1);
        (*out) = **ins;
        for i in 1..n {
            assert_eq!(test_pk_validate(cx, *ins.offset(i as isize)), 1);
            if secp256k1_ec_seckey_tweak_add(cx, (*out).0[..32].as_mut_ptr(), (**ins.offset(i as isize)).0[..32].as_ptr()) != 1 {
                return 0;
            }
        }
        test_cleanup_pk(out);
        assert_eq!(test_pk_validate(cx, out), 1);
        1
    }

    /// Sets out to point^scalar^1s
    pub unsafe fn secp256k1_ecdh(
        cx: *const Context,
        out: *mut c_uchar,
        point: *const PublicKey,
        scalar: *const c_uchar,
        hashfp: EcdhHashFn,
        data: *mut c_void,
    ) -> c_int {
        check_context_flags(cx, 0);
        assert_eq!(test_pk_validate(cx, point), 1);
        if secp256k1_ec_seckey_verify(cx, scalar) != 1 { return 0; }

        let scalar_slice = slice::from_raw_parts(scalar, 32);
        let pk_slice = &(*point).0[..32];

        let mut res_arr = [0u8; 32];
        for i in 0..32 {
            res_arr[i] = scalar_slice[i] ^ pk_slice[i] ^ 1;
        }

        if let Some(hashfn) = hashfp {
            (hashfn)(out, res_arr.as_ptr(), res_arr.as_ptr(), data);
        } else {
            res_arr[16] = 0x00; // result should always be a valid secret key
            let out_slice = slice::from_raw_parts_mut(out, 32);
            out_slice.copy_from_slice(&res_arr);
        }
        1
    }

    // ECDSA
    /// Verifies that sig is msg32||pk[..32]
    pub unsafe fn secp256k1_ecdsa_verify(cx: *const Context,
                                         sig: *const Signature,
                                         msg32: *const c_uchar,
                                         pk: *const PublicKey)
                                         -> c_int {
        check_context_flags(cx, SECP256K1_START_VERIFY);
        // Actually verify
        let sig_sl = slice::from_raw_parts(sig as *const u8, 64);
        let msg_sl = slice::from_raw_parts(msg32 as *const u8, 32);
        if &sig_sl[..32] == msg_sl && sig_sl[32..] == (*pk).0[0..32] {
            1
        } else {
            0
        }
    }

    /// Sets sig to msg32||pk[..32]
    pub unsafe fn secp256k1_ecdsa_sign(cx: *const Context,
                                       sig: *mut Signature,
                                       msg32: *const c_uchar,
                                       sk: *const c_uchar,
                                       _noncefn: NonceFn,
                                       _noncedata: *const c_void)
                                       -> c_int {
        check_context_flags(cx, SECP256K1_START_SIGN);
        // Check context is built for signing (and compute pk)
        let mut new_pk = PublicKey::new();
        if secp256k1_ec_pubkey_create(cx, &mut new_pk, sk) != 1 {
            return 0;
        }
        // Sign
        let sig_sl = slice::from_raw_parts_mut(sig as *mut u8, 64);
        let msg_sl = slice::from_raw_parts(msg32 as *const u8, 32);
        sig_sl[..32].copy_from_slice(msg_sl);
        sig_sl[32..].copy_from_slice(&new_pk.0[..32]);
        1
    }

    // Schnorr Signatures
    /// Verifies that sig is msg32||pk[32..]
    pub unsafe fn secp256k1_schnorrsig_verify(
        cx: *const Context,
        sig64: *const c_uchar,
        msg32: *const c_uchar,
        msglen: size_t,
        pubkey: *const XOnlyPublicKey,
    ) -> c_int {
        check_context_flags(cx, SECP256K1_START_VERIFY);
        // Check context is built for verification
        let mut new_pk = PublicKey::new();
        let _ = secp256k1_xonly_pubkey_tweak_add(cx, &mut new_pk, pubkey, msg32);
        // Actually verify
        let sig_sl = slice::from_raw_parts(sig64 as *const u8, 64);
        let msg_sl = slice::from_raw_parts(msg32 as *const u8, msglen);
        if &sig_sl[..32] == msg_sl && sig_sl[32..] == (*pubkey).0[..32] {
            1
        } else {
            0
        }
    }

    /// Sets sig to msg32||pk[..32]
    pub unsafe fn secp256k1_schnorrsig_sign(
        cx: *const Context,
        sig64: *mut c_uchar,
        msg32: *const c_uchar,
        keypair: *const Keypair,
        _aux_rand32: *const c_uchar
    ) -> c_int {
        check_context_flags(cx, SECP256K1_START_SIGN);
        // Check context is built for signing
        let mut new_kp = Keypair::new();
        if secp256k1_keypair_create(cx, &mut new_kp, (*keypair).0.as_ptr()) != 1 {
            return 0;
        }
        assert_eq!(new_kp, *keypair);
        // Sign
        let sig_sl = slice::from_raw_parts_mut(sig64 as *mut u8, 64);
        let msg_sl = slice::from_raw_parts(msg32 as *const u8, 32);
        sig_sl[..32].copy_from_slice(msg_sl);
        sig_sl[32..].copy_from_slice(&new_kp.0[32..64]);
        1
    }


    // Forwards to regular schnorrsig_sign function.
    pub unsafe fn secp256k1_schnorrsig_sign_custom(
        cx: *const Context,
        sig: *mut c_uchar,
        msg: *const c_uchar,
        _msg_len: size_t,
        keypair: *const Keypair,
        _extra_params: *const SchnorrSigExtraParams,
    ) -> c_int {
        secp256k1_schnorrsig_sign(cx, sig, msg, keypair, ptr::null())
    }

    // Extra keys
    pub unsafe fn secp256k1_keypair_create(
        cx: *const Context,
        keypair: *mut Keypair,
        seckey: *const c_uchar,
    ) -> c_int {
        check_context_flags(cx, SECP256K1_START_SIGN);
        if secp256k1_ec_seckey_verify(cx, seckey) == 0 { return 0; }

        let mut pk = PublicKey::new();
        if secp256k1_ec_pubkey_create(cx, &mut pk, seckey) == 0 { return 0; }

        let seckey_slice = slice::from_raw_parts(seckey, 32);
        (*keypair).0[..32].copy_from_slice(seckey_slice);
        (*keypair).0[32..].copy_from_slice(&pk.0);
        1
    }

    pub unsafe fn secp256k1_xonly_pubkey_parse(
        cx: *const Context,
        pubkey: *mut XOnlyPublicKey,
        input32: *const c_uchar,
    ) -> c_int {
        check_context_flags(cx, 0);
        let inslice = slice::from_raw_parts(input32, 32);
        (*pubkey).0[..32].copy_from_slice(inslice);
        (*pubkey).0[32..].copy_from_slice(inslice);
        test_cleanup_pk(pubkey as *mut PublicKey);
        test_pk_validate(cx, pubkey as *mut PublicKey)
    }

    pub unsafe fn secp256k1_xonly_pubkey_serialize(
        cx: *const Context,
        output32: *mut c_uchar,
        pubkey: *const XOnlyPublicKey,
    ) -> c_int {
        check_context_flags(cx, 0);
        let outslice = slice::from_raw_parts_mut(output32, 32);
        outslice.copy_from_slice(&(*pubkey).0[..32]);
        1
    }

    pub unsafe fn secp256k1_xonly_pubkey_from_pubkey(
        cx: *const Context,
        xonly_pubkey: *mut XOnlyPublicKey,
        pk_parity: *mut c_int,
        pubkey: *const PublicKey,
    ) -> c_int {
        check_context_flags(cx, 0);
        if !pk_parity.is_null() {
            *pk_parity = ((*pubkey).0[32] == 0).into();
        }
        (*xonly_pubkey).0.copy_from_slice(&(*pubkey).0);
        assert_eq!(test_pk_validate(cx, pubkey), 1);
        1
    }

    pub unsafe fn secp256k1_xonly_pubkey_tweak_add(
        cx: *const Context,
        output_pubkey: *mut PublicKey,
        internal_pubkey: *const XOnlyPublicKey,
        tweak32: *const c_uchar,
    ) -> c_int {
        check_context_flags(cx, SECP256K1_START_VERIFY);
        (*output_pubkey).0.copy_from_slice(&(*internal_pubkey).0);
        secp256k1_ec_pubkey_tweak_add(cx, output_pubkey, tweak32)
    }

    pub unsafe fn secp256k1_keypair_xonly_pub(
        cx: *const Context,
        pubkey: *mut XOnlyPublicKey,
        pk_parity: *mut c_int,
        keypair: *const Keypair
    ) -> c_int {
        check_context_flags(cx, 0);
        if !pk_parity.is_null() {
            *pk_parity = ((*keypair).0[64] == 0).into();
        }
        (*pubkey).0.copy_from_slice(&(*keypair).0[32..]);
        1
    }

    pub unsafe fn secp256k1_keypair_xonly_tweak_add(
        cx: *const Context,
        keypair: *mut Keypair,
        tweak32: *const c_uchar,
    ) -> c_int {
        check_context_flags(cx, SECP256K1_START_VERIFY);
        let mut pk = PublicKey::new();
        pk.0.copy_from_slice(&(*keypair).0[32..]);
        let mut sk = [0u8; 32];
        sk.copy_from_slice(&(*keypair).0[..32]);
        assert_eq!(secp256k1_ec_pubkey_tweak_add(cx, &mut pk, tweak32), 1);
        assert_eq!(secp256k1_ec_seckey_tweak_add(cx, (&mut sk[..]).as_mut_ptr(), tweak32), 1);
        (*keypair).0[..32].copy_from_slice(&sk);
        (*keypair).0[32..].copy_from_slice(&pk.0);
        1
    }

    pub unsafe fn secp256k1_xonly_pubkey_tweak_add_check(
        cx: *const Context,
        tweaked_pubkey32: *const c_uchar,
        tweaked_pubkey_parity: c_int,
        internal_pubkey: *const XOnlyPublicKey,
        tweak32: *const c_uchar,
    ) -> c_int {
        check_context_flags(cx, SECP256K1_START_VERIFY);
        let mut tweaked_pk = PublicKey::new();
        assert_eq!(secp256k1_xonly_pubkey_tweak_add(cx, &mut tweaked_pk, internal_pubkey, tweak32), 1);
        let in_slice = slice::from_raw_parts(tweaked_pubkey32, 32);
        if &tweaked_pk.0[..32] == in_slice && tweaked_pubkey_parity == (tweaked_pk.0[32] == 0).into() {
            1
        } else {
            0
        }
    }
}

#[cfg(secp256k1_fuzz)]
pub use self::fuzz_dummy::*;

#[cfg(test)]
mod tests {
    #[cfg(not(rust_secp_no_symbol_renaming))]
    #[test]
    fn test_strlen() {
        use std::ffi::CString;
        use super::strlen;

        let orig = "test strlen \t \n";
        let test = CString::new(orig).unwrap();

        assert_eq!(orig.len(), unsafe {strlen(test.as_ptr())});
    }
}
