use crate::{error::Error, trezorhal::translations};

use super::blob::Translations;

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
    let result = unsafe { translations::write(data, offset) };
    if result {
        Ok(())
    } else {
        Err(value_error!("Failed to write translations blob"))
    }
}

/// Load translations from flash, validate, and cache references to lookup
/// tables.
unsafe fn try_init<'a>() -> Result<Option<Translations<'a>>, Error> {
    // load from flash
    let flash_data = unsafe { translations::get_blob() };
    // check if flash is empty
    // TODO perhaps we should check the full area?
    if flash_data[0..16] == [super::blob::EMPTY_BYTE; 16] {
        return Ok(None);
    }
    // try to parse the data
    Translations::new(flash_data).map(Some)
}

pub fn init() {
    // unsafe block because every individual operation here is unsafe
    unsafe {
        // SAFETY: it is OK to look
        if TRANSLATIONS_ON_FLASH.is_some() {
            return;
        }
        // SAFETY: try_init unconditionally loads the translations from flash.
        // No other reference exists (TRANSLATIONS_ON_FLASH is None) so this is safe.
        match try_init() {
            // SAFETY: We are in a single-threaded environment so setting is OK.
            // (note that from this point on a reference to flash data is held)
            Ok(Some(t)) => TRANSLATIONS_ON_FLASH = Some(t),
            Ok(None) => {}
            // SAFETY: No reference to flash data exists so it is OK to erase it.
            Err(_) => translations::erase(),
        }
    }
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
