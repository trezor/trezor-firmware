//! Converts an ARMv8-M ELF executable file into a custom binary format suitable
//! for loading as an Trezor applet.
//!
//! The app binary format consists of a fixed-size header followed by the read-only
//! segment data and a list of relocation addresses. The header contains metadata about
//! the app, such as the virtual address of the entry function, sizes and addresses
//! of the read-only and read-write segments, and stack information.

use anyhow::{Context, Result, bail, ensure};
use object::{
    Object, ObjectSection, ObjectSegment, ObjectSymbol, RelocationFlags, RelocationTarget,
    elf::{
        R_ARM_ABS32, R_ARM_THM_MOVT_ABS, R_ARM_THM_MOVT_PREL, R_ARM_THM_MOVW_ABS_NC,
        R_ARM_THM_MOVW_PREL_NC,
    },
};
use std::{fmt, io::Write, mem::size_of};
use zerocopy::{IntoBytes, LittleEndian, U32};
use zerocopy_derive::{Immutable, IntoBytes};

const MPU_ALIGNMENT: usize = 32;

/// The ARMv8-M app binary header is a fixed-size structure at the beginning
/// of the image payload. All offsets are relative to the end of the header.
#[repr(C)]
#[derive(IntoBytes, Immutable, Debug)]
struct Armv8mBinaryHeader {
    /// Header version.
    version: U32<LittleEndian>,
    /// Offset of the read-only segment
    ro_offset: U32<LittleEndian>,
    /// Virtual address of the ro segment
    ro_va: U32<LittleEndian>,
    /// Size of the ro segment
    ro_size: U32<LittleEndian>,
    /// Offset of the relocation table for the ro segment
    ro_rel_offset: U32<LittleEndian>,
    /// Size of ro segment relocation table
    ro_rel_size: U32<LittleEndian>,
    /// Virtual address of the rw segment
    rw_va: U32<LittleEndian>,
    /// Read-write segment size
    rw_size: U32<LittleEndian>,
    /// Offset of the relocation table for the rw segment
    rw_rel_offset: U32<LittleEndian>,
    /// Size of the rw segment relocation table
    rw_rel_size: U32<LittleEndian>,
    /// Offset of the initialization data for the rw segment
    rw_init_offset: U32<LittleEndian>,
    /// Size of the initialization data for the rw segment
    rw_init_size: U32<LittleEndian>,
    /// Virtual address of the application stack
    stack_va: U32<LittleEndian>,
    /// Application stack size
    stack_size: U32<LittleEndian>,
    /// Application heap size
    heap_size: U32<LittleEndian>,
    /// Virtual address of the applet_main()
    entry_va: U32<LittleEndian>,
    /// Reserved field for runtime purposes (zeroed)
    runtime_flags: U32<LittleEndian>,
}

impl Armv8mBinaryHeader {
    /// Fixed size of the ARM app header in bytes.
    const HEADER_SIZE: usize = 128;

    fn to_padded_bytes(&self) -> [u8; Self::HEADER_SIZE] {
        let mut bytes = [0u8; Self::HEADER_SIZE];
        bytes[..size_of::<Self>()].copy_from_slice(self.as_bytes());
        bytes
    }
}

/// AppBinary represents the structure of the app binary
/// to be generated from the ELF file,
#[derive(Debug)]
pub(crate) struct Armv8mBinary {
    /// Virtual address of the entry function (applet_main)
    entry_va: u32,
    /// Read-only segment containing code and read-only data
    ro_segment: RoSegment,
    /// Read-write segment containing mutable data
    rw_segment: RwSegment,
    /// Stack information
    stack: StackInfo,
}

/// Describes the read-only segment of the app binary
struct RoSegment {
    /// Virtual address of the read-only segment
    va: u32,
    /// Data of the read-only segment
    data: Vec<u8>,
    /// Virtual addresses of the absolute relocations
    relocations: Vec<u8>,
}

impl fmt::Debug for RoSegment {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("RoSegment")
            .field("size", &self.data.len())
            .field("rel_count", &self.relocations.len())
            .finish()
    }
}

/// Describes the read-write segment of the app binary
#[derive(Debug)]
struct RwSegment {
    /// Virtual address of the read-write segment
    va: u32,
    /// Size of the read-write segment
    size: u32,
    /// Initialization data (may be empty or less than size)
    data: Vec<u8>,
    /// Virtual addresses of the absolute relocations
    relocations: Vec<u8>,
}

