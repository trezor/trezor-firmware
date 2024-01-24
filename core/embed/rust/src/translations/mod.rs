mod blob;
mod flash;
mod generated;
#[cfg(feature = "micropython")]
mod obj;
mod public_keys;
mod translated_string;

pub use blob::MAX_HEADER_LEN;
pub use translated_string::TranslatedString as TR;
pub const DEFAULT_LANGUAGE: &str = "enUS";

#[no_mangle]
pub unsafe extern "C" fn get_utf8_glyph(codepoint: cty::uint16_t, font: cty::c_int) -> *const u8 {
    // C will send a negative number
    let font_abs = font.unsigned_abs() as u16;

    // SAFETY:
    // We rely on the fact that the caller (`display_text_render` and friends) uses
    // and discards this data immediately.
    let Some(tr) = (unsafe { flash::get() }) else {
        return core::ptr::null();
    };
    if let Some(glyph) = tr.font(font_abs).and_then(|t| t.get(codepoint)) {
        glyph.as_ptr()
    } else {
        core::ptr::null()
    }
}
