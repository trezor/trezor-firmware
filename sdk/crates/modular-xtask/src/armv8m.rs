//! Converts an ARMv8-M ELF executable file into a custom binary format suitable
//! for loading as a Trezor external application
//!
//! The app binary format consists of a fixed-size header followed by the read-only
//! segment data and a list of relocation addresses. The header contains metadata about
//! the app, such as the virtual address of the entry function, sizes and addresses
//! of the read-only and read-write segments, and stack information.

use anyhow::{Context, Result, bail, ensure};
use cargo_metadata::Package;
use object::{
    Object, ObjectSection, ObjectSegment, ObjectSymbol, RelocationFlags, RelocationTarget,
    SymbolKind,
    elf::{
        R_ARM_ABS32, R_ARM_THM_JUMP24, R_ARM_THM_MOVT_ABS, R_ARM_THM_MOVW_ABS_NC, R_ARM_THM_PC22,
    },
};
use std::{borrow::Cow, fmt, io::Write, mem::size_of};
use zerocopy::{IntoBytes, LittleEndian, U32};
use zerocopy_derive::{Immutable, IntoBytes};

use crate::metadata;

const MPU_ALIGNMENT: usize = 32;
const STACK_ALIGNMENT: usize = 8;

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
    /// Minimal stack size
    stack_size: U32<LittleEndian>,
    /// Minimal heap size
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
    /// Minimal stack size
    stack_size: u32,
    /// Minimal heap size
    heap_size: u32,
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

struct BinaryBlocks<'a> {
    blocks: Vec<Cow<'a, [u8]>>,
}

impl<'a> BinaryBlocks<'a> {
    fn new() -> Self {
        Self { blocks: Vec::new() }
    }

    fn append(&mut self, data: &'a [u8]) -> u32 {
        let size = self.size();
        self.blocks.push(Cow::Borrowed(data));
        size as u32
    }

    fn pad(&mut self, alignment: usize) {
        let size = self.size();
        let padding = size.next_multiple_of(alignment) - size;
        self.blocks.push(Cow::Owned(vec![0u8; padding]));
    }

    fn size(&self) -> usize {
        self.blocks.iter().map(|block| block.len()).sum()
    }
}

impl<'a> IntoIterator for BinaryBlocks<'a> {
    type Item = Cow<'a, [u8]>;
    type IntoIter = std::vec::IntoIter<Self::Item>;

    fn into_iter(self) -> Self::IntoIter {
        self.blocks.into_iter()
    }
}

struct Relocation {
    // Virtual address where the relocation should be applied
    address: u32,
    // Relocation type (e.g., R_ARM_ABS32, R_ARM_THM_MOVT_ABS, etc.)
    r_type: u32,
    // Virtual address of the target symbol for the relocation
    target: u32,
}

impl Armv8mBinary {
    /// Name of the startup symbol that must be defined in the ELF file.
    const ENTRY_SYMBOL: &str = "applet_main";

    /// Creates an AppBinary instance from the provided ELF file, extracting
    /// the necessary segments, symbols, and relocations
    pub fn from_object_file(elf: &object::File<'_>, package: &Package) -> Result<Self> {
        Self::validate_elf(elf)?;

        let ro_segment = Self::ro_segment(elf)?;
        let rw_segment = Self::rw_segment(elf)?;

        let entry_va = Self::entry_address(elf)?;

        Ok(Self {
            entry_va,
            ro_segment,
            rw_segment,
            stack_size: metadata::stack_size(package)?,
            heap_size: metadata::heap_size(package)?,
        })
    }

    pub fn to_bytes(&self) -> Result<Vec<u8>> {
        let mut binary = Vec::new();
        self.write_to(&mut binary)?;
        Ok(binary)
    }

