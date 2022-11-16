//! This crate is a wrapper of blake2b.c.
//! Purpose of this crate is to replace blake2_simd crate
//! required by some Rust dependencies.

#![no_std]

use cty::c_void;

mod ffi;

pub const BLOCKBYTES: usize = 128;
pub const KEYBYTES: usize = 64;
pub const OUTBYTES: usize = 64;
pub const PERSONALBYTES: usize = 16;
pub const SALTBYTES: usize = 16;

#[derive(Clone, Copy)]
pub struct Hash {
    bytes: [u8; OUTBYTES],
    len: u8,
}

impl Hash {
    pub fn as_bytes(&self) -> &[u8] {
        &self.bytes[..self.len as usize]
    }

    #[inline]
    pub fn as_array(&self) -> &[u8; OUTBYTES] {
        &self.bytes
    }
}

#[derive(Clone, Copy)]
pub struct Params<'a, 'b> {
    key: Option<&'a [u8]>,
    personal: Option<&'b [u8]>,
    outlen: usize,
}

impl<'a, 'b> Params<'a, 'b> {
    pub fn new() -> Self {
        Params {
            key: None,
            personal: None,
            outlen: OUTBYTES,
        }
    }

    pub fn hash_length(&mut self, length: usize) -> &mut Self {
        self.outlen = length;
        self
    }

    pub fn key(&mut self, key: &'a [u8]) -> &mut Self {
        self.key = Some(key);
        self
    }

    pub fn personal(&mut self, personal: &'b [u8]) -> &mut Self {
        self.personal = Some(personal);
        self
    }

    pub fn to_state(self) -> State {
        assert!(self.key.is_none() || self.personal.is_none());
        let mut ctx = ffi::__blake2b_state {
            h: [0u64; 8usize],
            t: [0u64; 2usize],
            f: [0u64; 2usize],
            buf: [0u8; 128usize],
            buflen: 0usize,
            outlen: 0usize,
            last_node: 0u8,
        };
        let res = unsafe {
            match (self.key, self.personal) {
                (None, None) => ffi::blake2b_Init(&mut ctx, self.outlen),
                (Some(key), None) => ffi::blake2b_InitKey(
                    &mut ctx,
                    self.outlen,
                    key.as_ptr() as *const c_void,
                    key.len(),
                ),
                (None, Some(personal)) => ffi::blake2b_InitPersonal(
                    &mut ctx,
                    self.outlen,
                    personal.as_ptr() as *const c_void,
                    personal.len(),
                ),
                (Some(_), Some(_)) => {
                    panic!("Using key and personalization simultaniously not implemented.")
                }
            }
        };
        if res < 0 {
            panic!("Blake2b initialization failed.")
        }
        State { ctx }
    }

    pub fn hash(self, data: &[u8]) -> Hash {
        self.to_state().update(data).finalize()
    }
}

#[derive(Clone)]
pub struct State {
    ctx: ffi::blake2b_state,
}

impl State {
    pub fn new() -> Self {
        Params::new().to_state()
    }

    pub fn update(&mut self, data: &[u8]) -> &mut Self {
        unsafe {
            ffi::blake2b_Update(&mut self.ctx, data.as_ptr() as *const c_void, data.len());
        }
        self
    }

    pub fn finalize(&self) -> Hash {
        // Method `finalize` takes imutable reference to the self
        // to mirror `blake2b_simd` API.
        let mut bytes = [0u8; OUTBYTES];
        let ptr = bytes.as_mut_ptr() as *mut c_void;
        // clone `ctx` to get a mutable reference required by `ffi::blake2b_Final`
        let mut ctx = self.ctx.clone();
        let res = unsafe { ffi::blake2b_Final(&mut ctx, ptr, OUTBYTES) };
        if res < 0 {
            panic!("Blake2b hash finalization failed.")
        }
        Hash {
            bytes,
            len: self.ctx.outlen as u8,
        }
    }
}

pub fn blake2b(data: &[u8]) -> Hash {
    State::new().update(data).finalize()
}
