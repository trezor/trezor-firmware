use super::gc::Gc;
use super::runtime::catch_exception;
use super::{ffi, Error, Obj};

pub type Tuple = ffi::mp_obj_tuple_t;

impl Tuple {
    pub const fn empty() -> Gc<Self> {
        unsafe { Gc::from_raw(&ffi::mp_const_empty_tuple_obj as *const _ as *mut _) }
    }

    pub fn alloc(values: &[Obj]) -> Result<Gc<Self>, Error> {
        if values.is_empty() {
            return Ok(Self::empty());
        }

        // TODO: after the gc alloc refactor lands, we can allocate a tuple directly
        // without involving a exception-raising call
        // // construct a memory layout, simulating mp_obj_malloc_var
        // let base_layout = Layout::new::<Tuple>();
        // let items_layout = unwrap!(Layout::array::<Obj>(values.len()));
        // let (layout, offset) = unwrap!(base_layout.extend(items_layout));
        // // check that we're extending what we expect
        // assert!(offset == core::mem::offset_of!(Tuple, items));

        // SAFETY: Although `values` are copied into the new tuple and not mutated,
        // `mp_obj_new_tuple` is taking them through a mut pointer.
        // EXCEPTION: Will raise if allocation fails.
        catch_exception(|| unsafe {
            let tuple = ffi::mp_obj_new_tuple(values.len(), values.as_ptr() as *mut Obj);
            Gc::from_raw(tuple.as_ptr().cast())
        })
    }

    pub fn as_slice(&self) -> &[Obj] {
        // SAFETY:
        // - micropython promises that items have the right len
        // - items are part of the same allocation so the lifetime bound is correct
        unsafe { self.items.as_slice(self.len) }
    }

    pub fn as_mut_slice(&mut self) -> &mut [Obj] {
        // SAFETY:
        // - micropython promises that items have the right len
        // - items are part of the same allocation so the lifetime bound is correct
        unsafe { self.items.as_mut_slice(self.len) }
    }
}

impl From<Gc<Tuple>> for Obj {
    fn from(value: Gc<Tuple>) -> Self {
        // SAFETY:
        //  - `value` is an object struct with a base and a type.
        //  - `value` is GC-allocated.
        unsafe { Obj::from_ptr(Gc::into_raw(value).cast()) }
    }
}
impl TryFrom<Obj> for Gc<Tuple> {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        if unsafe { &ffi::mp_type_tuple }.is_type_of(obj) {
            // SAFETY: We assume that if `value` is an object pointer with the correct type,
            // it is managed by MicroPython GC (see `Gc::from_raw` for details).
            let this = unsafe { Gc::from_raw(obj.as_ptr().cast()) };
            Ok(this)
        } else {
            return Err(Error::TypeError);
        }
    }
}

macro_rules! impl_try_from_tuple {
    () => {};
    ($t:ident $v:ident $($tt:ident $vv:ident)*) => {
        impl<$t, $($tt),*> TryFrom<($t, $($tt),*)> for Obj
        where
            Obj: TryFrom<$t>,
            Error: From<<Obj as TryFrom<$t>>::Error>,
            $(Obj: TryFrom<$tt>,)*
            $(Error: From<<Obj as TryFrom<$tt>>::Error>,)*
        {
            type Error = Error;

            fn try_from(($v, $($vv),*): ($t, $($tt),*)) -> Result<Self, Self::Error> {
                let values = [
                    $v.try_into()?,
                    $($vv.try_into()?),*
                ];
                Ok(Tuple::alloc(&values)?.into())
            }
        }

        impl_try_from_tuple!($($tt $vv)*);
    }
}

impl_try_from_tuple!(T t U u V v W w X x Y y Z z);

#[cfg(test)]
mod tests {
    use super::*;
    use crate::micropython::buffer::StrBuffer;
    use crate::micropython::testutil::mpy_init;

    #[test]
    fn test_try_from_tuple() {
        unsafe { mpy_init() };

        let tuple = (true, 100, "hello");
        let obj: Obj = tuple.try_into().unwrap();
        let decoded = Gc::<Tuple>::try_from(obj).unwrap();
        let slice = decoded.as_slice();
        assert_eq!(bool::try_from(slice[0]).unwrap(), true);
        assert_eq!(i32::try_from(slice[1]).unwrap(), 100);
        let string = StrBuffer::try_from(slice[2]).unwrap();
        assert_eq!(string.as_ref(), "hello");
    }
}
