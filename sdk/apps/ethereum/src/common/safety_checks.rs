use crate::proto::common::SafetyCheckLevel;

/// Returns the effective safety check level.
pub fn read_setting() -> Result<SafetyCheckLevel> {
    // Check temporary cache first
    // if let Some(cached) = cache_get(APP_COMMON_SAFETY_CHECKS_TEMPORARY) {
    //     if let Some(&byte) = cached.first() {
    //         return SafetyCheckLevel::from_u8(byte);
    //     }
    // }

    // // Fall back to stored setting
    // let stored = storage_device_safety_check_level()?;
    // match stored {
    //     SAFETY_CHECK_LEVEL_STRICT => Ok(SafetyCheckLevel::Strict),
    //     SAFETY_CHECK_LEVEL_PROMPT => Ok(SafetyCheckLevel::PromptAlways),
    //     _ => Err(trezor_app_sdk::Error::InvalidArgument),
    // }
    Ok(SafetyCheckLevel::Strict)
}

/// Changes the safety level settings.
/// TODO not sure if this function should available to ethereum app
pub fn apply_setting(level: SafetyCheckLevel) -> Result<()> {
    // match level {
    //     SafetyCheckLevel::Strict => {
    //         cache_delete(APP_COMMON_SAFETY_CHECKS_TEMPORARY);
    //         storage_device_set_safety_check_level(SAFETY_CHECK_LEVEL_STRICT)?;
    //     }
    //     SafetyCheckLevel::PromptAlways => {
    //         cache_delete(APP_COMMON_SAFETY_CHECKS_TEMPORARY);
    //         storage_device_set_safety_check_level(SAFETY_CHECK_LEVEL_PROMPT)?;
    //     }
    //     SafetyCheckLevel::PromptTemporarily => {
    //         storage_device_set_safety_check_level(SAFETY_CHECK_LEVEL_STRICT)?;
    //         cache_set(APP_COMMON_SAFETY_CHECKS_TEMPORARY, &[level as u8]);
    //     }
    // }
    Ok(())
}

/// Shorthand for checking whether the effective level is Strict.
pub fn is_strict() -> bool {
    read_setting()
        .map(|level| level == SafetyCheckLevel::Strict)
        .unwrap_or(true)
}
