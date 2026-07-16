//! Converts an ELF executable file into a custom binary format suitable
//! for loading as a Trezor applet.
//!
//! The app binary format consists of a fixed-size header followed by the platform
//! specific executable binary.

use anyhow::{Context, Result, ensure};
use cargo_metadata::Package;
use object::Object;
use sha2::Digest;
use std::{
    fs,
    io::Write,
    mem::size_of,
    path::{Path, PathBuf},
};
use zerocopy::{IntoBytes, LittleEndian, U16, U32};
use zerocopy_derive::{Immutable, IntoBytes};

use crate::{armv8m, metadata};

#[repr(u32)]
enum AppBinaryType {
    ARMV8M = 0,
    X86_64 = 1,
}

/// The app header is a fixed-size structure at the beginning of the application image
/// containing metadata about the app, such as segment sizes and addresses padded
/// with zeroes to ensure it is exactly APP_HEADER_SIZE bytes in size.
#[repr(C)]
#[derive(IntoBytes, Immutable, Debug)]
struct AppHeader {
    /// Magic number to identify the app binary format
    magic: U32<LittleEndian>,
    /// Header size in bytes (contains AppHeader::APP_HEADER_SIZE)
    header_size: U32<LittleEndian>,
    /// Unique identifier of the app (utf-8 encoded, zero-padded)
    id: [u8; metadata::APP_ID_MAX_LEN],
    /// App name (utf-8 encoded, zero-padded)
    app_name: [u8; metadata::APP_NAME_MAX_LEN],
    /// Vendor name (utf-8 encoded, zero-padded)
    vendor_name: [u8; metadata::APP_VENDOR_MAX_LEN],
    /// Target model identifier (or zeroed for universal apps)
    model: [u8; 4],
    /// App version in the format major.minor.patch.build, each as a byte
    /// For example, version 1.2.3 would be represented as [1, 2, 3, 0]
    version: [u8; 4],
    /// SDK version that the app was built against
    sdk_version: [u8; 4],
    /// ABI version that the app was built against
    abi_version: u8,
    /// Target architecture of the binary payload (e.g., ARMV8M, X86_64)
    target_arch: u8,
    /// Application privilege ring
    app_ring: u8,
    /// Padding, reserved for future use
    reserved1: [u8; 1],
    /// Size of binary payload (code + init and relocation data)
    code_size: U32<LittleEndian>,
    /// Size of RAM required by the app
    /// (includes stack, heap, and static data)
    data_size: U32<LittleEndian>,
    /// Hash of the first payload chunk
    chunk_hash: [u8; 32],
    /// Size of each chunk of the binary payload in bytes
    chunk_size: U16<LittleEndian>,
    /// Reserved field for runtime purposes (zeroed)
    reserved2: [u8; 2],
    // TODO logo
    // TODO bip32_paths
}

impl AppHeader {
    /// Fixed size of the app header in bytes.
    const APP_HEADER_SIZE: usize = 0x100;
    /// Magic number used to identify the app binary format in the header.
    const APP_HEADER_MAGIC: u32 = 0x415A5254; // TRZA
    /// Chunk size used for hashing the payload in bytes.
    const CHUNK_SIZE: usize = 2048;

    fn to_padded_bytes(&self) -> [u8; AppHeader::APP_HEADER_SIZE] {
        let mut bytes = [0u8; AppHeader::APP_HEADER_SIZE];
        bytes[..size_of::<AppHeader>()].copy_from_slice(self.as_bytes());
        bytes
    }
}

pub fn convert_elf_to_bin(elf_path: &Path, package: &Package) -> Result<PathBuf> {
    let raw_elf = fs::read(elf_path)
        .with_context(|| format!("Failed to read the elf file {:?}", elf_path))?;

    let elf = object::File::parse(&*raw_elf)
        .with_context(|| format!("Failed to parse the elf file {:?}", elf_path))?;

    ensure!(
        elf.format() == object::BinaryFormat::Elf,
        "Unsupported binary format: {:?}",
        elf.format()
    );

    let (target_arch, code, data_size) = match elf.architecture() {
        object::Architecture::Arm => {
            let arm_binary = armv8m::Armv8mBinary::from_object_file(&elf, package)?;
            arm_binary.print_info();
            (
                AppBinaryType::ARMV8M,
                arm_binary.to_bytes()?,
                arm_binary.ram_size(),
            )
        }
        object::Architecture::X86_64 => (AppBinaryType::X86_64, raw_elf, 0),
        arch => anyhow::bail!("Unsupported architecture: {:?}", arch),
    };

    let header = AppHeader {
        magic: U32::new(AppHeader::APP_HEADER_MAGIC),
        header_size: U32::new(AppHeader::APP_HEADER_SIZE as u32),
        id: metadata::app_identifier(package)?,
        app_name: metadata::app_name(package)?,
        vendor_name: metadata::vendor_name(package)?,
        model: [0; 4],
        version: metadata::app_version(package)?,
        sdk_version: [0; 4],
        abi_version: 1,
        target_arch: target_arch as u8,
        app_ring: metadata::app_ring(package)?,
        reserved1: [0; 1],
        code_size: U32::new(code.len() as u32),
        chunk_hash: hash_payload(&code, AppHeader::CHUNK_SIZE),
        data_size: U32::new(data_size),
        chunk_size: U16::new(AppHeader::CHUNK_SIZE as u16),
        reserved2: [0; 2],
    };

    let bin_path = elf_path.with_extension("bin");

    let bin_file = fs::File::create(&bin_path)
        .with_context(|| format!("Failed to create output file {:?}", bin_path))?;

    let mut writer = std::io::BufWriter::new(bin_file);

    writer
        .write_all(&header.to_padded_bytes())
        .context("Failed to write the app header to the output file")?;

    writer
        .write_all(&code)
        .context("Failed to write the app binary data to the output file")?;

    Ok(bin_path)
}

/// Computes the SHA256 hash of the payload in chunks, processing them in reverse order.
/// The approach allows checking the integrity of the payload during loading, by
/// chunks of the specified size.
fn hash_payload(payload: &[u8], chunk_size: usize) -> [u8; 32] {
    payload
        .chunks(chunk_size)
        .rev()
        .fold([0u8; 32], |prev_hash, chunk| {
            let mut hasher = sha2::Sha256::new();
            hasher.update(chunk);
            hasher.update(prev_hash);
            hasher.finalize().into()
        })
}
