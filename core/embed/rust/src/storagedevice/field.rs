use crate::{error::Error, micropython::obj::Obj, storagedevice::helpers};
use core::{marker::PhantomData, str};
use cstr_core::cstr;
use heapless::{String, Vec};

// NOTE: it is impossible to create const with the error messages -
// not &CStr nor &str

// TODO:
// default_value: <T>
// possible_values: Vec<T>
pub struct Field<T> {
    app: u8,
    key: u8,
    public: bool,
    max_len_is_exact: bool,
    _marker: PhantomData<*const T>,
}

impl<T> Field<T> {
    pub const fn public(app: u8, key: u8) -> Self {
        Self {
            app,
            key,
            public: true,
            max_len_is_exact: false,
            _marker: PhantomData,
        }
    }

    pub const fn private(app: u8, key: u8) -> Self {
        Self {
            app,
            key,
            public: false,
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

    fn appkey(&self) -> u16 {
        helpers::get_appkey(self.app, self.key, self.public)
    }

    pub fn has(&self) -> bool {
        helpers::storage_has_rs(self.appkey())
    }

    pub fn delete(&self) -> Result<(), Error> {
        helpers::storage_delete_safe_rs(self.appkey())
    }

    fn get_bytes<const N: usize>(&self, buf: &mut [u8; N]) -> Option<u16> {
        helpers::storage_get_rs(self.appkey(), buf)
    }

    fn set_bytes(&self, buf: &[u8]) -> Result<(), Error> {
        helpers::storage_set_rs(self.appkey(), buf)
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

    pub fn set(&self, val: u32) -> Result<(), Error> {
        self.set_bytes(&val.to_le_bytes())
    }
}

impl Field<u16> {
    pub fn get(&self) -> Option<u16> {
        let mut buf = [0u8; 2];
        let len = self.get_bytes(&mut buf);
        if matches!(len, Some(2)) {
            Some(u16::from_le_bytes(buf))
        } else {
            None
        }
    }

    pub fn get_result(&self) -> Result<Obj, Error> {
        if let Some(result) = self.get() {
            Ok(result.into())
        } else {
            Ok(Obj::const_none())
        }
    }

    pub fn set(&self, val: u16) -> Result<(), Error> {
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
            Ok(Obj::const_none())
        }
    }

    pub fn set(&self, val: u8) -> Result<(), Error> {
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

    pub fn set(&self, val: bool) -> Result<(), Error> {
        self.set_bytes(&[if val { 1 } else { 0 }])
    }

    pub fn set_true_or_delete(self, val: bool) -> Result<(), Error> {
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
            let string = String::from(helpers::from_bytes_to_str(&buf[..len as usize])?);
            if self.max_len_is_exact && string.len() as usize != N {
                Ok(None)
            } else if string.len() as usize > N {
                // TODO: we could probably just return None and get rid of the Result
                Err(Error::ValueError(cstr!("Value too big")))
            } else {
                Ok(Some(string))
            }
        } else {
            Ok(None)
        }
    }

    pub fn get_result(&self) -> Result<Obj, Error> {
        if let Some(result) = self.get()? {
            result.as_str().try_into()
        } else {
            Ok(Obj::const_none())
        }
    }

    pub fn set(&self, val: &str) -> Result<(), Error> {
        if self.max_len_is_exact && val.chars().count() as usize != N {
            Err(Error::ValueError(cstr!("Value is not exact")))
        } else if val.chars().count() as usize > N {
            Err(Error::ValueError(cstr!("Value too big")))
        } else {
            self.set_bytes(val.as_bytes())
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
            } else if len as usize > N {
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
            Ok(Obj::const_none())
        }
    }

    pub fn set(&self, val: &[u8]) -> Result<(), Error> {
        if self.max_len_is_exact && val.len() as usize != N {
            Err(Error::ValueError(cstr!("Value is not exact")))
        } else if val.len() as usize > N {
            Err(Error::ValueError(cstr!("Value too big")))
        } else {
            self.set_bytes(val)
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
