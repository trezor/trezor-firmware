use core::cell::{Ref, RefCell, RefMut};

use super::{
    gc::Gc,
    obj::{Obj, ObjBase},
    typ::Type,
    Error,
};

/// MicroPython class implemented in Rust.
///
/// Required for using `PyObject` / `GcObject` handles to GC-managed objects.
/// See [`GcObject`] for more details.
pub trait PyClass {
    /// The MicroPython type object for this class.
    fn obj_type() -> &'static Type;
}

/// Marker trait for structs that have their type as the first element.
///
/// Identifies types whose in-memory representation has a base type as the first
/// element, so it is legible to MicroPython and convertible to/from `Obj`.
///
/// Necessarily has `obj_type()` because that is the base type. We additionally
/// require that the type is `'static`, even though theoretically someone could
/// want to create a type at runtime.
///
/// # Safety
///
/// Callers must ensure that `Self` is `#[repr(C)]` with an [`ObjBase`] as
/// its first field, so that MicroPython can treat pointers to `Self` as
/// valid `Obj` values.
pub unsafe trait HasObjBase {
    /// The MicroPython type object for this struct.
    fn obj_type() -> &'static Type;
}

/// Wrapper for GC-heap based Rust objects.
///
/// Represents a Rust object, backed by a [`PyClass`] class implementation.
/// Because handing over a Rust object to MicroPython loses all borrow
/// information, the struct always wraps the object in a `RefCell` for run-time
/// borrow checking.
///
/// Internal helper, not exposed for public use. Library users should either:
///
/// * if the Rust value is stack-bound, use it directly, or
/// * if the value is heap-bound, use a [`GcObject`] instead, which provides
///   allocation and conversion services.
#[repr(C)]
struct PyObject<T> {
    base: ObjBase,
    object: RefCell<T>,
}

// SAFETY:
// `PyObject` has an `ObjBase` as the first field
unsafe impl<T: PyClass> HasObjBase for PyObject<T> {
    fn obj_type() -> &'static Type {
        T::obj_type()
    }
}

impl<T: PyClass> PyObject<T> {
    /// Create a new `PyObject` from a Rust object.
    pub fn new(object: T) -> Self {
        let base = T::obj_type().as_base();
        Self {
            base,
            object: RefCell::new(object),
        }
    }
}

/// GC-managed Rust object, backed by a [`PyClass`] class implementation.
///
/// Represents a Rust object, backed by a [`PyClass`] class implementation,
/// living on the GC heap.
///
/// Because placing a Rust object on the GC managed heap loses all borrow
/// information, `GcObject` provides run-time borrow checking.
///
/// You also have the option of using a finalizer via `new_with_finalizer`. Note
/// that this is **distinct from `Drop`**: Rust finalizer will not get called
/// automatically, but you can configure a custom finalizer through your
/// `PyClass`.
#[repr(transparent)]
pub struct GcObject<T>(Gc<PyObject<T>>);

impl<T: PyClass> GcObject<T> {
    /// Allocate a new object on the MicroPython GC heap.
    pub fn new(object: T) -> Result<Self, Error> {
        Ok(GcObject(Gc::new(PyObject::new(object))?))
    }

    /// Allocate a new object and register it for finalisation.
    ///
    /// If the type exposes a `__del__` method, MicroPython will call it when
    /// the object is collected. The Rust `Drop` implementation is **not**
    /// invoked automatically; use `__del__` for custom teardown if needed.
    pub fn new_with_finalizer(object: T) -> Result<Self, Error> {
        let py_obj = PyObject::new(object);
        let gc = Gc::new_with_custom_finaliser(py_obj)?;
        Ok(GcObject(gc))
    }

    fn as_inner_ref(&self) -> &PyObject<T> {
        // SAFETY: we only ever take immutable references, and nobody else
        // (in particular micropython) has the knowledge to mutate the object
        unsafe { Gc::as_ref(&self.0) }
    }

    /// Immutably borrow the inner Rust object.
    ///
    /// Panics if the object is already mutably borrowed.
    pub fn borrow(&self) -> Ref<'_, T> {
        self.as_inner_ref().object.borrow()
    }

    /// Mutably borrow the inner Rust object.
    ///
    /// Panics if the object is already borrowed.
    pub fn borrow_mut(&self) -> RefMut<'_, T> {
        self.as_inner_ref().object.borrow_mut()
    }
}

impl<T: HasObjBase> TryFrom<Obj> for Gc<T> {
    type Error = Error;

    /// Recover a GC pointer from an `Obj`, checking the runtime type.
    ///
    /// Returns [`Error::TypeError`] if `obj` is not an instance of `T`'s type.
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

impl<T: HasObjBase> From<Gc<T>> for Obj {
    /// Convert a GC pointer back into an `Obj` for passing to MicroPython.
    fn from(value: Gc<T>) -> Self {
        // SAFETY:
        // - `value` is GC-allocated.
        // - `value` implements HasBaseType, denoting that it is repr(C) with a base
        //   type as the first field.
        unsafe { Self::from_ptr(Gc::into_raw(value).cast()) }
    }
}

impl<T: PyClass> TryFrom<Obj> for GcObject<T> {
    type Error = Error;

    /// Recover a [`GcObject`] from an `Obj`, checking the runtime type.
    ///
    /// Returns [`Error::TypeError`] if `obj` is not an instance of `T`'s type.
    fn try_from(obj: Obj) -> Result<Self, Self::Error> {
        let py_obj = Gc::<PyObject<T>>::try_from(obj)?;
        Ok(GcObject(py_obj))
    }
}

impl<T: PyClass> From<GcObject<T>> for Obj {
    /// Convert a [`GcObject`] into an `Obj` for passing to MicroPython.
    fn from(value: GcObject<T>) -> Self {
        value.0.into()
    }
}