/// Describes the stack information of the app binary
#[derive(Debug)]
struct StackInfo {
    /// Virtual address of the stack
    va: u32,
    /// Size of the stack
    size: u32,
}

impl Armv8mBinary {
    /// Name of the startup symbol that must be defined in the ELF file.
    const ENTRY_SYMBOL: &str = "applet_main";

    /// Creates an AppBinary instance from the provided ELF file, extracting
    /// the necessary segments, symbols, and relocations
    pub fn from_object_file(elf: &object::File<'_>) -> Result<Self> {
        Self::validate_elf(elf)?;

        let ro_segment = Self::ro_segment(elf)?;
        let rw_segment = Self::rw_segment(elf)?;
        let stack_section = Self::stack_section(elf)?;

        let entry_va = Self::entry_address(elf)?;

        Ok(Self {
            entry_va,
            ro_segment,
            rw_segment,
            stack: stack_section,
        })
    }

    pub fn to_bytes(&self) -> Result<Vec<u8>> {
        let mut binary = Vec::new();
        self.write_to(&mut binary)?;
        Ok(binary)
    }

    /// Prints information about the app binary
    pub fn print_info(&self) {
        println!(
            "Code segment: {} (incl. {} relocations, {} init data)",
            format_kb(self.ro_segment.data.len()),
            format_kb(self.ro_segment.relocations.len() + self.rw_segment.relocations.len()),
            format_kb(self.rw_segment.data.len())
        );
        println!(
            "Data segment: {} (incl. {} stack)",
            format_kb(self.rw_segment.size as usize),
            format_kb(self.stack.size as usize)
        );
    }

    /// Validates that the ELF file meets the expected format and structure requirements
    fn validate_elf(elf: &object::File<'_>) -> Result<()> {
        ensure!(
            elf.format() == object::BinaryFormat::Elf,
            "Unsupported binary format: {:?}",
            elf.format()
        );

        ensure!(
            elf.architecture() == object::Architecture::Arm,
            "Unsupported architecture: {:?}",
            elf.architecture()
        );

        ensure!(!elf.is_64(), "Only 32-bit binaries are supported");

        ensure!(
            elf.is_little_endian(),
            "Only little-endian binaries are supported"
        );

        ensure!(
            elf.kind() == object::ObjectKind::Executable,
            "Only executable binaries are supported"
        );

        let segment_count = elf.segments().count();
        ensure!(
            segment_count == 2,
            "Expected exactly 2 segments, found {}",
            segment_count
        );

        Ok(())
    }

    /// Finds the startup symbol and returns its virtual address
    fn entry_address(elf: &object::File<'_>) -> Result<u32> {
        let startup_symbol = elf
            .symbols()
            .find(|symbol| symbol.name().ok() == Some(Self::ENTRY_SYMBOL))
            .with_context(|| format!("Failed to find the '{}' symbol", Self::ENTRY_SYMBOL))?;

        u32::try_from(startup_symbol.address())
            .context("Startup symbol address does not fit in u32")
    }

    /// Finds and reads the read-only segment containing code and data.
    /// Returns the file offset and the segment data as a byte vector.
    fn ro_segment(elf: &object::File<'_>) -> Result<RoSegment> {
        let ro_segment = elf
            .segments()
            .find(|segment| {
                let perm = segment.permissions();
                perm.readonly() && perm.executable()
            })
            .context("Failed to find the read-only segment")?;

        let mut data = ro_segment
            .data()
            .context("Failed to read the read-only segment data")
            .map(|data| data.to_vec())?;

        // Pad data with zeroes to ensure it is properly aligned
        let padding = data.len().next_multiple_of(MPU_ALIGNMENT) - data.len();
        data.extend(vec![0; padding]);
      
        let relocations = [
            Self::relocations(elf, ".text")?,
            Self::relocations(elf, ".rodata")?,
        ].concat();

        Ok(RoSegment {
            va: u32::try_from(ro_segment.address())
                .context("Read-segment address does not fit in u32")?,
            data,
            relocations,
        })
    }

