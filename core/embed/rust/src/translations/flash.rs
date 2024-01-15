use crate::{error::Error, trezorhal::translations};

use super::Translations;

static mut TRANSLATIONS_ON_FLASH: Option<Translations> = None;

pub fn erase() -> Result<(), Error> {
    // SAFETY: Looking is safe (in a single threaded environment).
    if unsafe { TRANSLATIONS_ON_FLASH.is_some() } {
        return Err(value_error!("Translations blob already set"));
    }

    // SAFETY: The blob is not set, so there are no references to it.
    unsafe { translations::erase() };
    Ok(())
}

pub fn write(data: &[u8], offset: usize) -> Result<(), Error> {
    // SAFETY: Looking is safe (in a single threaded environment).
    if unsafe { TRANSLATIONS_ON_FLASH.is_some() } {
        return Err(value_error!("Translations blob already set"));
    }

    // SAFETY: The blob is not set, so there are no references to it.
    unsafe { translations::write(data, offset) };
    Ok(())
}

/// Load translations from flash, validate, and cache references to lookup
/// tables.
pub fn init() -> Result<(), Error> {
    if unsafe { TRANSLATIONS_ON_FLASH.is_some() } {
        return Ok(());
    }
    let flash_data = unsafe { translations::get_blob() };
    todo!();
    let blob = Translations::new(flash_data);
    // SAFETY: TODO
    unsafe { TRANSLATIONS_ON_FLASH = blob.ok() };
    Ok(())
}

// SAFETY: Invalidates all references coming from the flash-based blob.
// In other words, none should exist when this function is called.
pub unsafe fn deinit() {
    // SAFETY: Given the above, we can safely clear the cached object.
    unsafe { TRANSLATIONS_ON_FLASH = None };
}

// SAFETY: Gives out a reference to a TranslationsBlob which can be invalidated
// by calling `erase()`. The caller must not store this reference, nor any that
// come from it, beyond the lifetime of the current function.
pub unsafe fn get<'a>() -> Option<&'a Translations<'a>> {
    // SAFETY: We are in a single-threaded environment.
    unsafe { TRANSLATIONS_ON_FLASH.as_ref() }
}
