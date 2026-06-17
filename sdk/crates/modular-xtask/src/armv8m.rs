//! Converts an ARMv8-M ELF executable file into a custom binary format suitable
//! for loading as an Trezor applet.
//!
//! The app binary format consists of a fixed-size header followed by the read-only
//! segment data and a list of relocation addresses. The header contains metadata about
//! the app, such as the virtual address of the entry function, sizes and addresses
//! of the read-only and read-write segments, and stack information.

use anyhow::{Context, Result, ensure};
use object::{Object, ObjectSection, ObjectSegment, ObjectSymbol};
use std::{fmt, io::Write, mem::size_of};
use zerocopy::{IntoBytes, LittleEndian, U32};
use zerocopy_derive::{Immutable, IntoBytes};

#[repr(C)]
#[derive(IntoBytes, Immutable)]
struct Armv8mBinaryHeader {
    /// Size of the read-only segment. Read-only segment starts always just after the header,
    /// and its virtual address is always 0.
    ro_size: U32<LittleEndian>,
    /// Number of relocations immediately following the read-only segment data
    /// (each relocation is represented as a 4-byte virtual address in the app binary).
    reloc_count: U32<LittleEndian>,
    /// Read-write segment size that needs to be reserved in memory at load time
    rw_size: U32<LittleEndian>,
    /// Virtual address of the read-write segment
    rw_va: U32<LittleEndian>,
    /// Virtual address of the initialization data for the read-write segment.
    /// Initialization data need to be copied from the read-only segment to the
    /// read-write segment at load time
    rw_init_va: U32<LittleEndian>,
    /// Size of the initialization data for the read-write segment in bytes
    rw_init_size: U32<LittleEndian>,
    /// Virtual address of the application stack
    stack_va: U32<LittleEndian>,
    /// Application stack size in bytes
    stack_size: U32<LittleEndian>,
    /// Heap size in bytes (not used in the current implementation, set to 0)
    heap_size: U32<LittleEndian>,
    /// Virtual address of the entry function (applet_main) in the read-only segment
    entry_va: U32<LittleEndian>,
}

impl Armv8mBinaryHeader {
    /// Fixed size of the ARM app header in bytes.
    const HEADER_SIZE: usize = 0x64;

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
    /// Data of the read-only segment
    data: Vec<u8>,
    /// Virtual addresses of the absolute relocations
    /// in the read-only segment
    relocations: Vec<u32>,
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
    /// Initial virtual address of the segment
    init_va: u32,
    /// Initial size of the segment
    init_size: u32,
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

        let (ro_offset, ro_segment_data) = Self::ro_segment(elf)?;
        let relocations = Self::rodata_relocations(elf)?;

        let rw_segment = Self::rw_segment(elf, ro_offset)?;
        let stack_section = Self::stack_section(elf)?;

        let entry_va = Self::entry_address(elf)?;

        let ro_segment = RoSegment {
            data: ro_segment_data,
            relocations,
        };

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
            "Code segment: {} (incl. {} relocations)",
            format_kb(self.ro_segment.data.len()),
            self.ro_segment.relocations.len()
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
            .with_context(|| {
                format!(
                    "Failed to find the '{}' symbol",
                    Self::ENTRY_SYMBOL
                )
            })?;