    /// Prints information about the app binary
    pub fn print_info(&self) {
        let rel_size = self.ro_segment.relocations.len() + self.rw_segment.relocations.len();
        let init_size = self.rw_segment.data.len();
        println!(
            "Code segment: {} (incl. {} relocations, {} init data)",
            format_kb(self.ro_segment.data.len() + rel_size + init_size),
            format_kb(rel_size),
            format_kb(init_size)
        );
        println!(
            "Data segment: {} (incl. {} stack, {} heap)",
            format_kb((self.rw_segment.size + self.stack_size + self.heap_size) as usize),
            format_kb(self.stack_size as usize),
            format_kb(self.heap_size as usize)
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

    /// Finds and reads the read-only segment containing code and rodata.
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
        ]
        .concat();

        Ok(RoSegment {
            va: u32::try_from(ro_segment.address())
                .context("Read-only segment address does not fit in u32")?,
            data,
            relocations,
        })
    }

    /// Finds the read-write segment
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

    /// Parses the relocation entries for the specified section.
    fn relocations(elf: &object::File<'_>, section: &str) -> Result<Vec<u8>> {
        let Some(rel_section) = elf.sections().find(|s| s.name() == Ok(section)) else {
            // Section not found, return empty relocation list
            return Ok(Vec::new());
        };

        // Filter out relocations that do not make sense for our use case.
        // This significantly reduces the number of relocations we need to
        // store in the binary.
        let relocations = rel_section.relocations().try_fold(
            Vec::new(),
            |mut relocations, (address, relocation)| -> Result<_> {
                let RelocationTarget::Symbol(symbol_index) = relocation.target() else {
                    bail!("Unsupported relocation target: {:?}", relocation.target());
                };

                let symbol = elf
                    .symbol_by_index(symbol_index)
                    .context("Invalid relocation symbol")?;

                let section = symbol
                    .section_index()
                    .and_then(|section_index| elf.section_by_index(section_index).ok())
                    .context("Invalid relocation symbol section")?;

                let RelocationFlags::Elf { r_type } = relocation.flags() else {
                    bail!("Unsupported relocation type: {:?}", relocation.flags());
                };

                let in_code = matches!(section.name(), Ok(".text") | Ok(".rodata"));

                // Ignored relocation?
                if matches!(r_type, R_ARM_THM_PC22 | R_ARM_THM_JUMP24) && in_code {
                    // Ignored relocations
                    return Ok(relocations);
                }

                // Supported relocation type? 
                match r_type {
                    R_ARM_ABS32 => {}
                    R_ARM_THM_MOVW_ABS_NC | R_ARM_THM_MOVT_ABS => {
                        Self::verify_movx_addend_zero(r_type, address, &rel_section, &symbol)?;
                    }
                    _ => bail!("Unsupported relocation type: {:?}", relocation.flags()),
                }

                relocations.push(Relocation {
                    address: address as u32,
                    r_type,
                    target: symbol.address() as u32,
                });
                Ok(relocations)
            },
        )?;

        Self::encode_relocations(relocations)
    }

