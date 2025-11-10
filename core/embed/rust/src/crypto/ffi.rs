#![allow(non_camel_case_types)]

include!(concat!(env!("OUT_DIR"), "/crypto.rs"));

// Struct size is dependent on macros, do a basic check that it's same on both
// GCC and Clang(bindgen)
const STATIC_ASSERT_GCM_CTX_SIZE: () = {
    debug_assert!(core::mem::size_of::<gcm_ctx>() == 352);
};
