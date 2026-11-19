//! Checks that the device on the debug probe is the model being flashed.
//!
//! The debug probe's target config only tells MCU families apart (F4 vs U5),
//! but several models share one family. Before writing, a short read-only
//! session reads two things from the device:
//!
//! * the MCU's `DEV_ID`, which tells the U5 variants apart, and
//! * the board capabilities the boardloader stores at `BOARDCAPS_START`, which
//!   name the model the boardloader was built for.
//!
//! A mismatch in either refuses the operation, and so do missing or unreadable
//! board capabilities: models sharing an MCU do not all keep them at the same
//! address, so finding none at the model's own address does not rule out
//! another model's boardloader. A blank device, or a boardloader too old to
//! have them, needs `--skip-device-check`.

use std::fs;

use anyhow::{Context, Result, anyhow, ensure};

use crate::args::Model;
use crate::{helpers, openocd};

/// Header of the board capabilities block.
const CAPABILITIES_HEADER: &[u8] = b"TRZC";
/// Tag that ends the board capabilities.
const TAG_TERMINATOR: u8 = 0x00;
/// Tag of the four-character model name, e.g. `T3W1`.
const TAG_MODEL_NAME: u8 = 0x02;

/// Fails unless the connected device is a `model` device, as far as it can
/// be told -- see the module documentation.
pub fn check(model: Model, skip: bool) -> Result<()> {
    if skip {
        println!("Skipping the check of the connected device");
        return Ok(());
    }

    println!("Checking the connected device");
    let mcu = check_mcu(model)?;
    let board = check_board(model)?;

    println!("Connected device: {mcu} with a {board} boardloader");
    Ok(())
}

/// Reads the device's `DEV_ID` and fails unless it is the one of `model`'s
/// MCU. Returns the MCU's name.
fn check_mcu(model: Model) -> Result<String> {
    let config = model.config()?;
    let (idcode_address, expected_dev_id) = config.mcu_dev_id()?;

    let idcode = openocd::read_memory(model, idcode_address, 4)
        .context("Failed to read the MCU's IDCODE")?;
    let found = dev_id(&idcode)?;

    ensure!(
        found == expected_dev_id,
        "the connected MCU reports DEV_ID 0x{found:03X}, but {} has an {} \
         (DEV_ID 0x{expected_dev_id:03X}) -- is another model connected? \
         Pass --skip-device-check to proceed anyway",
        model.model_id(),
        config.mcu
    );
    Ok(config.mcu)
}

/// Reads the device's board capabilities and fails unless they name `model`.
/// Returns the board name.
fn check_board(model: Model) -> Result<String> {
    let memory_ld = model.model_memory_ld()?;
    let content = fs::read_to_string(&memory_ld)
        .with_context(|| format!("Failed to read `{}`", memory_ld.display()))?;
    let caps_start = helpers::read_symbol_from_content(&content, "BOARDCAPS_START")?;
    let caps_size = helpers::read_symbol_from_content(&content, "BOARDCAPS_MAXSIZE")?;

    let caps = openocd::read_memory(model, caps_start, caps_size).with_context(|| {
        format!(
            "Failed to read the board capabilities at 0x{caps_start:08X}, so the model \
             cannot be confirmed. Pass --skip-device-check to proceed anyway"
        )
    })?;
    let board = board_name(&caps).with_context(|| {
        format!(
            "no board capabilities at 0x{caps_start:08X} (blank flash, an old boardloader, \
             or another model's boardloader), so the model cannot be confirmed. \
             Pass --skip-device-check to proceed anyway"
        )
    })?;

    ensure!(
        board == model.model_id(),
        "the connected device has a {board} boardloader, not a {} one -- is \
         another model connected? Pass --skip-device-check to proceed anyway",
        model.model_id()
    );
    Ok(board)
}

/// The `DEV_ID` field of a `DBGMCU_IDCODE` read.
fn dev_id(idcode: &[u8]) -> Result<u16> {
    let idcode: [u8; 4] = idcode
        .try_into()
        .map_err(|_| anyhow!("the IDCODE read is not four bytes"))?;
    Ok((u32::from_le_bytes(idcode) & 0xFFF) as u16)
}

/// The model name in board capabilities, if they are present and have one.
///
/// Walks the tag-length-value list the same way the firmware does: a header,
/// then `tag, length, data` until a terminator or the end of the area.
fn board_name(caps: &[u8]) -> Option<String> {
    let mut rest = caps.strip_prefix(CAPABILITIES_HEADER)?;
    while let [tag, length, data @ ..] = rest {
        let value = data.get(..*length as usize)?;
        match *tag {
            TAG_TERMINATOR => return None,
            TAG_MODEL_NAME if value.len() == 4 => {
                return Some(String::from_utf8_lossy(value).into_owned());
            }
            _ => {}
        }
        rest = &data[value.len()..];
    }
    None
}

#[cfg(test)]
mod tests {
    use super::{board_name, dev_id};

    /// Board capabilities as the boardloader lays them out, for `model`.
    fn caps(model: &str) -> Vec<u8> {
        let mut caps = b"TRZC".to_vec();
        caps.extend([0x02, 4]);
        caps.extend(model.as_bytes());
        caps.extend([0x03, 4, 2, 1, 0, 0]);
        caps.extend([0x00, 0]);
        caps.resize(0x100, 0xFF);
        caps
    }

    #[test]
    fn reads_the_model_name() {
        assert_eq!(board_name(&caps("T3W1")).as_deref(), Some("T3W1"));
    }

    #[test]
    fn finds_the_model_name_after_other_tags() {
        let mut caps = b"TRZC".to_vec();
        caps.extend([0x03, 4, 2, 1, 0, 0, 0x01, 0]);
        caps.extend([0x02, 4]);
        caps.extend(b"T2B1");
        caps.extend([0x00, 0]);

        assert_eq!(board_name(&caps).as_deref(), Some("T2B1"));
    }

    #[test]
    fn erased_flash_has_no_model_name() {
        assert_eq!(board_name(&[0xFF; 0x100]), None);
    }

    #[test]
    fn stops_at_the_terminator() {
        let mut caps = b"TRZC".to_vec();
        caps.extend([0x00, 0, 0x02, 4]);
        caps.extend(b"T3W1");

        assert_eq!(board_name(&caps), None);
    }

    #[test]
    fn rejects_a_field_running_past_the_area() {
        let mut caps = b"TRZC".to_vec();
        caps.extend([0x02, 4]);
        caps.extend(b"T3");

        assert_eq!(board_name(&caps), None);
    }

    #[test]
    fn takes_the_dev_id_from_the_idcode() {
        // DBGMCU_IDCODE 0x10016476, little-endian: REV_ID 0x1001, DEV_ID 0x476.
        assert_eq!(dev_id(&[0x76, 0x64, 0x01, 0x10]).unwrap(), 0x476);
    }

    #[test]
    fn requires_a_four_byte_idcode() {
        assert!(dev_id(&[0x76, 0x64]).is_err());
    }
}
