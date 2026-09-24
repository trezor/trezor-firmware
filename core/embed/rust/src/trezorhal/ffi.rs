#![allow(non_camel_case_types)]
#![allow(non_upper_case_globals)]
#![allow(clippy::upper_case_acronyms)]
#![allow(non_snake_case)]
#![allow(dead_code)]
#![allow(unnecessary_transmutes)]
#![allow(clippy::transmute_int_to_bool)]
#![allow(clippy::too_many_arguments)]
#![allow(clippy::cast_lossless)]

include!(concat!(env!("OUT_DIR"), "/trezorhal.rs"));

// FIXME should go into rtl/ somehow
pub type Status = ts_t;
pub struct StatusError {
    pub code: core::num::NonZeroI32,
}

impl Status {
    pub fn code(&self) -> i32 {
        self.code
    }

    pub fn is_ok(&self) -> bool {
        self.code == 0
    }

    pub fn ok(&self) -> Result<(), StatusError> {
        match core::num::NonZeroI32::new(self.code()) {
            Some(code) => Err(StatusError { code }),
            None => Ok(()),
        }
    }
}
