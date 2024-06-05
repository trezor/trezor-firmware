use spin::{RwLock, RwLockReadGuard};

use crate::{
    error::{value_error, Error},
    trezorhal::translations,
};

use super::blob::Translations;

static TRANSLATIONS_ON_FLASH: RwLock<Option<Translations>> = RwLock::new(None);

/// Erase translations blob from flash.
///
/// The blob must be deinitialized via `deinit()` before calling this function.
pub fn erase() -> Result<(), Error> {
    // Write-lock is not necessary but it hints that nobody should call `erase()`
    // while others are looking.
    let blob = unwrap!(TRANSLATIONS_ON_FLASH.try_write());
    {
        if blob.is_some() {
            return Err(value_error!(c"Translations blob already set"));
        }

        // SAFETY: The blob is not set, so there are no references to it.
        unsafe { translations::erase() };
    }
    Ok(())
}

/// Write translations blob to flash.
///
/// The blob must be deinitialized via `deinit()` before calling this function.
pub fn write(data: &[u8], offset: usize) -> Result<(), Error> {
    // Write-lock is not necessary but it hints that nobody should call `erase()`
    // while others are looking.
    let blob = unwrap!(TRANSLATIONS_ON_FLASH.try_write());
    let result = {
        if blob.is_some() {
            return Err(value_error!(c"Translations blob already set"));
        }

        // SAFETY: The blob is not set, so there are no references to it.
        unsafe { translations::write(data, offset) }
    };
    if result {
        Ok(())
    } else {
        Err(value_error!(c"Failed to write translations blob"))
    }
}

/// Load translations from flash, validate, and cache references to lookup
/// tables.
///
/// # Safety
/// Result depends on flash contents, see `translations::get_blob()`.
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

/// Initialize translations subsystem with current data from flash
///
/// Will erase any data from the translations section if the blob is invalid. At
/// end, either the blob is available via `get()`, or there is a None value.
///
/// Does nothing if the data is already loaded. Call `deinit()` first to force
/// reload.
pub fn init() {
    let blob = unwrap!(TRANSLATIONS_ON_FLASH.try_upgradeable_read());
    if blob.is_some() {
        return;
    }

    let mut blob = blob.upgrade();
    // SAFETY: try_init unconditionally loads the translations from flash.
    // No other reference exists (TRANSLATIONS_ON_FLASH is None) so this is safe.
    match unsafe { try_init() } {
        Ok(Some(t)) => *blob = Some(t),
        Ok(None) => {}
        // SAFETY: No reference to flash data exists so it is OK to erase it.
        Err(_) => unsafe { translations::erase() },
    }
}

/// Deinitialize translations subsystem.
///
/// If the blob is locked by a reader, `deinit()` will return an error.
pub fn deinit() -> Result<(), Error> {
    let Some(mut blob) = TRANSLATIONS_ON_FLASH.try_write() else {
        return Err(value_error!(c"Translations are in use."));
    };
    *blob = None;
    Ok(())
}

/// Get a reference to the translations blob.
///
/// # Safety
///
/// This function relies on `Translations` to Do The Right Thing™ by only
/// returning references whose lifetime is tied to the lifetime _of the
/// reference_, as opposed to the underlying data.
///
/// Due to us placing the `Translations` blob in a `static` variable, the
/// lifetime of its data must be `'static`. The true lifetime, however, is
/// "between init() and deinit()".
///
/// So instead we tie all references to the lifetime of the returned
/// `RwLockReadGuard`, through making sure that `Translations` only ever returns
/// references that live as long as the reference giving them out.
pub fn get() -> Result<RwLockReadGuard<'static, Option<Translations<'static>>>, Error> {
    TRANSLATIONS_ON_FLASH
        .try_read()
        .ok_or(value_error!(c"Translations are in use."))
}
