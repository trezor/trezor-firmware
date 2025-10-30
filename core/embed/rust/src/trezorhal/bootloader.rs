use super::ffi;

use num_traits::FromPrimitive;

#[derive(PartialEq, Debug, Eq, Clone, Copy, FromPrimitive, ToPrimitive)]
pub enum BootloaderWFResult {
    ErrorFatal = ffi::workflow_result_t_WF_ERROR_FATAL as _,
    Error = ffi::workflow_result_t_WF_ERROR as _,
    Ok = ffi::workflow_result_t_WF_OK as _,
    OkRebootSelected = ffi::workflow_result_t_WF_OK_REBOOT_SELECTED as _,
    OkFirmwareInstalled = ffi::workflow_result_t_WF_OK_FIRMWARE_INSTALLED as _,
    OkDeviceWiped = ffi::workflow_result_t_WF_OK_DEVICE_WIPED as _,
    OkBootloaderUnlocked = ffi::workflow_result_t_WF_OK_BOOTLOADER_UNLOCKED as _,
    OkUiAction = ffi::workflow_result_t_WF_OK_UI_ACTION as _,
    OkPairingCompleted = ffi::workflow_result_t_WF_OK_PAIRING_COMPLETED as _,
    OkPairingFailed = ffi::workflow_result_t_WF_OK_PAIRING_FAILED as _,
    Cancelled = ffi::workflow_result_t_WF_CANCELLED as _,
}

pub fn bootloader_process_usb() -> BootloaderWFResult {
    unsafe {
        BootloaderWFResult::from_u32(ffi::bootloader_process_usb())
            .unwrap_or(BootloaderWFResult::Error)
    }
}

#[cfg(feature = "ble")]
pub fn bootloader_process_ble() -> BootloaderWFResult {
    unsafe {
        BootloaderWFResult::from_u32(ffi::bootloader_process_ble())
            .unwrap_or(BootloaderWFResult::Error)
    }
}

pub fn debuglink_process() {
    unsafe { ffi::debuglink_process() }
}

pub fn debuglink_notify_layout_change() {
    unsafe { ffi::debuglink_notify_layout_change() }
}
