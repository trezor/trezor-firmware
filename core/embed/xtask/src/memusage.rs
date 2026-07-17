use std::fs;
use std::ops::Range;
use std::path::Path;

use anyhow::{Context, Result, bail};

#[derive(Debug, Clone)]
struct MemoryRegion {
    name: String,
    origin: u64,
    length: u64,
}

#[derive(Debug, Clone)]
struct OutputSection {
    name: String,
    address: u64,
    size: u64,
    load_address: Option<u64>,
}

/// Returns true for zero-initialized / reserved sections (`.bss`, `.stack`,
/// `.heap`). These are NOBITS: they occupy RAM but carry no bytes in the flash
/// image. GNU ld nonetheless reports a `load address` for them (the LMA cursor
/// continues past the preceding `AT>FLASH` `.data` section), which must NOT be
/// counted as flash usage — otherwise a large reserved stack inflates the
/// reported figure well beyond the real image size.
fn is_nobits_section(name: &str) -> bool {
    const NOBITS: [&str; 3] = [".bss", ".stack", ".heap"];
    NOBITS
        .iter()
        .any(|prefix| name == *prefix || name.starts_with(&format!("{prefix}.")))
}

/// Prints a table of memory usage by region, based on the contents of
/// the given map file.
pub fn print_memusage(mapfile: &Path) -> Result<()> {
    let content = fs::read_to_string(mapfile)
        .with_context(|| format!("Failed to read `{}`", mapfile.display()))?;

    let regions = parse_memory_regions(&content)?;
    let sections = parse_output_sections(&content)?;

    // Some images (e.g. the boot_ucb bootloader) are zero-padded to fill their
    // whole flash region. The linker exports `__flash_padding_size` so we can
    // report real content usage instead of a misleading 100%.
    let flash_padding = parse_symbol_value(&content, "__flash_padding_size");

    println!(
        "xtask: Memory usage from `{}`",
        mapfile
            .file_name()
            .map(|name| name.to_string_lossy())
            .unwrap_or_else(|| mapfile.as_os_str().to_string_lossy())
    );
    println!(
        "{:<16} {:>12} {:>12} {:>8}",
        "Region", "Used", "Total", "Usage"
    );

    for region in regions {
        let mut used = used_bytes_for_region(&region, &sections);

        // Exclude the fixed-size image padding from the reported usage so the
        // figure reflects real content. The padding only applies to the FLASH
        // region the image is linked into.
        let mut note = String::new();
        if region.name == "FLASH"
            && let Some(padding) = flash_padding
        {
            used = used.saturating_sub(padding);
            note = format!("  (+{} padding)", format_bytes(padding));
        }

        let percent = if region.length == 0 {
            0.0
        } else {
            (used as f64 / region.length as f64) * 100.0
        };

        println!(
            "{:<16} {:>12} {:>12} {:>7.2}%{}",
            region.name,
            format_bytes(used),
            format_bytes(region.length),
            percent,
            note
        );
    }

    Ok(())
}

/// Parses the value of a symbol assignment from the map file, i.e. a line of
/// the form `0x<value>  <name> = ...`.
fn parse_symbol_value(content: &str, name: &str) -> Option<u64> {
    for line in content.lines() {
        let mut parts = line.split_whitespace();
        let (Some(value), Some(symbol)) = (parts.next(), parts.next()) else {
            continue;
        };
        if symbol == name && parts.next() == Some("=") {
            return parse_hex(value).ok();
        }
    }
    None
}

