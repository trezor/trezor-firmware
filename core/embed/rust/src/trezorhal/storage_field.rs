use super::{
    ffi,
    storage::{self, StorageError, StorageResult},
};
use core::{marker::PhantomData, str};
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

    pub fn appkey(&self) -> u16 {
        let app = self.app | self.access as u8;
        (app as u16) << 8 | self.key as u16
    }

    /// Checking if the length of the field is not unexpected
    const fn is_len_ok(&self, len: usize, expected: usize) -> bool {
        if self.max_len_is_exact {
            len == expected
        } else {
            len <= expected
        }
    }
}

// Traits to make sure all the fields are implemented correctly
pub trait FieldOpsBase {
    fn is_set(&self) -> bool;
    fn delete(&self) -> StorageResult<()>;
}
impl<T> FieldOpsBase for Field<T> {
    fn is_set(&self) -> bool {
        storage::has(self.appkey())
    }

    fn delete(&self) -> StorageResult<()> {
        // If field is not there, storage::delete() would return Err()
        if !self.is_set() {
            return Ok(());
        }

        if !storage::delete(self.appkey()) {
            Err(StorageError::WriteFailed)
        } else {
            Ok(())
        }
    }
}

pub trait FieldGetSet<T> {
    fn get(&self) -> Option<T>;
    fn set(&self, value: T) -> StorageResult<()>;
}

pub trait FieldOps<T>: FieldOpsBase + FieldGetSet<T> {}
impl<T> FieldOps<T> for Field<T> where Field<T>: FieldGetSet<T> {}

impl FieldGetSet<u32> for Field<u32> {
    fn get(&self) -> Option<u32> {
        let mut buf = [0u8; 4];
        let len = storage::get(self.appkey(), &mut buf);
        if matches!(len, Ok(4)) {
            Some(u32::from_be_bytes(buf))
        } else {
            None
        }
    }

    fn set(&self, val: u32) -> StorageResult<()> {
        storage::set(self.appkey(), &val.to_be_bytes())
    }
}

impl FieldGetSet<u16> for Field<u16> {
    fn get(&self) -> Option<u16> {
        let mut buf = [0u8; 2];
        let len = storage::get(self.appkey(), &mut buf);
        if matches!(len, Ok(2)) {
            Some(u16::from_be_bytes(buf))
        } else {
            None
        }
    }

    fn set(&self, val: u16) -> StorageResult<()> {
        storage::set(self.appkey(), &val.to_be_bytes())
    }
}

impl FieldGetSet<u8> for Field<u8> {
    fn get(&self) -> Option<u8> {
        let mut buf = [0u8];
        let len = storage::get(self.appkey(), &mut buf);
        if matches!(len, Ok(1)) {
            Some(buf[0])
        } else {
            None
        }
    }

    fn set(&self, val: u8) -> StorageResult<()> {
        storage::set(self.appkey(), &[val])
    }
}

impl FieldGetSet<bool> for Field<bool> {
    fn get(&self) -> Option<bool> {
        let mut buf = [0u8];
        let len = storage::get(self.appkey(), &mut buf);
        if matches!(len, Ok(1)) {
            Some(buf[0] == TRUE_BYTE)
        } else {
            None
        }
    }

    fn set(&self, val: bool) -> StorageResult<()> {
        storage::set(self.appkey(), &[if val { TRUE_BYTE } else { FALSE_BYTE }])
    }
}

/// Helper function defined only on boolean Fields
pub fn set_true_or_delete(field: impl FieldOps<bool>, value: bool) -> StorageResult<()> {
    if value {
        field.set(true)
    } else {
        field.delete()
    }
}

impl<const N: usize> FieldGetSet<String<N>> for Field<String<N>> {
    fn get(&self) -> Option<String<N>> {
        let mut buf = [0u8; MAX_STRING];
        let len = storage::get(self.appkey(), &mut buf);
        len.ok().and_then(|len| {
            let string = match str::from_utf8(&buf[..len as usize]) {
                Ok(s) => String::from(s),
                Err(_) => return None,
            };
            if self.is_len_ok(string.chars().count(), N) {
                Some(string)
            } else {
                None
            }
        })
    }

    fn set(&self, val: String<N>) -> StorageResult<()> {
        if self.is_len_ok(val.len(), N) {
            storage::set(self.appkey(), val.as_bytes())
        } else {
            Err(StorageError::InvalidData)
        }
    }
}

impl<const N: usize> FieldGetSet<Vec<u8, N>> for Field<Vec<u8, N>> {
    fn get(&self) -> Option<Vec<u8, N>> {
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

    fn set(&self, val: Vec<u8, N>) -> Result<(), StorageError> {
        if self.is_len_ok(val.len(), N) {
            storage::set(self.appkey(), val.as_ref())
        } else {
            Err(StorageError::InvalidData)
        }
    }
}

/// For usage in U2F
pub struct Counter(Field<u32>);

impl Counter {
    pub const fn public(app: u8, key: u8) -> Self {
        Self(Field::public(app, key))
    }
    pub const fn public_writable(app: u8, key: u8) -> Self {
        Self(Field::public_writable(app, key))
    }
    pub const fn private(app: u8, key: u8) -> Self {
        Self(Field::private(app, key))
    }

