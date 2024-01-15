use crate::{
    error::Error,
    micropython::{
        buffer::{get_buffer, StrBuffer},
        ffi,
        gc::Gc,
        map::Map,
        module::Module,
        obj::{Obj, ObjBase},
        qstr::Qstr,
        typ::Type,
        util,
    },
};

use super::translated_string::TranslatedString;

pub fn tr(item: TranslatedString) -> StrBuffer {
    // SAFETY: 
    let stored_translations = item.translate(unsafe { super::flash::get() });
    StrBuffer::alloc(stored_translations)
}

#[repr(C)]
pub struct TrObj {
    base: ObjBase,
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for TrObj {}

fn translate(translation: TranslatedString) -> Result<Obj, Error> {
    // SAFETY: TryFrom<&str> for Obj allocates a copy of the passed in string.
    // The reference to flash data is discarded at the end of this function.
    let stored_translations = unsafe { super::flash::get() };
    translation.translate(stored_translations).try_into()
}

impl TrObj {
    const fn obj_type() -> &'static Type {
        static TR_TYPE: Type = obj_type! {
            name: Qstr::MP_QSTR_TR,
            attr_fn: TrObj::attr_fn,
        };
        &TR_TYPE
    }

    pub const fn singleton() -> &'static Self {
        static TR_OBJ: TrObj = TrObj {
            base: TrObj::obj_type().as_base(),
        };
        &TR_OBJ
    }

    fn getattr(&self, attr: Qstr) -> Result<Obj, Error> {
        if let Some(translation) = TranslatedString::from_qstr(attr) {
            Ok(translate(translation)?)
        } else {
            Err(Error::AttributeError(attr))
        }
    }

    /// Convert TrObj to a MicroPython object
    pub const fn as_obj(&'static self) -> Obj {
        // SAFETY:
        //  - We are an object struct with a base and a type.
        //  - 'static lifetime holds us in place.
        //  - There's nothing to mutate.
        unsafe { Obj::from_ptr(self as *const _ as *mut _) }
    }
}

// MicroPython interface
// SAFETY: Caller is supposed to be MicroPython, or copy MicroPython contracts
// about the meaning of arguments.
impl TrObj {
    unsafe extern "C" fn attr_fn(_self_in: Obj, attr: ffi::qstr, dest: *mut Obj) {
        let block = || {
            let arg = unsafe { dest.read() };
            if !arg.is_null() {
                // Null destination would mean a `setattr`.
                return Err(Error::TypeError);
            }
            let attr = Qstr::from_u16(attr as u16);
            unsafe { dest.write(TrObj::singleton().getattr(attr)?) };
            Ok(())
        };
        unsafe { util::try_or_raise(block) }
    }
}

#[derive(Copy, Clone)]
enum HeaderSource {
    Flash,
    Gc(Obj),
}

impl HeaderSource {
    pub fn from_gc(obj: Obj) -> Result<Self, Error> {
        if !obj.is_bytes() {
            return Err(Error::TypeError);
        }
        Ok(Self::Gc(obj))
    }

    // SAFETY: This is a convenience wrapper around TranslationsHeader::from_flash()
    // and get_buffer() on the GC object. Safety parameters of those apply here,
    // namely, we only guarantee validity of the returned data for a short
    // timeframe (more precisely, until either MicroPython is allowed to touch
    // the Gc variant, or until flash contents are updated with a new
    // translations blob). In the Gc case, we also do not guarantee
    // immutability. The caller should discard the result immediately after use.
    pub unsafe fn header<'a>(self) -> Result<super::TranslationsHeader<'a>, Error> {
        match self {
            HeaderSource::Flash => unsafe { super::flash::get() }
                .map(|blob| Ok(blob.header))
                .unwrap_or(Err(value_error!("Translations blob not set"))),
            HeaderSource::Gc(obj) => {
                // get_buffer will succeed because we only accept bytes-like objects when
                // constructing
                super::TranslationsHeader::parse(unwrap!(unsafe { get_buffer(obj) }))
            }
        }
    }
}

#[repr(C)]
pub struct TranslationsHeader {
    base: ObjBase,
    source: HeaderSource,
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for TranslationsHeader {}

impl TranslationsHeader {
    const fn obj_type() -> &'static Type {
        static TYPE: Type = obj_type! {
            name: Qstr::MP_QSTR_TranslationHeader,
            make_new_fn: TranslationsHeader::make_new,
            attr_fn: TranslationsHeader::attr_fn,
        };
        &TYPE
    }

    fn from_gc(obj: Obj) -> Result<Self, Error> {
        Ok(Self {
            base: Self::obj_type().as_base(),
            source: HeaderSource::from_gc(obj)?,
        })
    }