/// Parses the memory regions from the "Memory Configuration" part of
/// the map file.
fn parse_memory_regions(content: &str) -> Result<Vec<MemoryRegion>> {
    let mut lines = content.lines();

    // We expect the memory configuration to look like this:

    // Memory Configuration
    //
    // Name             Origin             Length             Attributes
    // FLASH            0x0c004000         0x00018000         xr
    // BOARDCAPS        0x0c01bf00         0x00000100         rw
    // MAIN_RAM         0x300c0000         0x00010000         rw
    // AUX1_RAM         0x30190000         0x000e0000         rw
    // BOOT_ARGS        0x30000000         0x00000200         rw
    // FB1_RAM          0x30000200         0x000bfe00         rw
    // FB2_RAM          0x300d0000         0x000c0000         rw
    // *default*        0x00000000         0xffffffff

    // Skip lines until we find the "Memory Configuration" header
    for line in lines.by_ref() {
        if line.trim() == "Memory Configuration" {
            break;
        }
    }

    // The first non-empty line after the header should be the column headers,
    // which we can skip.
    let header = lines
        .by_ref()
        .find(|line| !line.trim().is_empty())
        .ok_or_else(|| anyhow::anyhow!("Map file is missing memory configuration header"))?;

    // We expect the header to contain at least "Origin" and "Length" columns.
    if !header.contains("Origin") || !header.contains("Length") {
        bail!("Map file has an unexpected memory configuration header");
    }

    let mut regions = Vec::new();

    for line in lines {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            break;
        }

        let mut parts = trimmed.split_whitespace();
        let Some(name) = parts.next() else {
            continue;
        };

        if name == "*default*" {
            continue;
        }

        let Some(origin) = parts.next() else {
            continue;
        };
        let Some(length) = parts.next() else {
            continue;
        };

        regions.push(MemoryRegion {
            name: name.to_string(),
            origin: parse_hex(origin)?,
            length: parse_hex(length)?,
        });
    }

    if regions.is_empty() {
        bail!("Map file does not define any concrete memory regions");
    }

    regions.sort_by_key(|region| region.origin);
    Ok(regions)
}

/// Parses the output sections from the "Linker script and memory map" part
/// of the map file.
fn parse_output_sections(content: &str) -> Result<Vec<OutputSection>> {
    let mut in_map = false;
    let mut sections = Vec::new();

    // We expect the linker map to look like this:

    // Linker script and memory map
    //.text           0x08000000       0x100
    //.rodata         0x08000100        0x80
    //.data           0x20000000        0x20 load address 0x08000180
    //.bss            0x20000020        0x40

    // This section contains a lot of other information,
    // but we only care about lines that start with '.'

    for line in content.lines() {
        let trimmed = line.trim_start();

        if !in_map {
            if trimmed == "Linker script and memory map" {
                in_map = true;
            }
            continue;
        }

        if !line.starts_with('.') {
            continue;
        }

        let mut parts = line.split_whitespace();
        let Some(name) = parts.next() else {
            continue;
        };
        let Some(address) = parts.next() else {
            continue;
        };
        let Some(size) = parts.next() else {
            continue;
        };

        let address = parse_hex(address)?;
        let size = parse_hex(size)?;
        if size == 0 {
            continue;
        }

        let mut load_address = None;
        let remaining: Vec<_> = parts.collect();
        for window in remaining.windows(3) {
            if window[0] == "load" && window[1] == "address" {
                load_address = Some(parse_hex(window[2])?);
                break;
            }
        }

        sections.push(OutputSection {
            name: name.to_string(),
            address,
            size,
            load_address,
        });
    }

    Ok(sections)
}

/// Calculates the total number of bytes used in `region` by the sections in
/// `sections`, counting both runtime and load addresses.
fn used_bytes_for_region(region: &MemoryRegion, sections: &[OutputSection]) -> u64 {
    let mut ranges = Vec::new();
    let region_end = region.origin.saturating_add(region.length);

    for section in sections {
        if let Some(range) =
            intersect_range(section.address, section.size, region.origin, region_end)
        {
            ranges.push(range);
        }

        // A NOBITS section (.bss/.stack/.heap) carries no bytes in the flash
        // image; its reported load address is a phantom from the LMA cursor and
        // must not be counted as flash usage.
        if let Some(load_address) = section.load_address
            && load_address != section.address
            && !is_nobits_section(&section.name)
            && let Some(range) =
                intersect_range(load_address, section.size, region.origin, region_end)
        {
            ranges.push(range);
        }
    }

    merged_len(ranges)
}

/// Returns the intersection of the range defined by `start` and `size` with
fn intersect_range(
    start: u64,
    size: u64,
    region_start: u64,
    region_end: u64,
) -> Option<Range<u64>> {
    let end = start.checked_add(size)?;
    let clipped_start = start.max(region_start);
    let clipped_end = end.min(region_end);
    (clipped_start < clipped_end).then_some(clipped_start..clipped_end)
}

/// Merges overlapping and adjacent ranges and returns the total length
/// covered by the merged ranges.
fn merged_len(mut ranges: Vec<Range<u64>>) -> u64 {
    if ranges.is_empty() {
        return 0;
    }

    ranges.sort_by_key(|range| range.start);

    let mut merged: Vec<Range<u64>> = Vec::with_capacity(ranges.len());
    for range in ranges {
        match merged.last_mut() {
            Some(last) if range.start <= last.end => {
                last.end = last.end.max(range.end);
            }
            _ => merged.push(range),
        }
    }

    merged
        .into_iter()
        .map(|range| range.end - range.start)
        .sum()
}