    pub fn get_and_increment(&self) -> StorageResult<u32> {
        storage::get_next_counter(self.0.appkey())
    }
    pub fn set(&self, value: u32) -> StorageResult<()> {
        storage::set_counter(self.0.appkey(), value)
    }
}

#[cfg(test)]
mod tests {
    use cstr_core::cstr;

    use super::*;
    use crate::{
        error::Error,
        micropython::buffer::{Buffer, StrBuffer},
    };

    fn init_storage(unlock: bool) {
        storage::init();
        storage::wipe();
        storage::lock();
        if unlock {
            storage::unlock("", None);
        }
    }

    const VERSION: Field<u8> = Field::private(0x01, 0x01);
    const PRIVATE_BOOL: Field<bool> = Field::private(0x01, 0x02);
    const PUBLIC_STRING: Field<String<10>> = Field::public(0x01, 0x03);
    const PUBLIC_VEC: Field<Vec<u8, 2>> = Field::public(0x01, 0x04);

    #[test]
    fn test_basic() {
        init_storage(true);

        assert!(!VERSION.is_set());
        assert!(VERSION.set(10).is_ok());
        assert_eq!(VERSION.get(), Some(10));
        assert!(VERSION.is_set());
        assert!(VERSION.delete().is_ok());
        assert!(!VERSION.is_set());
    }

    #[test]
    fn test_private() {
        init_storage(true);

        assert!(VERSION.set(10).is_ok());
        assert_eq!(VERSION.get(), Some(10));

        storage::lock();
        assert!(!VERSION.is_set());
        assert!(VERSION.set(10).is_err());
        assert!(VERSION.get().is_none());
    }

    #[test]
    fn test_public() {
        init_storage(true);

        assert!(PUBLIC_STRING.set(String::from("hello")).is_ok());
        assert_eq!(PUBLIC_STRING.get(), Some(String::from("hello")));

        storage::lock();
        assert!(PUBLIC_STRING.set(String::from("world")).is_err());
        assert_eq!(PUBLIC_STRING.get(), Some(String::from("hello")));
    }

    #[test]
    fn test_value_too_long_str() {
        init_storage(true);

        const GOOD_VALUE: &str = "hello";
        const TOO_LONG_VALUE: &str = "someveryverylongstring";

        // Normal input
        let good_string = StrBuffer::from(GOOD_VALUE).try_into().unwrap();
        assert!(PUBLIC_STRING.set(good_string).is_ok());
        assert_eq!(PUBLIC_STRING.get(), Some(String::from(GOOD_VALUE)));

        // Input too long
        // Needs a function because the error happens in StrBuffer::try_into,
        // which needs a context of String<N> being present in PUBLIC_STRING.set()
        fn set_too_long_string() -> Result<(), Error> {
            let long_string = StrBuffer::from(TOO_LONG_VALUE).try_into()?;
            PUBLIC_STRING.set(long_string)?;
            Ok(())
        }

        let result = set_too_long_string();
        assert!(result.is_err());
        assert_eq!(
            result.err(),
            Some(Error::ValueError(cstr!("String is too long to fit")))
        );

        assert_eq!(PUBLIC_STRING.get(), Some(String::from(GOOD_VALUE)));
    }

    #[test]
    fn test_value_too_long_vec() {
        init_storage(true);

        const GOOD_VALUE: &[u8; 2] = &[1, 255];
        const TOO_LONG_VALUE: &[u8; 3] = &[1, 255, 123];

        // Normal input
        let good_string = Buffer::from(GOOD_VALUE).try_into().unwrap();
        assert!(PUBLIC_VEC.set(good_string).is_ok());
        assert_eq!(PUBLIC_VEC.get(), Vec::from_slice(GOOD_VALUE).ok());

        // Input too long
        // Needs a function because the error happens in Buffer::try_into,
        // which needs a context of Vec<u8, N> being present in PUBLIC_VEC.set()
        fn set_too_long_vec() -> Result<(), Error> {
            let too_long_vec = Buffer::from(TOO_LONG_VALUE).try_into()?;
            PUBLIC_VEC.set(too_long_vec)?;
            Ok(())
        }

        let result = set_too_long_vec();
        assert!(result.is_err());
        assert_eq!(
            result.err(),
            Some(Error::ValueError(cstr!("Buffer is too long to fit")))
        );

        assert_eq!(PUBLIC_VEC.get(), Vec::from_slice(GOOD_VALUE).ok());
    }

    #[test]
    fn test_set_true_or_delete() {
        init_storage(true);

        assert!(!PRIVATE_BOOL.is_set());
        assert!(PRIVATE_BOOL.set(false).is_ok());
        assert!(PRIVATE_BOOL.is_set());
        assert_eq!(PRIVATE_BOOL.get(), Some(false));

        assert!(set_true_or_delete(PRIVATE_BOOL, true).is_ok());
        assert_eq!(PRIVATE_BOOL.get(), Some(true));

        assert!(set_true_or_delete(PRIVATE_BOOL, false).is_ok());
        assert!(!PRIVATE_BOOL.is_set());
    }
}