    const fn from_flash() -> &'static Self {
        static OBJ: TranslationsHeader = TranslationsHeader {
            base: TranslationsHeader::obj_type().as_base(),
            source: HeaderSource::Flash,
        };
        &OBJ
    }

    pub const extern "C" fn obj_from_flash(_cls_in: Obj) -> Obj {
        // SAFETY:
        //  - Self::from_flash returns a reference to an object in ROM which can't be
        //    mutated.
        //  - That object is a struct with a base and a type.
        unsafe { Obj::from_ptr(Self::from_flash() as *const _ as *mut _) }
    }

    pub fn getattr(&self, attr: Qstr) -> Result<Obj, Error> {
        // SAFETY: All data from the header is copied before returning.
        let header = unsafe { self.source.header()? };
        match attr {
            Qstr::MP_QSTR_load_from_flash => Ok(obj_fn_1!(Self::obj_from_flash).as_obj()),
            Qstr::MP_QSTR_language_name => header.language.try_into(),
            Qstr::MP_QSTR_data_length => Ok(header.data_length.into()),
            Qstr::MP_QSTR_change_language_title => header.change_language_title.try_into(),
            Qstr::MP_QSTR_change_language_prompt => header.change_language_prompt.try_into(),
            Qstr::MP_QSTR_version => {
                let version = [header.version];
                todo!()
            }
            _ => Err(Error::AttributeError(attr)),
        }
    }
}

// MicroPython interface
// SAFETY: Caller is supposed to be MicroPython, or uphold MicroPython contracts
// about the meaning of arguments.
impl TranslationsHeader {
    pub unsafe extern "C" fn make_new(
        typ: *const Type,
        n_args: usize,
        n_kw: usize,
        args: *const Obj,
    ) -> Obj {
        if n_args != 1 || n_kw != 0 || typ != Self::obj_type() {
            return Error::TypeError.into_obj();
        }

        let block = |args: &[Obj], kwargs: &Map| {
            assert!(args.len() == 1);
            Gc::new(Self::from_gc(args[0])?).map(Into::into)
        };
        unsafe { util::try_with_args_and_kwargs_inline(n_args, n_kw, args, block) }
    }

    pub unsafe extern "C" fn attr_fn(_self_in: Obj, attr: ffi::qstr, dest: *mut Obj) {
        let block = || {
            let arg = unsafe { dest.read() };
            if !arg.is_null() {
                // Null destination would mean a `setattr`.
                return Err(Error::TypeError);
            }

            let this = Gc::<Self>::try_from(_self_in)?;
            let attr = Qstr::from_u16(attr as u16);
            unsafe { dest.write(this.getattr(attr)?) };
            Ok(())
        };
        unsafe { util::try_or_raise(block) }
    }
}

impl From<Gc<TranslationsHeader>> for Obj {
    fn from(value: Gc<TranslationsHeader>) -> Self {
        // SAFETY:
        //  - `value` is an object struct with a base and a type.
        //  - `value` is GC-allocated.
        unsafe { Obj::from_ptr(Gc::into_raw(value).cast()) }
    }
}

impl TryFrom<Obj> for Gc<TranslationsHeader> {
    type Error = Error;

    fn try_from(value: Obj) -> Result<Self, Self::Error> {
        if TranslationsHeader::obj_type().is_type_of(value) {
            // SAFETY: We assume that if `value` is an object pointer with the correct type,
            // it is managed by MicroPython GC (see `Gc::from_raw` for details).
            let this = unsafe { Gc::from_raw(value.as_ptr().cast()) };
            Ok(this)
        } else {
            Err(Error::TypeError)
        }
    }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezortranslate: Module = obj_module! {
    // TODO: add function to get all the translations keys in order
    // - so that client can validate it is sending correct keys in correct order

    /// class TranslationsHeader:
    ///     """Metadata about the translations blob."""
    /// 
    ///     language_name: str
    ///     version: tuple[int, int, int, int]
    ///     change_language_title: str
    ///     change_language_prompt: str
    ///     header_length: int
    ///     data_length: int
    /// 
    ///     def __init__(self, header_bytes: bytes) -> None:
    ///         """Parse header from bytes.
    ///         The header has variable length.
    ///         """
    ///
    ///     @staticmethod
    ///     def load_from_flash() -> TranslationsHeader | None:
    ///         """Load translations from flash."""
    Qstr::MP_QSTR_TranslationsHeader => TranslationsHeader::obj_type().as_obj(),

    /// from trezortranslate_keys import TR  # noqa: F401
    /// """Translation object with attributes."""
    Qstr::MP_QSTR_TR => TrObj::singleton().as_obj(),
};
