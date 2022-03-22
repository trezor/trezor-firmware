use crate::{error::Error, micropython::obj::Obj, trezorhal::secbool};
use core::{marker::PhantomData, str};
use cstr_core::cstr;
use heapless::{String, Vec};

const FLAG_PUBLIC: u8 = 0x80;

const NONE: Obj = Obj::const_none();

extern "C" {
    // storage.h
    fn storage_has(key: u16) -> secbool::Secbool;
    fn storage_delete(key: u16) -> secbool::Secbool;
    fn storage_get(key: u16, val: *const u8, max_len: u16, len: *mut u16) -> secbool::Secbool;
    fn storage_set(key: u16, val: *const u8, len: u16) -> secbool::Secbool;
}

// TODO:
// default_value: <T>
// possible_values: Vec<T>
pub struct Field<T> {
    app: u8,
    key: u8,
    public: bool,
    max_len_error: bool, // Could pass the whole Error somehow (const issues)
    max_len_is_exact: bool,
    _marker: PhantomData<*const T>,
}

impl<T> Field<T> {
    pub const fn public(app: u8, key: u8) -> Self {
        Self {
            app,
            key,
            public: true,
            max_len_error: false,
            max_len_is_exact: false,
            _marker: PhantomData,
        }
    }

    pub const fn private(app: u8, key: u8) -> Self {
        Self {
            app,
            key,
            public: false,
            max_len_error: false,
            max_len_is_exact: false,
            _marker: PhantomData,
        }
    }

    pub const fn exact(self) -> Self {
        Self {
            max_len_is_exact: true,
            ..self
        }
    }

    pub const fn max_len_error(self) -> Self {
        Self {
            max_len_error: true,
            ..self
        }
    }

    fn appkey(&self) -> u16 {
        if self.public {
            ((self.app | FLAG_PUBLIC) as u16) << 8 | self.key as u16
        } else {
            (self.app as u16) << 8 | self.key as u16
        }
    }

    pub fn has(&self) -> bool {
        secbool::TRUE == unsafe { storage_has(self.appkey()) }
    }

    pub fn delete(&self) -> bool {
        secbool::TRUE == unsafe { storage_delete(self.appkey()) }
    }

    fn get_bytes<const N: usize>(&self, buf: &mut [u8; N]) -> Option<u16> {
        assert!(N <= u16::MAX as usize);
        let mut len = 0;
        let result = unsafe { storage_get(self.appkey(), buf.as_mut_ptr(), N as u16, &mut len) };
        if result != secbool::TRUE {
            None
        } else {
            Some(len)
        }
    }

    // TODO: cannot throw an exception when storage_set returns false?
    fn set_bytes(&self, buf: &[u8]) -> bool {
        assert!(buf.len() <= u16::MAX as usize);
        secbool::TRUE == unsafe { storage_set(self.appkey(), buf.as_ptr(), buf.len() as u16) }
    }
}

impl Field<u32> {
    pub fn get(&self) -> Option<u32> {
        let mut buf = [0u8; 4];
        let len = self.get_bytes(&mut buf);
        if matches!(len, Some(4)) {
            Some(u32::from_le_bytes(buf))
        } else {
            None
        }
    }

    pub fn set(&self, val: u32) -> bool {
        self.set_bytes(&val.to_le_bytes())
    }
}

impl Field<u16> {
    pub fn get(&self) -> Option<u16> {
        let mut buf = [0u8; 2];
        let len = self.get_bytes(&mut buf);
        if matches!(len, Some(1)) || matches!(len, Some(2)) {
            Some(u16::from_le_bytes(buf))
        } else {
            None
        }
    }

    pub fn get_result(&self) -> Result<Obj, Error> {
        if let Some(result) = self.get() {
            Ok(result.into())
        } else {
            Ok(NONE)
        }
    }

    pub fn set(&self, val: u16) -> bool {
        self.set_bytes(&val.to_le_bytes())
    }
}

