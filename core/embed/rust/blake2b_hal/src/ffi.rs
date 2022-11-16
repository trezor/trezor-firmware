#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct __blake2b_state {
    pub h: [u64; 8usize],
    pub t: [u64; 2usize],
    pub f: [u64; 2usize],
    pub buf: [u8; 128usize],
    pub buflen: usize,
    pub outlen: usize,
    pub last_node: u8,
}
#[allow(non_camel_case_types)]
pub type blake2b_state = __blake2b_state;
extern "C" {
    pub fn blake2b_Init(S: *mut blake2b_state, outlen: usize) -> cty::c_int;
}
extern "C" {
    pub fn blake2b_InitKey(
        S: *mut blake2b_state,
        outlen: usize,
        key: *const cty::c_void,
        keylen: usize,
    ) -> cty::c_int;
}
extern "C" {
    pub fn blake2b_InitPersonal(
        S: *mut blake2b_state,
        outlen: usize,
        personal: *const cty::c_void,
        personal_len: usize,
    ) -> cty::c_int;
}
extern "C" {
    pub fn blake2b_Update(
        S: *mut blake2b_state,
        pin: *const cty::c_void,
        inlen: usize,
    ) -> cty::c_int;
}
extern "C" {
    pub fn blake2b_Final(S: *mut blake2b_state, out: *mut cty::c_void, outlen: usize)
        -> cty::c_int;
}
