mod blob;
mod flash;
mod generated;
#[cfg(feature = "micropython")]
mod obj;
mod public_keys;
mod translated_string;

pub use translated_string::TranslatedString as TR;
pub const DEFAULT_LANGUAGE: &str = "en-US";

/// # Safety
///
/// Returned pointer will only point to valid font data for as long as
/// the flash content is not invalidated by `erase()` or `write()`.
#[no_mangle]
pub unsafe extern "C" fn get_utf8_glyph(codepoint: cty::uint16_t, font: cty::c_int) -> *const u8 {
    // C will send a negative number
    let font_abs = font.unsigned_abs() as u16;

    // SAFETY: Reference is discarded at the end of the function.
    // We do return a _pointer_ to the same memory location, but the pointer is
    // always valid.
    let Ok(translations) = flash::get() else {
        return core::ptr::null();
    };
    let Some(tr) = translations.as_ref() else {
        return core::ptr::null();
    };
    if let Some(glyph) = tr.font(font_abs).and_then(|t| t.get(codepoint)) {
        glyph.as_ptr()
    } else {
        core::ptr::null()
    }
}