    /// Finds the read-write segment and calculates the init virtual address and size
    fn rw_segment(elf: &object::File<'_>) -> Result<RwSegment> {
        let rw_segment = elf
            .segments()
            .find(|segment| {
                let perm = segment.permissions();
                perm.readable() && perm.writable() && !perm.executable()
            })
            .context("Failed to find the read-write segment")?;

        let data = rw_segment
            .data()
            .context("Failed to read the read-write segment data")
            .map(|data| data.to_vec())?;

        let relocations = Self::relocations(elf, ".data")?;

        Ok(RwSegment {
            va: u32::try_from(rw_segment.address())
                .context("Read-write segment address does not fit in u32")?,
            size: u32::try_from(rw_segment.size())
                .context("Read-write segment size does not fit in u32")?,
            data,
            relocations,
        })
    }

    fn relocations(elf: &object::File<'_>, section: &str) -> Result<Vec<u8>> {
        let Some(rel_section) = elf
            .sections()
            .find(|s| s.name() == Ok(section))
        else {
            return Ok(Vec::new());
        };

        // Filter relocation that we want to apply
        let relocations = rel_section
            .relocations()
            .filter_map(|(address, relocation)| {
                let RelocationTarget::Symbol(symbol_index) = relocation.target() else {
                    return None;
                };

                let symbol = elf.symbol_by_index(symbol_index).ok()?;
                let section = elf.section_by_index(symbol.section_index()?).ok()?;
                let in_rw_segment = matches!(section.name(), Ok(".data") | Ok(".bss"));
    
                let r_type = match (relocation.flags(), in_rw_segment) {
                    (RelocationFlags::Elf { r_type: r @ R_ARM_ABS32 }, _) => r,
                    (RelocationFlags::Elf { r_type: r @ R_ARM_THM_MOVT_ABS }, _) => r,
                    (RelocationFlags::Elf { r_type: r @ R_ARM_THM_MOVW_ABS_NC }, _) => r,
                    (RelocationFlags::Elf { r_type: r @ R_ARM_THM_MOVT_PREL }, true) => r,
                    (RelocationFlags::Elf { r_type: r @ R_ARM_THM_MOVW_PREL_NC }, true) => r,
                    _ => return None,
                };

                Some((address as u32, r_type, symbol.address() as u32, in_rw_segment))
            })
            .collect::<Vec<_>>();

        // 16-bit Relocation format
        // -----------------------------------------------------------------------
        // | 15 | 14 | 13 | 12 | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
        // | type              |              offset                             |
        // -----------------------------------------------------------------------
        // type
        //   0 => skip `offset` bytes
        //   1 => skip (`offset` << 12) + next 16-bit value bytes
        //   2 => R_ARM_ABS32
        //   3 => R_ARM_THM_MOVT_ABS (next 16-bit contains low-part of target address)
        //   4 => R_ARM_THM_MOVW_ABS_NC (next 16-bit contains high-part of target address)
        //   5 => R_ARM_THM_MOVT_PREL (target rw segment)
        //   6 => R_ARM_THM_MOVW_PREL_NC
        // offset = 11 bits
        //  difference between the relocation address and the last relocation address + 1

        static REL_TYPE_RESET: u32 = 0 << 12;
        static REL_TYPE_SKIP: u32 = 1 << 12;
        static REL_TYPE_SKIP_LONG: u32 = 2 << 12;
        static REL_TYPE_ABS32: u32 = 3 << 12;
        static REL_TYPE_MOVT_ABS: u32 = 4 << 12;
        static REL_TYPE_MOVW_ABS: u32 = 5 << 12;
        static REL_TYPE_MOVT_PREL: u32 = 6 << 12;
        static REL_TYPE_MOVW_PREL: u32 = 7 << 12;
        static REL_VALUE_MAX: u32 = (1 << 12) - 1;

        let mut last_address = 0;
        let mut result = Vec::new();

        let push = |result: &mut Vec<u16>, value: u32| {
            result.push(value as u16);
        };

        if ! relocations.is_empty() {
            push(&mut result, REL_TYPE_RESET);
        }

        for (address, r_type, target_address, in_rw_segment) in relocations {
            println!(
                "Relocation: address=0x{:x}, type=0x{:x}, in_rw_segment={}",
                address, r_type, in_rw_segment
            );

            let mut offset = address - last_address;

            while offset > REL_VALUE_MAX {
                let skip = (offset - REL_VALUE_MAX).min((REL_VALUE_MAX << 16) - 1);
                if skip <= REL_VALUE_MAX {
                    push(&mut result, REL_TYPE_SKIP | skip);
                } else {
                    push(&mut result, REL_TYPE_SKIP_LONG | (skip >> 16));
                    push(&mut result, skip & 0xFFFF);
                }
                offset -= skip;
            }

            match r_type {
                R_ARM_ABS32 => push(&mut result, REL_TYPE_ABS32 | offset),
                R_ARM_THM_MOVT_ABS => {
                    push(&mut result, REL_TYPE_MOVT_ABS | offset);
                    push(&mut result, target_address & 0xFFFF);
                }
                R_ARM_THM_MOVW_ABS_NC => {
                    push(&mut result, REL_TYPE_MOVW_ABS | offset);
                    push(&mut result, target_address >> 16);
                }
                R_ARM_THM_MOVT_PREL => {
                    push(&mut result, REL_TYPE_MOVT_PREL | offset);
                }
                R_ARM_THM_MOVW_PREL_NC => {
                    push(&mut result, REL_TYPE_MOVW_PREL | offset);
                }
                _ => bail!("Unsupported relocation type: {:?}", r_type),
            }
        
            last_address = address;
        }

        // Return Vec<u8> by flattening Vec<u16> into bytes
        Ok(result
            .into_iter()
            .flat_map(|value| value.to_le_bytes())
            .collect())
    }