impl Field<u8> {
    pub fn get(&self) -> Option<u8> {
        let mut buf = [0u8];
        let len = self.get_bytes(&mut buf);
        if matches!(len, Some(1)) {
            Some(buf[0])
        } else {
            None
        }
    }

    pub fn get_result(&self) -> Result<Obj, Error> {
        if let Some(result) = self.get() {
            Ok(result.into())
        } else {
            Ok(NONE)
        }
    }

    pub fn set(&self, val: u8) -> bool {
        self.set_bytes(&[val])
    }
}

impl Field<bool> {
    pub fn get(&self) -> Option<bool> {
        let mut buf = [0u8];
        let len = self.get_bytes(&mut buf);
        if matches!(len, Some(1)) {
            Some(buf[0] != 0)
        } else {
            None
        }
    }

    pub fn get_result(&self) -> Result<Obj, Error> {
        if let Some(result) = self.get() {
            Ok(result.into())
        } else {
            // If nothing there, assume false
            Ok(false.into())
        }
    }

    pub fn set(&self, val: bool) -> bool {
        self.set_bytes(&[if val { 1 } else { 0 }])
    }

    pub fn set_true_or_delete(self, val: bool) -> bool {
        if val {
            self.set(true)
        } else {
            self.delete()
        }
    }
}

impl<const N: usize> Field<String<N>> {
    pub fn get(&self) -> Result<Option<String<N>>, Error> {
        let mut buf = [0u8; N];
        let len = self.get_bytes(&mut buf);
        if let Some(len) = len {
            if self.max_len_is_exact && len as usize != N {
                Ok(None)
            } else if self.max_len_error && len as usize > N {
                Err(Error::ValueError(cstr!("Value too big")))
            } else {
                Ok(Some(String::from(
                    str::from_utf8(&buf[..len as usize]).ok().unwrap(),
                )))
            }
        } else {
            Ok(None)
        }
    }

    pub fn get_result(&self) -> Result<Obj, Error> {
        if let Some(result) = self.get()? {
            result.as_str().try_into()
        } else {
            Ok(NONE)
        }
    }

    pub fn set(&self, val: &str) -> Result<bool, Error> {
        if self.max_len_is_exact && val.chars().count() as usize != N {
            Err(Error::ValueError(cstr!("String is not exact length")))
        } else if self.max_len_error && val.chars().count() as usize > N {
            Err(Error::ValueError(cstr!("String too long")))
        } else {
            Ok(self.set_bytes(val.as_bytes()))
        }
    }
}

impl<const N: usize> Field<Vec<u8, N>> {
    pub fn get(&self) -> Result<Option<Vec<u8, N>>, Error> {
        let mut buf = [0u8; N];
        let len = self.get_bytes(&mut buf);
        if let Some(len) = len {
            if self.max_len_is_exact && len as usize != N {
                Ok(None)
            } else if self.max_len_error && len as usize > N {
                // TODO: we could probably just return None and get rid of the Result
                Err(Error::ValueError(cstr!("Value too big")))
            } else {
                Ok(Some((&buf[..len as usize]).iter().cloned().collect()))
            }
        } else {
            Ok(None)
        }
    }

    pub fn get_result(&self) -> Result<Obj, Error> {
        if let Some(result) = self.get()? {
            (&result as &[u8]).try_into()
        } else {
            Ok(NONE)
        }
    }

    pub fn set(&self, val: &[u8]) -> Result<bool, Error> {
        if self.max_len_is_exact && val.len() as usize != N {
            Err(Error::ValueError(cstr!("Value is not exact size")))
        } else if self.max_len_error && val.len() as usize > N {
            Err(Error::ValueError(cstr!("Value too big")))
        } else {
            Ok(self.set_bytes(val))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // TODO: we could have some global Map for testing purposes,
    // and we would be mocking the storage_set/get/has
    // OR https://stackoverflow.com/questions/63850791/unit-testing-mocking-and-traits-in-rust

    #[test]
    fn test_field() {
        const VERSION: Field<Vec<u8, 1>> = Field::private(0x01, 0x01);

        assert!(!VERSION.has());
    }
}
