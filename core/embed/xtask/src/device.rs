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
//! A mismatch in either refuses the operation. Missing board capabilities
//! (blank flash, or a boardloader too old to have them) only confirm the MCU,
//! and a warning says so.

use std::fs;

use anyhow::{Context, Result, anyhow, bail};

use crate::args::Model;
use crate::{helpers, openocd};

/// Header of the board capabilities block.
const CAPABILITIES_HEADER: &[u8] = b"TRZC";
/// Tag that ends the board capabilities.
const TAG_TERMINATOR: u8 = 0x00;
/// Tag of the four-character model name, e.g. `T3W1`.
const TAG_MODEL_NAME: u8 = 0x02;

/// What the probe read from the device.
#[derive(Debug)]
struct Probe {
    /// Value of `DBGMCU_IDCODE`.
    idcode: u32,
    /// Contents of the board capabilities area, or why they could not be read.
    boardcaps: Result<Vec<u8>, String>,
}

/// Fails unless the connected device is a `model` device, as far as it can
/// be told -- see the module documentation.
pub fn check(model: Model, skip: bool) -> Result<()> {
    if skip {
        println!("Skipping the check of the connected device");
        return Ok(());
    }

    let config = model.config()?;
    let (idcode_address, dev_id) = config.mcu_dev_id()?;

    let memory_ld = model.model_memory_ld()?;
    let content = fs::read_to_string(&memory_ld)
        .with_context(|| format!("Failed to read `{}`", memory_ld.display()))?;
    let caps_start = helpers::read_symbol_from_content(&content, "BOARDCAPS_START")?;
    let caps_size = helpers::read_symbol_from_content(&content, "BOARDCAPS_MAXSIZE")?;

    println!("Checking the connected device");
    let reads = openocd::read_memory(model, &[(idcode_address, 4), (caps_start, caps_size)])?;
    let probe = Probe::from_reads(reads)?;

    let board = verify(model.model_id(), &config.mcu, dev_id, &probe)?;
    match board {
        Some(board) => println!(
            "Connected device: {} with a {board} boardloader",
            config.mcu
        ),
        None => println!(
            "Warning: no board capabilities at 0x{caps_start:08X} (blank flash or an old \
             boardloader), so only the MCU ({}) is confirmed, not the model",
            config.mcu
        ),
    }
    Ok(())
}

impl Probe {
    /// Builds the probe from the results of the `DBGMCU_IDCODE` and board
    /// capabilities reads, in that order.
    fn from_reads(reads: Vec<Result<Vec<u8>, String>>) -> Result<Self> {
        let [idcode, boardcaps]: [_; 2] = reads
            .try_into()
            .map_err(|_| anyhow!("expected two memory reads"))?;

        let idcode = idcode.map_err(|e| anyhow!("Failed to read the MCU's IDCODE: {e}"))?;
        let idcode = u32::from_le_bytes(
            idcode
                .try_into()
                .map_err(|_| anyhow!("the IDCODE read is not four bytes"))?,
        );

        Ok(Self { idcode, boardcaps })
    }
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

/// Checks the probe against `model`. Returns the board name if the board
/// capabilities confirm the model, or `None` if only the MCU could be checked.
fn verify(model: &str, mcu: &str, dev_id: u16, probe: &Probe) -> Result<Option<String>> {
    let found = (probe.idcode & 0xFFF) as u16;
    if found != dev_id {
        bail!(
            "the connected MCU reports DEV_ID 0x{found:03X}, but {model} has an {mcu} \
             (DEV_ID 0x{dev_id:03X}) -- is another model connected? \
             Pass --skip-device-check to proceed anyway"
        );
    }

    let Some(board) = probe.boardcaps.as_deref().ok().and_then(board_name) else {
        return Ok(None);
    };
    if board != model {
        bail!(
            "the connected device has a {board} boardloader, not a {model} one -- is \
             another model connected? Pass --skip-device-check to proceed anyway"
        );
    }
    Ok(Some(board))
}

#[cfg(test)]
mod tests {
    use super::{Probe, board_name, verify};

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

    fn probe(idcode: u32, boardcaps: Result<Vec<u8>, String>) -> Probe {
        Probe { idcode, boardcaps }
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
    fn builds_the_probe_from_reads() {
        let probe = Probe::from_reads(vec![Ok(vec![0x76, 0x64, 0x01, 0x10]), Ok(b"TRZC".to_vec())])
            .unwrap();

        assert_eq!(probe.idcode, 0x1001_6476);
        assert_eq!(probe.boardcaps.unwrap(), b"TRZC");
    }

    #[test]
    fn keeps_a_failed_capabilities_read() {
        let probe = Probe::from_reads(vec![Ok(vec![0x19, 0x64, 0x03, 0x20]), Err("failed".into())])
            .unwrap();

        assert_eq!(probe.boardcaps.unwrap_err(), "failed");
    }

    #[test]
    fn requires_the_idcode() {
        assert!(Probe::from_reads(vec![Err("failed".into()), Ok(vec![])]).is_err());
    }

    #[test]
    fn accepts_the_matching_device() {
        let probe = probe(0x1001_6476, Ok(caps("T3W1")));

        assert_eq!(
            verify("T3W1", "stm32u5g", 0x476, &probe)
                .unwrap()
                .as_deref(),
            Some("T3W1")
        );
    }

    #[test]
    fn rejects_another_mcu() {
        // A T3T1 (STM32U585) connected while flashing for a T3W1.
        let probe = probe(0x2000_6482, Ok(caps("T3T1")));
        let error = verify("T3W1", "stm32u5g", 0x476, &probe).unwrap_err();

        assert!(error.to_string().contains("DEV_ID 0x482"));
    }

    #[test]
    fn rejects_another_model_on_the_same_mcu() {
        // T2T1 and T2B1 share the STM32F427; only the boardloader tells them apart.
        let probe = probe(0x2003_6419, Ok(caps("T2T1")));
        let error = verify("T2B1", "stm32f427", 0x419, &probe).unwrap_err();

        assert!(error.to_string().contains("T2T1 boardloader"));
    }

    #[test]
    fn confirms_only_the_mcu_without_capabilities() {
        let blank = probe(0x2003_6419, Ok(vec![0xFF; 0x100]));
        let unreadable = probe(0x2003_6419, Err("failed".into()));

        assert_eq!(verify("T2B1", "stm32f427", 0x419, &blank).unwrap(), None);
        assert_eq!(
            verify("T2B1", "stm32f427", 0x419, &unreadable).unwrap(),
            None
        );
    }
}