        u32::try_from(startup_symbol.address())
            .context("Startup symbol address does not fit in u32")
    }

    /// Finds and reads the read-only segment containing code and data.
    /// Returns the file offset and the segment data as a byte vector.
    fn ro_segment(elf: &object::File<'_>) -> Result<(u64, Vec<u8>)> {
        let ro_segment = elf
            .segments()
            .find(|segment| {
                let perm = segment.permissions();
                perm.readonly() && perm.executable()
            })
            .context("Failed to find the read-only segment")?;

        ensure!(
            ro_segment.address() == 0,
            "Read-only segment must start at address 0, found 0x{:x}",
            ro_segment.address()
        );

        let (file_offset, _) = ro_segment.file_range();
        let mut data = ro_segment
            .data()
            .context("Failed to read the read-only segment data")
            .map(|data| data.to_vec())?;

        // Pad data with zeroes to ensure it is aligned to 4 bytes
        let padding = (4 - (data.len() % 4)) % 4;
        data.extend(vec![0; padding]);

        Ok((file_offset, data))
    }

    /// Finds the read-write segment and calculates the init virtual address and size
    fn rw_segment(elf: &object::File<'_>, ro_offset: u64) -> Result<RwSegment> {
        let rw_segment = elf
            .segments()
            .find(|segment| {
                let perm = segment.permissions();
                perm.readable() && perm.writable() && !perm.executable()
            })
            .context("Failed to find the read-write segment")?;

        let (rw_offset, _) = rw_segment.file_range();

        ensure!(
            rw_offset >= ro_offset,
            "Read-write segment file offset must not be before read-only segment file offset"
        );

        Ok(RwSegment {
            va: u32::try_from(rw_segment.address())
                .context("Read-write segment address does not fit in u32")?,
            size: u32::try_from(rw_segment.size())
                .context("Read-write segment size does not fit in u32")?,
            init_va: u32::try_from(rw_offset - ro_offset)
                .context("Read-write init offset does not fit in u32")?,
            init_size: u32::try_from(
                rw_segment
                    .data()
                    .context("Failed to read the read-write segment data")?
                    .len(),
            )
            .context("Read-write segment initialized size does not fit in u32")?,
        })
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

    /// Collects the addresses of all relocations in the .rodata section.
    ///
    /// Returns a vector of relocation addresses as u32 value, that
    /// represent the virtual addresses in the read-only segment
    /// that need to be relocated at load time.
    ///
    /// Only Absolute relocations with zero addend are supported.
    fn rodata_relocations(elf: &object::File<'_>) -> Result<Vec<u32>> {
        let ro_data = elf
            .sections()
            .find(|section| section.name() == Ok(".rodata"))
            .context("Failed to find the .rodata section")?;

        ro_data
            .relocations()
            .map(|(address, relocation)| {
                ensure!(
                    relocation.kind() == object::RelocationKind::Absolute
                        && relocation.addend() == 0,
                    "All relocations in .rodata must be Absolute with zero addend"
                );

                Ok(address as u32)
            })
            .collect::<Result<Vec<_>>>()
    }

    /// Writes the app binary content to the provided writer
    fn write_to(&self, writer: &mut impl Write) -> Result<()> {
        writer
            .write_all(&self.header_bytes()?)
            .context("Failed to write the header to the output file")?;

        writer
            .write_all(&self.ro_segment.data)
            .context("Failed to write .rodata content to the output file")?;

        for relocation in &self.ro_segment.relocations {
            writer
                .write_all(&relocation.to_le_bytes())
                .context("Failed to write relocation address to the output file")?;
        }

        Ok(())
    }

    /// Builds the app header and convert it to a byte array of size APP_HEADER_SIZE
    fn header_bytes(&self) -> Result<[u8; Armv8mBinaryHeader::HEADER_SIZE]> {
        let ro_size = u32::try_from(self.ro_segment.data.len())
            .context("Read-only segment size does not fit in u32")?;

        let reloc_count = u32::try_from(self.ro_segment.relocations.len())
            .context("Relocation count does not fit in u32")?;

        let arm_header = Armv8mBinaryHeader {
            entry_va: U32::new(self.entry_va),
            ro_size: U32::new(ro_size),
            reloc_count: U32::new(reloc_count),
            rw_size: U32::new(self.rw_segment.size),
            rw_va: U32::new(self.rw_segment.va),
            rw_init_va: U32::new(self.rw_segment.init_va),
            rw_init_size: U32::new(self.rw_segment.init_size),
            stack_va: U32::new(self.stack.va),
            stack_size: U32::new(self.stack.size),
            heap_size: U32::new(0),
        };


        Ok(arm_header.to_padded_bytes())
    }
}

/// Formats the given byte size as a human-readable string in kilobytes
/// with one decimal place
fn format_kb(bytes: usize) -> String {
    format!("{:.1} KB", bytes as f64 / 1024.0)
}

