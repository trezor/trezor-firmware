use core::cell::{Ref, RefCell, RefMut};

use super::gc::Gc;
use super::obj::{Obj, ObjBase};
use super::typ::Type;
use crate::error::Error;

/// Marker trait for Python objects implemented in Rust.
///
/// must have obj
pub trait PyObject {
    fn obj_type() -> &'static Type;
}

/// Marker trait for structs that have their type as the first element.
pub unsafe trait HasBaseType {
    fn obj_type() -> &'static Type;
}

#[repr(C)]
pub struct PythonObject<T> {
    base: ObjBase,
    object: RefCell<T>,
}

unsafe impl<T: PyObject> HasBaseType for PythonObject<T> {
    fn obj_type() -> &'static Type {
        T::obj_type()
    }
}

impl<T: PyObject> PythonObject<T> {
    pub fn new(object: T) -> Self {
        let base = T::obj_type().as_base();
        Self {
            base,
            object: RefCell::new(object),
        }
    }
}

impl<T: PyObject> From<T> for PythonObject<T> {
    fn from(object: T) -> Self {
        Self::new(object)
    }
}

pub struct GcObject<T>(Gc<PythonObject<T>>);

impl<T: PyObject> GcObject<T> {
    pub fn new(object: T) -> Result<Self, Error> {
        Ok(GcObject(Gc::new(PythonObject::new(object))?))
    }

    pub fn new_with_finalizer(object: T) -> Result<Self, Error> {
        let py_obj = PythonObject::new(object);
        let gc = Gc::new_with_custom_finaliser(py_obj)?;
        Ok(GcObject(gc))
    }

    pub fn borrow(&self) -> Ref<'_, T> {
        self.0.object.borrow()
    }

    pub fn borrow_mut(&self) -> RefMut<'_, T> {
        self.0.object.borrow_mut()
    }
}

impl<T: HasBaseType> TryFrom<Obj> for Gc<T> {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        if T::obj_type().is_type_of(obj) {
            // SAFETY:
            // - given `is_type_of` matches, we expect that `obj` is a pointer to the
            //   expected type (i.e., manual RTTI is correct)
            // - we assume that an `Obj` of the right type is in fact GC-managed.
            let this = unsafe { Gc::from_raw(obj.as_ptr().cast()) };
            Ok(this)
        } else {
            Err(Error::TypeError)
        }
    }
}

impl<T: HasBaseType> From<Gc<T>> for Obj {
    fn from(value: Gc<T>) -> Self {
        // SAFETY:
        // - `value` is GC-allocated.
        // - `value` implements HasBaseType, denoting that it is repr(C) with a base
        //   type as the first field.
        unsafe { Self::from_ptr(Gc::into_raw(value).cast()) }
    }
}

impl<T: PyObject> TryFrom<Obj> for GcObject<T> {
    type Error = Error;

    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let py_obj = Gc::<PythonObject<T>>::try_from(obj)?;
        Ok(GcObject(py_obj))
    }
}

impl<T: PyObject> From<GcObject<T>> for Obj {
    fn from(value: GcObject<T>) -> Self {
        value.0.into()
    }
}
