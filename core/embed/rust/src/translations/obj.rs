use crate::{
    error::Error,
    io::InputStream,
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
    trezorhal::translations,
};

use super::translated_string::TranslatedString;

impl TryFrom<TranslatedString> for StrBuffer {
    type Error = Error;

    fn try_from(value: TranslatedString) -> Result<Self, Self::Error> {
        // SAFETY: The translated string is copied into a new memory. Reference to flash
        // data is discarded at the end of this function.
        let translated = value.translate(unsafe { super::flash::get() });
        StrBuffer::alloc(translated)
        // TODO fall back to English (which is static and can be converted
        // infallibly) if the allocation fails?
    }
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
    data_len: Obj,
    data_hash: Obj,
    total_len: Obj,
}

// SAFETY: We are in a single-threaded environment.
unsafe impl Sync for TranslationsHeader {}

impl TranslationsHeader {
    pub(super) fn new(header: &super::blob::TranslationsHeader<'_>) -> Result<Self, Error> {
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
            data_len: header.data_len.try_into()?,
            data_hash: header.data_hash.as_ref().try_into()?,
            total_len: header.total_len.try_into()?,
        })
    }

    pub fn getattr(&self, attr: Qstr) -> Result<Obj, Error> {
        let obj = match attr {
            Qstr::MP_QSTR_language => self.language,
            Qstr::MP_QSTR_version => self.version,
            Qstr::MP_QSTR_change_language_title => self.change_language_title,
            Qstr::MP_QSTR_change_language_prompt => self.change_language_prompt,
            Qstr::MP_QSTR_data_len => self.data_len,
            Qstr::MP_QSTR_data_hash => self.data_hash,
            Qstr::MP_QSTR_total_len => self.total_len,
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
            let (header, _) =
                super::blob::TranslationsHeader::parse_from(&mut InputStream::new(buffer))?;
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

extern "C" fn area_bytesize() -> Obj {
    let bytesize = translations::area_bytesize();
    unsafe { util::try_or_raise(|| bytesize.try_into()) }
}

extern "C" fn get_language() -> Obj {
    let block = || {
        // SAFETY: reference is discarded at the end of the block
        let lang_name = unsafe { super::flash::get() }.map(|t| t.header.language);
        lang_name.unwrap_or(super::DEFAULT_LANGUAGE).try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn init() -> Obj {
    let block = || {
        super::flash::init();
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn deinit() -> Obj {
    // SAFETY: Safe by itself. Any unsafety stems from some other piece of code
    // not upholding the safety parameters.
    unsafe { super::flash::deinit() };
    Obj::const_none()
}

extern "C" fn erase() -> Obj {
    let block = || {
        super::flash::erase()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn write(data: Obj, offset: Obj) -> Obj {
    let block = || {
        // SAFETY: reference is discarded at the end of the block
        let data = unsafe { get_buffer(data)? };
        let offset: usize = offset.try_into()?;
        super::flash::write(data, offset)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn verify(data: Obj) -> Obj {
    let block = || {
        // SAFETY: reference is discarded at the end of the block
        let data = unsafe { get_buffer(data)? };
        super::blob::Translations::new(data)?;
        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezortranslate: Module = obj_module! {
    /// from trezortranslate_keys import TR as TR  # noqa: F401
    /// """Translation object with attributes."""
    Qstr::MP_QSTR_TR => TR_OBJ.as_obj(),

    /// MAX_HEADER_LEN: int
    /// """Maximum length of the translations header."""
    Qstr::MP_QSTR_MAX_HEADER_LEN => Obj::small_int(super::MAX_HEADER_LEN),

    /// def area_bytesize() -> int:
    ///     """Maximum size of the translation blob that can be stored."""
    Qstr::MP_QSTR_area_bytesize => obj_fn_0!(area_bytesize).as_obj(),

    /// def get_language() -> str:
    ///     """Get the current language."""
    Qstr::MP_QSTR_get_language => obj_fn_0!(get_language).as_obj(),

    /// def init() -> None:
    ///     """Initialize the translations system.
    ///
    ///     Loads and verifies translation data from flash. If the verification passes,
    ///     Trezor UI is translated from that point forward.
    ///     """
    Qstr::MP_QSTR_init => obj_fn_0!(init).as_obj(),

    /// def deinit() -> None:
    ///     """Deinitialize the translations system.
    ///
    ///     Translations must be deinitialized before erasing or writing to flash.
    ///     """
    Qstr::MP_QSTR_deinit => obj_fn_0!(deinit).as_obj(),

    /// def erase() -> None:
    ///     """Erase the translations blob from flash."""
    Qstr::MP_QSTR_erase => obj_fn_0!(erase).as_obj(),

    /// def write(data: bytes, offset: int) -> None:
    ///     """Write data to the translations blob in flash."""
    Qstr::MP_QSTR_write => obj_fn_2!(write).as_obj(),

    /// def verify(data: bytes) -> None:
    ///     """Verify the translations blob."""
    Qstr::MP_QSTR_verify => obj_fn_1!(verify).as_obj(),

    /// class TranslationsHeader:
    ///     """Metadata about the translations blob."""
    /// 
    ///     language: str
    ///     version: tuple[int, int, int, int]
    ///     change_language_title: str
    ///     change_language_prompt: str
    ///     data_len: int
    ///     data_hash: bytes
    ///     total_len: int
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
};
