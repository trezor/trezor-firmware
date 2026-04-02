use anyhow::{Context, Result, ensure};
use std::{
    fs,
    {path::Path, process},
};

use crate::args::FlashArgs;
use crate::helpers::artifacts_dir;

/*
flash: flash_boardloader flash_bootloader flash_firmware ## flash everything using OpenOCD

flash_firmware: $(FIRMWARE_BUILD_DIR)/firmware.bin ## flash firmware using OpenOCD
ifeq ($(MCU),$(filter $(MCU),STM32F4))
    $(OPENOCD) -c "init; reset halt; flash write_image erase $<.p1 $(FIRMWARE_START); flash write_image erase $<.p2 $(FIRMWARE_P2_START); exit"

else
    $(OPENOCD) -c "init; reset halt; flash write_image erase $< $(FIRMWARE_START); exit"
endif

flash_combine: $(PRODTEST_BUILD_DIR)/combined.bin ## flash combined using OpenOCD
    $(OPENOCD) -c "init; reset halt; flash write_image erase $< $(BOARDLOADER_START); exit"

flash_erase: ## erase all sectors in flash bank 0
    $(OPENOCD) -c "init; reset halt; flash info 0; flash erase_sector 0 0 last; flash erase_check 0; exit"

flash_erase_bootloader: ## erase bootloader
    $(OPENOCD) -c "init; reset halt; flash info 0; flash erase_sector 0 $(BOOTLOADER_SECTOR_START) $(BOOTLOADER_SECTOR_END); exit"

flash_erase_firmware: ## erase bootloader
ifeq ($(MCU),$(filter $(MCU),STM32F4))
    $(OPENOCD) -c "init; reset halt; flash info 0; flash erase_sector 0 $(FIRMWARE_P1_SECTOR_START) $(FIRMWARE_P1_SECTOR_END);  flash erase_sector 0 $(FIRMWARE_P2_SECTOR_START) $(FIRMWARE_P2_SECTOR_END); exit"

else
    $(OPENOCD) -c "init; reset halt; flash info 0; flash erase_sector 0 $(FIRMWARE_SECTOR_START) $(FIRMWARE_SECTOR_END); exit"
endif

flash_read_storage: ## read storage sectors from flash
    $(OPENOCD) -c "init; reset halt; flash read_bank 0 storage1.data $(STORAGE_1_OFFSET) $(STORAGE_SIZE); flash read_bank 0 storage2.data $(STORAGE_2_OFFSET) $(STORAGE_SIZE); exit"

flash_erase_storage: ## erase storage sectors from flash
    $(OPENOCD) -c "init; reset halt; flash erase_sector 0 $(STORAGE_1_SECTOR_START) $(STORAGE_1_SECTOR_END); flash erase_sector 0 $(STORAGE_2_SECTOR_START) $(STORAGE_2_SECTOR_END); exit"

flash_bootloader_jlink: $(BOOTLOADER_BUILD_DIR)/bootloader.bin ## flash bootloader using JLink
    JLinkExe -nogui 1 -commanderscript embed/projects/bootloader/bootloader_flash.jlink

flash_bootloader_ci_jlink: $(BOOTLOADER_CI_BUILD_DIR)/bootloader.bin ## flash CI bootloader using JLink
    JLinkExe -nogui 1 -commanderscript embed/projects/bootloader_ci/bootloader_flash.jlink

flash_firmware_jlink: $(FIRMWARE_BUILD_DIR)/firmware.bin ## flash firmware using JLink. file names must end in .bin for JLink
    cp -f $<.p1 $<.p1.bin
    cp -f $<.p2 $<.p2.bin
    ## pad 2nd part so that FW integrity works after flash
    ## read&compare in flashing will avoid erasing unmodified sectors
    truncate -s $(FIRMWARE_P2_MAXSIZE) $<.p2.bin
    JLinkExe -nogui 1 -commanderscript embed/projects/firmware/firmware_flash.jlink

## openocd debug commands:

openocd: ## start openocd which connects to the device
    $(OPENOCD)

openocd_reset: ## cause a system reset using OpenOCD
    $(OPENOCD) -c "init; reset; exit"
*/

pub fn flash(args: FlashArgs) -> Result<()> {
    let binary = artifacts_dir(args.model)?.join(format!("{}.bin", args.component.binary_name()));

    let binary = binary
        .canonicalize()
        .with_context(|| format!("Failed to locate `{}` for flashing", binary.display()))?;

    let flash_start = args.component.flash_start_symbol()?;
    let mem_ld = binary.with_extension("mem.ld");

    let address = read_symbol_address(&mem_ld, flash_start).with_context(|| {
        format!(
            "Failed to load `{}` from `{}`",
            flash_start,
            mem_ld.display()
        )
    })?;

    println!(
        "Flashing `{}` to address 0x{:08X}",
        binary.display(),
        address
    );

    let status = process::Command::new("openocd")
        .args(["-f", "interface/stlink.cfg"])
        .args(["-c", "transport select hla_swd"])
        .args(["-f", args.model.openocd_target()])
        .arg("-c")
        .arg(format!(
            "init; reset halt; flash write_image erase {} 0x{:X}; exit",
            binary.display(),
            address
        ))
        .status()
        .context("Failed to spawn `openocd`")?;

    ensure!(status.success(), "`openocd` failed with status: {status}");

    Ok(())
}

/// Reads symbol from memory.ld file and parse it as an address.
fn read_symbol_address(file: &Path, symbol: &str) -> Result<u32> {
    let content =
        fs::read_to_string(file).with_context(|| format!("Failed to read `{}`", file.display()))?;
    let prefix = format!("{symbol} =");

    let value = content
        .lines()
        .map(str::trim)
        .find_map(|line| line.strip_prefix(&prefix))
        .map(|value| value.trim().trim_end_matches(';').trim())
        .with_context(|| format!("Address `{symbol}` not found in `{}`", file.display()))?;

    parse_address(value).with_context(|| {
        format!(
            "Invalid address `{value}` for `{symbol}` in `{}`",
            file.display()
        )
    })
}

/// Parses a string as a u32 address, supporting both decimal and
/// hexadecimal formats.
fn parse_address(value: &str) -> Result<u32> {
    if let Some(hex) = value
        .strip_prefix("0x")
        .or_else(|| value.strip_prefix("0X"))
    {
        Ok(u32::from_str_radix(hex, 16)?)
    } else {
        Ok(value.parse()?)
    }
}
