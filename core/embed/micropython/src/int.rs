use crate::gc::Gc;
use crate::py_object::HasBaseType;
use crate::typ::Type;
use crate::{Error, Obj, ffi};

pub type Int = ffi::mp_obj_int_t;

// SAFETY: Int type is a builtin and therefore has the right layout.
unsafe impl HasBaseType for Int {
    fn obj_type() -> &'static Type {
        unsafe { &ffi::mp_type_int }
    }
}

const MPZ_DIGIT_BIT_SIZE: usize = core::mem::size_of::<ffi::mpz_dig_t>() * 8;

type Mpz = ffi::mpz_t;

impl Mpz {
    fn digits(&self) -> &[ffi::mpz_dig_t] {
        // SAFETY: digits are private to the mpz object, which we hold immutably,
        // so the lifetime of the slice is the same as the lifetime of the holder.
        unsafe { core::slice::from_raw_parts(self.dig.cast(), self.len) }
    }

    fn is_negative(&self) -> bool {
        self.neg() != 0
    }

    fn value_u32(&self) -> Result<u32, Error> {
        let digits = self.digits();
        const DIGITS_TO_SKIP: usize =
            core::mem::size_of::<u32>() / core::mem::size_of::<ffi::mpz_dig_t>();
        if digits.iter().skip(DIGITS_TO_SKIP).any(|&digit| digit != 0) {
            return Err(Error::OutOfRange);
        }
        let value = digits.iter().rev().fold(0, |acc, &digit| {
            (acc << MPZ_DIGIT_BIT_SIZE) | (digit as u32)
        });
        Ok(value)
    }

    fn value_u64(&self) -> Result<u64, Error> {
        let digits = self.digits();
        const DIGITS_TO_SKIP: usize =
            core::mem::size_of::<u64>() / core::mem::size_of::<ffi::mpz_dig_t>();
        if digits.iter().skip(DIGITS_TO_SKIP).any(|&digit| digit != 0) {
            return Err(Error::OutOfRange);
        }
        let value = digits.iter().rev().fold(0, |acc, &digit| {
            (acc << MPZ_DIGIT_BIT_SIZE) | (digit as u64)
        });
        Ok(value)
    }
}

impl TryFrom<&Mpz> for u32 {
    type Error = Error;

    fn try_from(mpz: &Mpz) -> Result<Self, Self::Error> {
        if mpz.is_negative() {
            return Err(Error::OutOfRange);
        }
        mpz.value_u32()
    }
}

impl TryFrom<&Mpz> for u64 {
    type Error = Error;

    fn try_from(mpz: &Mpz) -> Result<Self, Self::Error> {
        if mpz.is_negative() {
            return Err(Error::OutOfRange);
        }
        mpz.value_u64()
    }
}

impl TryFrom<&Mpz> for i32 {
    type Error = Error;

    fn try_from(mpz: &Mpz) -> Result<Self, Self::Error> {
        let value_u32 = mpz.value_u32()?;
        if !mpz.is_negative() {
            if value_u32 <= i32::MAX as u32 {
                Ok(value_u32 as i32)
            } else {
                Err(Error::OutOfRange)
            }
        } else {
            if value_u32 <= i32::MIN.unsigned_abs() {
                Ok((value_u32 as i32).wrapping_neg())
            } else {
                Err(Error::OutOfRange)
            }
        }
    }
}

impl TryFrom<&Mpz> for i64 {
    type Error = Error;

    fn try_from(mpz: &Mpz) -> Result<Self, Self::Error> {
        let value_u64 = mpz.value_u64()?;
        if !mpz.is_negative() {
            if value_u64 <= i64::MAX as u64 {
                Ok(value_u64 as i64)
            } else {
                Err(Error::OutOfRange)
            }
        } else {
            if value_u64 <= i64::MIN.unsigned_abs() {
                Ok((value_u64 as i64).wrapping_neg())
            } else {
                Err(Error::OutOfRange)
            }
        }
    }
}

macro_rules! try_from_obj_to_int {
    ($type:ty) => {
        impl TryFrom<Obj> for $type {
            type Error = Error;

            fn try_from(obj: Obj) -> Result<Self, Self::Error> {
                if obj.is_small_int() {
                    return Ok(obj.small_int_value() as $type);
                } else {
                    let int: Gc<Int> = obj.try_into()?;
                    // SAFETY: we discard the reference at the end of the function
                    let mpz = unsafe {
                        let int = Gc::as_ref(&int);
                        &int.mpz
                    };
                    mpz.try_into()
                }
            }
        }
    };
}

try_from_obj_to_int!(u32);
try_from_obj_to_int!(u64);
try_from_obj_to_int!(i32);
try_from_obj_to_int!(i64);

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runtime::catch_exception;

    fn new_i64(value: i64) -> Obj {
        // SAFETY: just ffi
        // EXCEPTION: raises if allocation fails
        catch_exception!(unsafe { ffi::mp_obj_new_int_from_ll } => { value })
            .expect("Failed to create i64 object")
    }

    fn new_u64(value: u64) -> Obj {
        // SAFETY: just ffi
        // EXCEPTION: raises if allocation fails
        catch_exception!(unsafe { ffi::mp_obj_new_int_from_ull } => { value })
            .expect("Failed to create u64 object")
    }

    #[test]
    fn test_u32() {
        unsafe { crate::testutil::mpy_init() };
        let zero: Obj = new_u64(0);
        assert_eq!(TryInto::<u32>::try_into(zero).unwrap(), 0u32);

        let max: Obj = new_u64(u32::MAX as u64);
        assert_eq!(TryInto::<u32>::try_into(max).unwrap(), u32::MAX);
    }

    #[test]
    fn test_u64() {
        unsafe { crate::testutil::mpy_init() };
        let zero: Obj = new_u64(0);
        assert_eq!(TryInto::<u64>::try_into(zero).unwrap(), 0u64);

        let max: Obj = new_u64(u64::MAX);
        assert_eq!(TryInto::<u64>::try_into(max).unwrap(), u64::MAX);
    }

    #[test]
    fn test_i32() {
        unsafe { crate::testutil::mpy_init() };
        let zero: Obj = new_i64(0);
        assert_eq!(TryInto::<i32>::try_into(zero).unwrap(), 0i32);

        let max: Obj = new_i64(i32::MAX as i64);
        assert_eq!(TryInto::<i32>::try_into(max).unwrap(), i32::MAX);

        let min: Obj = new_i64(i32::MIN as i64);
        assert_eq!(TryInto::<i32>::try_into(min).unwrap(), i32::MIN);
    }

    #[test]
    fn test_i64() {
        unsafe { crate::testutil::mpy_init() };
        let zero: Obj = new_i64(0);
        assert_eq!(TryInto::<i64>::try_into(zero).unwrap(), 0i64);

        let max: Obj = new_i64(i64::MAX);
        assert_eq!(TryInto::<i64>::try_into(max).unwrap(), i64::MAX);

        let min: Obj = new_i64(i64::MIN);
        assert_eq!(TryInto::<i64>::try_into(min).unwrap(), i64::MIN);
    }

    #[test]
    fn test_u32_overflow() {
        unsafe { crate::testutil::mpy_init() };

        let big = (u32::MAX as i64) + 1;
        let bigobj = new_i64(big);
        std::assert_matches!(TryInto::<u32>::try_into(bigobj), Err(Error::OutOfRange));
    }
}
