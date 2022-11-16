//! Tiny module for wrapping Rust structs into Python objects
//!
//! # Example:
//! ```
//! impl Wrappable for Foo {
//!     fn obj_type() -> &'static Type { ... }
//! }
//!
//! fn bar(obj: Obj) -> Obj {
//!     let foo: Gc<Wrapped<Foo>> = obj.try_into()?;
//!     let foo: Foo = foo.deref().inner();
//!     let result: Foo = baz(foo);
//!     result.wrap()
//! }
//! ```

use crate::{
    error::Error,
    micropython::{
        gc::Gc,
        obj::{Obj, ObjBase},
        typ::Type,
    },
};

pub trait Wrappable: Sized {
    fn obj_type() -> &'static Type;

    fn alloc(inner: Self) -> Result<Gc<Wrapped<Self>>, Error> {
        Gc::new(Wrapped {
            base: Self::obj_type().as_base(),
            inner,
        })
    }

    fn wrap(self) -> Result<Obj, Error> {
        let value: Gc<Wrapped<Self>> = Self::alloc(self)?;
        // SAFETY:
        //  - `value` is GC-allocated.
        //  - `value` is `repr(C)`.
        //  - `value` has a `base` as the first field with the correct type.
        let obj = unsafe { Obj::from_ptr(Gc::into_raw(value).cast()) };
        Ok(obj)
    }
}

#[repr(C)]
pub struct Wrapped<T: Wrappable> {
    base: ObjBase,
    inner: T,
}

impl<T: Wrappable> Wrapped<T> {
    pub fn inner(&self) -> &T {
        &self.inner
    }

    pub fn inner_mut(&mut self) -> &mut T {
        &mut self.inner
    }
}

impl<T: Wrappable> TryFrom<Obj> for Gc<Wrapped<T>> {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Gc<Wrapped<T>>, Error> {
        if T::obj_type().is_type_of(obj) {
            // SAFETY: We assume that if `obj` is an object pointer with the correct type,
            // it is always GC-allocated.
            let this = unsafe { Gc::from_raw(obj.as_ptr().cast()) };
            Ok(this)
        } else {
            Err(Error::TypeError)
        }
    }
}
