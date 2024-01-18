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
    // SAFETY: The translated string is copied into a new memory. Reference to flash
    // data is discarded at the end of this function.
    let translated = item.translate(unsafe { super::flash::get() });
    StrBuffer::alloc(translated).unwrap_or_else(|_| item.untranslated().into())
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
            unsafe { dest.write(TR_OBJ.getattr(attr)?) };
            Ok(())
        };
        unsafe { util::try_or_raise(block) }
    }
}

static TR_OBJ_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_TR,
    attr_fn: TrObj::attr_fn,
};

static TR_OBJ: TrObj = TrObj {
    base: TR_OBJ_TYPE.as_base(),
};

#[repr(C)]
pub struct TranslationsHeader {
    base: ObjBase,

    language: Obj,
    version: Obj,
    change_language_title: Obj,
    change_language_prompt: Obj,
    header_length: Obj,
    data_length: Obj,
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for TranslationsHeader {}

impl TranslationsHeader {
    pub(super) fn new(header: &super::TranslationsHeader<'_>) -> Result<Self, Error> {
        let version_objs: [Obj; 4] = {
            let v = header.version;
            [v[0].into(), v[1].into(), v[2].into(), v[3].into()]
        };
        Ok(Self {
            base: TRANSLATIONS_HEADER_TYPE.as_base(),
            language: header.language.try_into()?,
            version: util::new_tuple(&version_objs)?,
            change_language_title: header.change_language_title.try_into()?,
            change_language_prompt: header.change_language_prompt.try_into()?,
            header_length: header.header_length.into(),
            data_length: header.data_length.into(),
        })
    }

    pub fn getattr(&self, attr: Qstr) -> Result<Obj, Error> {
        let obj = match attr {
            Qstr::MP_QSTR_language_name => self.language,
            Qstr::MP_QSTR_version => self.version,
            Qstr::MP_QSTR_change_language_title => self.change_language_title,
            Qstr::MP_QSTR_change_language_prompt => self.change_language_prompt,
            Qstr::MP_QSTR_header_length => self.header_length,
            Qstr::MP_QSTR_data_length => self.data_length,
            Qstr::MP_QSTR_load_from_flash => LOAD_FROM_FLASH_FN.as_obj(),
            _ => return Err(Error::AttributeError(attr)),
        };
        Ok(obj)
    }
}

// MicroPython interface
// SAFETY: Caller is supposed to be MicroPython, or uphold MicroPython contracts
// about the meaning of arguments.
impl TranslationsHeader {
    pub unsafe extern "C" fn make_new(
        _typ: *const Type,
        n_args: usize,
        n_kw: usize,
        args: *const Obj,
    ) -> Obj {
        let block = |args: &[Obj], kwargs: &Map| {
            if args.len() != 1 || !kwargs.is_empty() {
                return Err(Error::TypeError);
            }
            // SAFETY: reference is discarded at the end of this function.
            let buffer = unsafe { get_buffer(args[0])? };
            let header = super::TranslationsHeader::parse(buffer)?;
            let new = Self::new(&header)?;
            Ok(Gc::new(new)?.into())
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

    pub extern "C" fn load_from_flash(_cls_in: Obj) -> Obj {
        let block = || {
            // SAFETY: reference is discarded at the end of this function.
            match unsafe { super::flash::get() } {
                Some(translations) => {
                    let new = Self::new(&translations.header)?;
                    Ok(Gc::new(new)?.into())
                }
                None => Ok(Obj::const_none()),
            }
        };
        unsafe { util::try_or_raise(block) }
    }
}

static TRANSLATIONS_HEADER_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_TranslationsHeader,
    make_new_fn: TranslationsHeader::make_new,
    attr_fn: TranslationsHeader::attr_fn,
};

static LOAD_FROM_FLASH_FN: ffi::mp_obj_fun_builtin_fixed_t =
    obj_fn_1!(TranslationsHeader::load_from_flash);

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
        if TRANSLATIONS_HEADER_TYPE.is_type_of(value) {
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
    Qstr::MP_QSTR_TranslationsHeader => TRANSLATIONS_HEADER_TYPE.as_obj(),

    /// from trezortranslate_keys import TR  # noqa: F401
    /// """Translation object with attributes."""
    Qstr::MP_QSTR_TR => TR_OBJ.as_obj(),
};
