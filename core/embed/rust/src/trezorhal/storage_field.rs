use core::marker::PhantomData;
use core::str;
use super::{
    ffi,
    storage::{self, StorageError},
};
use heapless::{String, Vec};

const TRUE_BYTE: u8 = 0x01;
const FALSE_BYTE: u8 = 0x00;

const MAX_STRING: usize = 300;

#[repr(u8)]
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub enum FieldAccess {
    Private = 0x00,
    PublicReadable = ffi::FLAG_PUBLIC as u8,
    PublicWritable = ffi::FLAGS_WRITE as u8,
}

// TODO:
// default_value: <T>
// possible_values: Vec<T>
pub struct Field<T> {
    app: u8,
    key: u8,
    access: FieldAccess,
    max_len_is_exact: bool,
    _marker: PhantomData<*const T>,
}

impl<T> Field<T> {
    const fn new(app: u8, key: u8, access: FieldAccess) -> Self {
        assert!(app < ffi::MAX_APPID as u8);
        Self {
            app,
            key,
            access,
            max_len_is_exact: false,
            _marker: PhantomData,
        }
    }

    pub const fn public(app: u8, key: u8) -> Self {
        Self::new(app, key, FieldAccess::PublicReadable)
    }

    pub const fn public_writable(app: u8, key: u8) -> Self {
        Self::new(app, key, FieldAccess::PublicWritable)
    }

    pub const fn private(app: u8, key: u8) -> Self {
        Self::new(app, key, FieldAccess::Private)
    }

    pub const fn exact(self) -> Self {
        Self {
            max_len_is_exact: true,
            ..self
        }
    }

    fn appkey(&self) -> u16 {
        let app = self.app | self.access as u8;
        (app as u16) << 8 | self.key as u16
    }

    pub fn has(&self) -> bool {
        storage::has(self.appkey())
    }

    pub fn delete(&self) -> Result<(), StorageError> {
        // If there is nothing, storage_delete() would return false
        if !self.has() {
            return Ok(());
        }

        if !storage::delete(self.appkey()) {
            Err(StorageError::WriteFailed)
        } else {
            Ok(())
        }
    }

    const fn is_len_ok(&self, len: usize, expected: usize) -> bool {
        if self.max_len_is_exact {
            len == expected
        } else {
            len <= expected
        }
    }
}

impl Field<u32> {
    pub fn get(&self) -> Option<u32> {
        let mut buf = [0u8; 4];
        let len = storage::get(self.appkey(), &mut buf);
        if matches!(len, Ok(4)) {
            Some(u32::from_le_bytes(buf))
        } else {
            None
        }
    }

    pub fn set(&self, val: u32) -> Result<(), StorageError> {
        storage::set(self.appkey(), &val.to_le_bytes())
    }
}

impl Field<u16> {
    pub fn get(&self) -> Option<u16> {
        let mut buf = [0u8; 2];
        let len = storage::get(self.appkey(), &mut buf);
        if matches!(len, Ok(2)) {
            Some(u16::from_le_bytes(buf))
        } else {
            None
        }
    }

    pub fn set(&self, val: u16) -> Result<(), StorageError> {
        storage::set(self.appkey(), &val.to_le_bytes())
    }
}

impl Field<u8> {
    pub fn get(&self) -> Option<u8> {
        let mut buf = [0u8];
        let len = storage::get(self.appkey(), &mut buf);
        if matches!(len, Ok(1)) {
            Some(buf[0])
        } else {
            None
        }
    }

    pub fn set(&self, val: u8) -> Result<(), StorageError> {
        storage::set(self.appkey(), &[val])
    }
}

impl Field<bool> {
    pub fn get(&self) -> Option<bool> {
        let mut buf = [0u8];
        let len = storage::get(self.appkey(), &mut buf);
        if matches!(len, Ok(1)) {
            Some(buf[0] == TRUE_BYTE)
        } else {
            None
        }
    }

    pub fn set(&self, val: bool) -> Result<(), StorageError> {
        storage::set(self.appkey(), &[if val { TRUE_BYTE } else { FALSE_BYTE }])
    }

    pub fn set_true_or_delete(self, val: bool) -> Result<(), StorageError> {
        if val {
            self.set(true)
        } else {
            self.delete()
        }
    }
}

impl<const N: usize> Field<String<N>> {
    pub fn get(&self) -> Option<String<N>> {
        let mut buf = [0u8; MAX_STRING];
        let len = storage::get(self.appkey(), &mut buf);
        len.ok().and_then(|len| {
            let string = String::from(str::from_utf8(&buf[..len as usize]).ok().unwrap());
            if self.is_len_ok(string.chars().count(), N) {
                Some(string)
            } else {
                None
            }
        })
    }

    pub fn set(&self, val: &str) -> Result<(), StorageError> {
        if self.is_len_ok(val.chars().count(), N) {
            storage::set(self.appkey(), val.as_bytes())
        } else {
            Err(StorageError::InvalidData)
        }
    }
}

impl<const N: usize> Field<Vec<u8, N>> {
    pub fn get(&self) -> Option<Vec<u8, N>> {
        let mut buf = [0u8; N];
        let len = storage::get(self.appkey(), &mut buf);
        len.ok().and_then(|len| {
            if self.is_len_ok(len, N) {
                Vec::from_slice(&buf[..len]).ok()
            } else {
                None
            }
        })
    }

    pub fn set(&self, val: &[u8]) -> Result<(), StorageError> {
        if self.is_len_ok(val.len(), N) {
            storage::set(self.appkey(), val)
        } else {
            Err(StorageError::InvalidData)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // TODO: we could have some global Map for testing purposes,
    // and we would be mocking the storage_set/get/has
    // OR https://stackoverflow.com/questions/63850791/unit-testing-mocking-and-traits-in-rust

    fn init_storage(unlock: bool) {
        storage::init();
        storage::wipe();
        storage::lock();
        if unlock {
            storage::unlock("", None);
        }
    }

    const VERSION: Field<u8> = Field::private(0x01, 0x01);
    const PUBLIC_STRING: Field<String<10>> = Field::public(0x01, 0x02);

    #[test]
    fn test_basic() {
        init_storage(true);

        assert!(!VERSION.has());
        assert!(VERSION.set(10).is_ok());
        assert_eq!(VERSION.get(), Some(10));
        assert!(VERSION.has());
        assert!(VERSION.delete().is_ok());
    }

    #[test]
    fn test_private() {
        init_storage(true);

        assert!(VERSION.set(10).is_ok());
        assert_eq!(VERSION.get(), Some(10));

        storage::lock();
        assert!(!VERSION.has());
        assert!(VERSION.set(10).is_err());
        assert!(VERSION.get().is_none());
    }

    #[test]
    fn test_public() {
        init_storage(true);

        assert!(PUBLIC_STRING.set("hello").is_ok());
        assert_eq!(PUBLIC_STRING.get(), Some(String::from("hello")));

        storage::lock();
        assert!(PUBLIC_STRING.set("world").is_err());
        assert_eq!(PUBLIC_STRING.get(), Some(String::from("hello")));
    }
}