    /// Reads the .stack section to get the stack size and virtual address
    fn stack_section(elf: &object::File<'_>) -> Result<StackInfo> {
        let stack_section = elf
            .sections()
            .find(|section| section.name() == Ok(".stack"))
            .context("Failed to find the .stack section")?;

        Ok(StackInfo {
            va: u32::try_from(stack_section.address())
                .context("Stack section address does not fit in u32")?,
            size: u32::try_from(stack_section.size())
                .context("Stack section size does not fit in u32")?,
        })
    }

    /// Writes the app binary content to the provided writer
    fn write_to(&self, writer: &mut impl Write) -> Result<()> {
        let mut blocks: Vec<&[u8]> = vec![];

        let ro_offset = 0;
        blocks.push(&self.ro_segment.data);

        let rw_init_offset = ro_offset + self.ro_segment.data.len();
        blocks.push(&self.rw_segment.data);

        let ro_rel_offset = rw_init_offset + self.rw_segment.data.len();
        blocks.push(&self.ro_segment.relocations);

        let rw_rel_offset = ro_rel_offset + self.ro_segment.relocations.len();
        blocks.push(&self.rw_segment.relocations);

        // Ensure that ro_segment starts at the offset aligned to MPU_ALIGNMENT
        let padding = vec![0u8; rw_rel_offset.next_multiple_of(MPU_ALIGNMENT) - rw_rel_offset];
        blocks.push(&padding);

        let header = Armv8mBinaryHeader {
            version: U32::new(0),
            ro_offset: U32::new(ro_offset as u32),
            ro_va: U32::new(self.ro_segment.va),
            ro_size: U32::new(self.ro_segment.data.len() as u32),
            ro_rel_offset: U32::new(ro_rel_offset as u32),
            ro_rel_size: U32::new(self.ro_segment.relocations.len() as u32),
            rw_va: U32::new(self.rw_segment.va),
            rw_size: U32::new(self.rw_segment.size),
            rw_rel_offset: U32::new(rw_rel_offset as u32),
            rw_rel_size: U32::new(self.rw_segment.relocations.len() as u32),
            rw_init_offset: U32::new(rw_init_offset as u32),
            rw_init_size: U32::new(self.rw_segment.data.len() as u32),
            stack_va: U32::new(self.stack.va),
            stack_size: U32::new(self.stack.size),
            heap_size: U32::new(0),
            entry_va: U32::new(self.entry_va),
            runtime_flags: U32::new(0),
        };

        writer
            .write_all(&header.to_padded_bytes())
            .context("Failed to write header")?;
        for data in blocks {
            writer.write_all(data).context("Failed to write binary")?;
        }

        println!("Header: {:?} bytes", header);

        Ok(())
    }
}

/// Formats the given byte size as a human-readable string in kilobytes
/// with one decimal place
fn format_kb(bytes: usize) -> String {
    if bytes < 512 {
        format!("{} B", bytes)
    } else {
        format!("{:.1} KB", bytes as f64 / 1024.0)
    }
}