    /// Verifies that a MOVW/MOVT relocation carries a zero implicit addend.
    ///
    /// A standalone MOVW/MOVT reconstructs the *other* half of the 32-bit target
    /// from the symbol address rather than from its paired instruction, so a
    /// non-zero addend would be silently mis-encoded. This checks the assumption
    /// per entry: the resolved immediate in the instruction must equal the
    /// corresponding half of the symbol address (low half for MOVW, high half
    /// for MOVT). Because every pair shares one symbol, checking every MOVW and
    /// every MOVT proves `S + A == S` (addend 0) for every target, without
    /// needing to pair them.
    ///
    /// In practice rustc/LLVM emits a distinct symbol for each constant (exact
    /// address, addend 0), and REL cannot fold a carrying offset into a MOVW/MOVT
    /// immediate anyway, so this check never fails today. If a future toolchain
    /// (or hand-written asm such as `movw #:lower16:foo+2`) introduces a non-zero
    /// addend, the build fails with an error instead of producing a broken image.
    fn verify_movx_addend_zero<'data>(
        r_type: u32,
        address: u64,
        section: &impl ObjectSection<'data>,
        symbol: &impl ObjectSymbol<'data>,
    ) -> Result<()> {
        let section_va = section.address();
        let section_data = section
            .data()
            .context("Failed to read section data for relocation check")?;
        let offset = (address as usize)
            .checked_sub(section_va as usize)
            .context("Relocation address precedes its section")?;
        let word = section_data
            .get(offset..offset + 4)
            .context("Relocation address out of section bounds")?;
        let instruction = u32::from_le_bytes(word.try_into().unwrap());
        let imm = Self::extract_movx_imm(instruction);

        // Thumb function symbols carry the interworking bit (bit 0) in the
        // resolved value; it only affects the low half (MOVW).
        let thumb_bit = matches!(symbol.kind(), SymbolKind::Text) as u32;
        let target = symbol.address() as u32;
        let expected = if r_type == R_ARM_THM_MOVW_ABS_NC {
            ((target | thumb_bit) & 0xFFFF) as u16
        } else {
            ((target >> 16) & 0xFFFF) as u16
        };

        ensure!(
            imm == expected,
            "MOVW/MOVT relocation at {:#010x} against '{}' has a non-zero addend \
             (immediate {:#06x} != expected {:#06x}); the standalone MOVW/MOVT \
             encoding cannot represent it",
            address,
            symbol.name().unwrap_or("<unnamed>"),
            imm,
            expected
        );

        Ok(())
    }

    /// Extracts the 16-bit immediate from a Thumb-2 MOVW/MOVT instruction word.
    /// Mirrors `extract_movx_value` in the on-device loader.
    fn extract_movx_imm(instruction: u32) -> u16 {
        let imm1 = ((instruction >> 10) & 0x1) as u16;
        let imm4 = (instruction & 0xF) as u16;
        let imm3 = ((instruction >> 28) & 0x7) as u16;
        let imm8 = ((instruction >> 16) & 0xFF) as u16;
        (imm4 << 12) | (imm1 << 11) | (imm3 << 8) | imm8
    }

    /// Encodes relocation entries into the compact 16-bit binary format.
    fn encode_relocations(relocations: Vec<Relocation>) -> Result<Vec<u8>> {
        // 16-bit Relocation format
        // -----------------------------------------------------------------------
        // | 15 | 14 | 13 | 12 | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
        // | type              |              offset                             |
        // -----------------------------------------------------------------------
        // type
        //   0 => reset `offset` to 0
        //   1 => skip `offset` bytes
        //   2 => skip (`offset` << 16) + next 16-bit value bytes
        //   3 => R_ARM_ABS32
        //   4 => R_ARM_THM_MOVW_ABS_NC (next 16-bit contains high-part of target address)
        //   5 => R_ARM_THM_MOVT_ABS (next 16-bit contains low-part of target address)
        //   6 => R_ARM_THM_MOVW_ABS_NC + R_ARM_THM_MOVT_ABS pair (no trailing word;
        //        the movt instruction is at `offset` + 4 and both halves of the
        //        target address are recovered from the two instructions)
        // offset = 12 bits
        //  difference between the relocation address and the last relocation address

        static REL_TYPE_RESET_ADDR: u32 = 0 << 12;
        static REL_TYPE_SKIP_SHORT: u32 = 1 << 12;
        static REL_TYPE_SKIP_LONG: u32 = 2 << 12;
        static REL_TYPE_ABS32: u32 = 3 << 12;
        static REL_TYPE_MOVW_ABS: u32 = 4 << 12;
        static REL_TYPE_MOVT_ABS: u32 = 5 << 12;
        static REL_TYPE_MOVW_MOVT_ABS: u32 = 6 << 12;

        static REL_VALUE_MAX: u32 = (1 << 12) - 1;

        let mut address = None;
        let mut result = Vec::new();

        let push = |result: &mut Vec<u16>, value: u32| {
            result.push(value as u16);
        };

        let mut i = 0;
        while i < relocations.len() {
            let rel = &relocations[i];

            // We rely on the fact that the relocations are sorted
            // by address, so we can compute the offset
            ensure!(
                address.is_none_or(|address| rel.address > address),
                "Relocation addresses must be in ascending order"
            );

            if address.is_none() {
                // The first relocation entry is always a reset
                push(&mut result, REL_TYPE_RESET_ADDR);
                address = Some(0);
            }

            let mut offset = rel.address - address.unwrap_or(0);

            // Insert skip entries if the offset is larger than
            // the maximum value that can be stored in 12 bits.
            while offset > REL_VALUE_MAX {
                let skip = (offset - REL_VALUE_MAX).min((REL_VALUE_MAX << 16) - 1);
                if skip <= REL_VALUE_MAX {
                    push(&mut result, REL_TYPE_SKIP_SHORT | skip);
                } else {
                    push(&mut result, REL_TYPE_SKIP_LONG | (skip >> 16));
                    push(&mut result, skip & 0xFFFF);
                }
                offset -= skip;
            }

            // Insert the relocation entry based on its type
            match rel.r_type {
                R_ARM_ABS32 => push(&mut result, REL_TYPE_ABS32 | offset),
                R_ARM_THM_MOVW_ABS_NC => {
                    // Collapse an adjacent MOVW/MOVT pair that targets the same
                    // symbol into a single 2-byte entry. The loader recovers both
                    // halves of the target address directly from the two
                    // instructions, so no trailing word is needed.
                    if let Some(next) = relocations.get(i + 1)
                        && next.r_type == R_ARM_THM_MOVT_ABS
                        && next.address == rel.address + 4
                        && next.target == rel.target
                    {
                        push(&mut result, REL_TYPE_MOVW_MOVT_ABS | offset);
                        // Skip the movt; it is consumed as part of the pair.
                        i += 1;
                    } else {
                        push(&mut result, REL_TYPE_MOVW_ABS | offset);
                        push(&mut result, rel.target >> 16);
                    }
                }
                R_ARM_THM_MOVT_ABS => {
                    push(&mut result, REL_TYPE_MOVT_ABS | offset);
                    push(&mut result, rel.target & 0xFFFF);
                }
                _ => bail!("Unsupported relocation type: {:?}", rel.r_type),
            }

            address = Some(rel.address);
            i += 1;
        }

        // Return Vec<u8> by flattening Vec<u16> into bytes
        Ok(result
            .into_iter()
            .flat_map(|value| value.to_le_bytes())
            .collect())
    }

    /// Writes the app binary content to the provided writer
    fn write_to(&self, writer: &mut impl Write) -> Result<()> {
        let mut blocks = BinaryBlocks::new();

        let ro_offset = blocks.append(&self.ro_segment.data);
        let rw_init_offset = blocks.append(&self.rw_segment.data);
        let ro_rel_offset = blocks.append(&self.ro_segment.relocations);
        let rw_rel_offset = blocks.append(&self.rw_segment.relocations);

        // Ensure that we end up with a binary that is
        // aligned to the MPU_ALIGNMENT boundary.
        blocks.pad(MPU_ALIGNMENT);

        let header = Armv8mBinaryHeader {
            version: U32::new(0),
            ro_offset: U32::new(ro_offset),
            ro_va: U32::new(self.ro_segment.va),
            ro_size: U32::new(self.ro_segment.data.len() as u32),
            ro_rel_offset: U32::new(ro_rel_offset),
            ro_rel_size: U32::new(self.ro_segment.relocations.len() as u32),
            rw_va: U32::new(self.rw_segment.va),
            rw_size: U32::new(self.rw_segment.size),
            rw_rel_offset: U32::new(rw_rel_offset),
            rw_rel_size: U32::new(self.rw_segment.relocations.len() as u32),
            rw_init_offset: U32::new(rw_init_offset),
            rw_init_size: U32::new(self.rw_segment.data.len() as u32),
            stack_size: U32::new(self.stack_size),
            heap_size: U32::new(self.heap_size),
            entry_va: U32::new(self.entry_va),
            runtime_flags: U32::new(0),
        };

        writer
            .write_all(&header.to_padded_bytes())
            .context("Failed to write header")?;

        for data in blocks {
            writer
                .write_all(data.as_ref())
                .context("Failed to write binary")?;
        }

        Ok(())
    }

    pub fn ram_size(&self) -> u32 {
        self.rw_segment.size.next_multiple_of(MPU_ALIGNMENT as u32)
            + self.stack_size.next_multiple_of(STACK_ALIGNMENT as u32)
            + self.heap_size.next_multiple_of(MPU_ALIGNMENT as u32)
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