/// Parses a hex string which may optionally start with "0x" or "0X".
fn parse_hex(value: &str) -> Result<u64> {
    let trimmed = value.trim();
    let digits = trimmed
        .strip_prefix("0x")
        .or_else(|| trimmed.strip_prefix("0X"))
        .unwrap_or(trimmed);

    u64::from_str_radix(digits, 16)
        .with_context(|| format!("Failed to parse hex value `{trimmed}`"))
}

/// Formats a byte value as a human-readable string, using KB if the
/// value is 1024 or more.
fn format_bytes(value: u64) -> String {
    if value >= 1024 {
        format!("{:.1} KB", value as f64 / 1024.0)
    } else {
        format!("{value} B")
    }
}

#[cfg(test)]
mod tests {
    use super::{
        parse_memory_regions, parse_output_sections, parse_symbol_value, used_bytes_for_region,
    };

    #[test]
    fn counts_runtime_and_load_addresses() {
        let map = r#"
Memory Configuration

Name             Origin             Length             Attributes
FLASH            0x08000000         0x00010000         xr
RAM              0x20000000         0x00002000         rw
*default*        0x00000000         0xffffffff

Linker script and memory map

.text           0x08000000       0x100
.rodata         0x08000100        0x80
.data           0x20000000        0x20 load address 0x08000180
.bss            0x20000020        0x40
"#;

        let regions = parse_memory_regions(map).expect("memory regions should parse");
        let sections = parse_output_sections(map).expect("sections should parse");

        let flash = regions
            .iter()
            .find(|region| region.name == "FLASH")
            .unwrap();
        let ram = regions.iter().find(|region| region.name == "RAM").unwrap();

        assert_eq!(used_bytes_for_region(flash, &sections), 0x1a0);
        assert_eq!(used_bytes_for_region(ram, &sections), 0x60);
    }

    #[test]
    fn parses_padding_symbol_value() {
        // Symbol assignment lines look like this in the map file.
        let map = r#"
Linker script and memory map

                0x000018e4                        __flash_padding_size = (_bootloader_code_end - __flash_padding_start)
                0x0c03c000                        _bootloader_code_end = .
"#;

        assert_eq!(
            parse_symbol_value(map, "__flash_padding_size"),
            Some(0x18e4)
        );
        assert_eq!(
            parse_symbol_value(map, "_bootloader_code_end"),
            Some(0x0c03c000)
        );
        // A symbol that is not present yields None (no padding to subtract).
        assert_eq!(parse_symbol_value(map, "__missing_symbol"), None);
    }

    #[test]
    fn ignores_nobits_load_addresses() {
        // `.bss` and `.stack` are NOBITS: they live in RAM but the linker
        // reports a flash `load address` for them. That phantom LMA (here a
        // huge 64 KB stack) must not be counted as flash usage.
        let map = r#"
Memory Configuration

Name             Origin             Length             Attributes
FLASH            0x08000000         0x00010000         xr
RAM              0x20000000         0x00020000         rw
*default*        0x00000000         0xffffffff

Linker script and memory map

.flash          0x08000000       0x100
.data           0x20000000        0x20 load address 0x08000100
.bss            0x20000020        0x40 load address 0x08000120
.stack          0x20000060     0x10000 load address 0x08000120
"#;

        let regions = parse_memory_regions(map).expect("memory regions should parse");
        let sections = parse_output_sections(map).expect("sections should parse");

        let flash = regions.iter().find(|r| r.name == "FLASH").unwrap();
        let ram = regions.iter().find(|r| r.name == "RAM").unwrap();

        // Flash: .flash (0x100) + .data load image (0x20); the .bss/.stack
        // phantom LMAs are excluded.
        assert_eq!(used_bytes_for_region(flash, &sections), 0x120);
        // RAM: .data + .bss + .stack VMAs are all counted as usual.
        assert_eq!(used_bytes_for_region(ram, &sections), 0x10060);
    }

    #[test]
    fn padding_symbol_does_not_confuse_section_parsing() {
        // A symbol line (leading whitespace, no leading '.') must not be picked
        // up as an output section.
        let map = r#"
Linker script and memory map

.flash          0x0c016000     0x1f5d0
                0x000018e4                        __flash_padding_size = 0x18e4
"#;

        let sections = parse_output_sections(map).expect("sections should parse");
        assert_eq!(sections.len(), 1);
        assert_eq!(sections[0].address, 0x0c016000);
    }
}
