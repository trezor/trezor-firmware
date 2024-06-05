use crate::{
    error::Error,
    io::InputStream,
    micropython::{
        buffer::{get_buffer, StrBuffer},
        ffi,
        macros::{
            attr_tuple, obj_dict, obj_fn_0, obj_fn_1, obj_fn_2, obj_map, obj_module, obj_type,
        },
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        simple_type::SimpleTypeObj,
        typ::Type,
        util,
    },
    trezorhal::translations,
};

use super::translated_string::TranslatedString;

impl TryFrom<TranslatedString> for StrBuffer {
    type Error = Error;

    fn try_from(value: TranslatedString) -> Result<Self, Self::Error> {
        let blob = super::flash::get()?;
        let translated = value.translate(blob.as_ref());
        StrBuffer::alloc(translated)
        // TODO fall back to English (which is static and can be converted
        // infallibly) if the allocation fails?
    }
}

fn translate(translation: TranslatedString) -> Result<Obj, Error> {
    translation
        .translate(super::flash::get()?.as_ref())
        .try_into()
}

// SAFETY: Caller is supposed to be MicroPython, or copy MicroPython contracts
// about the meaning of arguments.
unsafe extern "C" fn tr_attr_fn(_self_in: Obj, attr: ffi::qstr, dest: *mut Obj) {
    let block = || {
        let arg = unsafe { dest.read() };
        if !arg.is_null() {
            // Null destination would mean a `setattr`.
            return Err(Error::TypeError);
        }
        let attr = Qstr::from_u16(attr as u16);
        let result = if let Some(translation) = TranslatedString::from_qstr(attr) {
            translate(translation)?
        } else {
            return Err(Error::AttributeError(attr));
        };
        unsafe { dest.write(result) };
        Ok(())
    };
    unsafe { util::try_or_raise(block) }
}

static TR_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_TR,
    attr_fn: tr_attr_fn,
};

static TR_OBJ: SimpleTypeObj = SimpleTypeObj::new(&TR_TYPE);

fn make_translations_header(header: &super::blob::TranslationsHeader<'_>) -> Result<Obj, Error> {
    let version_objs: [Obj; 4] = {
        let v = header.version;
        [v[0].into(), v[1].into(), v[2].into(), v[3].into()]
    };
    attr_tuple! {
        Qstr::MP_QSTR_language => header.language.try_into()?,
        Qstr::MP_QSTR_version => util::new_tuple(&version_objs)?,
        Qstr::MP_QSTR_data_len => header.data_len.try_into()?,
        Qstr::MP_QSTR_data_hash => header.data_hash.as_ref().try_into()?,
        Qstr::MP_QSTR_total_len => header.total_len.try_into()?,
    }
}

pub unsafe extern "C" fn translations_header_new(
    _self_in: Obj,
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
        make_translations_header(&header)
    };
    unsafe { util::try_with_args_and_kwargs_inline(n_args, n_kw, args, block) }
}

pub extern "C" fn translations_header_from_flash(_cls_in: Obj) -> Obj {
    let block = || match super::flash::get()?.as_ref() {
        Some(translations) => make_translations_header(translations.header()),
        None => Ok(Obj::const_none()),
    };
    unsafe { util::try_or_raise(block) }
}

static TRANSLATIONS_HEADER_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_TranslationsHeader,
    locals: &obj_dict!(obj_map! {
        Qstr::MP_QSTR_load_from_flash => obj_fn_1!(translations_header_from_flash).as_obj(),
    }),
    call_fn: translations_header_new,
};

static TRANSLATIONS_HEADER_OBJ: SimpleTypeObj = SimpleTypeObj::new(&TRANSLATIONS_HEADER_TYPE);

extern "C" fn area_bytesize() -> Obj {
    let bytesize = translations::area_bytesize();
    unsafe { util::try_or_raise(|| bytesize.try_into()) }
}

extern "C" fn get_language() -> Obj {
    let block = || {
        let blob = super::flash::get()?;
        let lang_name = blob.as_ref().map(|t| t.header().language);
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
    let block = || {
        super::flash::deinit()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
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
    Qstr::MP_QSTR_TranslationsHeader => TRANSLATIONS_HEADER_OBJ.as_obj(),
};
