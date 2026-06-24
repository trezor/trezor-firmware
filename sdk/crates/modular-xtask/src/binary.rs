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

use crate::armv8m;

#[repr(u32)]
enum AppBinaryType {
    ARMV8M = 0,
    X86_64 = 1,
}

/// The app header is a fixed-size structure at the beginning of the applicatio image
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
    id: [u8; AppHeader::APP_ID_MAX_LEN],
    /// App name (utf-8 encoded, zero-padded)
    app_name: [u8; AppHeader::APP_NAME_MAX_LEN],
    /// Vendor name (utf-8 encoded, zero-padded)
    vendor_name: [u8; AppHeader::APP_VENDOR_MAX_LEN],
    /// Target model identifier (or zeroed for universal apps)
    model: [u8; 4],
    /// App version in the format major.minor.patch.build, each as a byte
    /// For example, version 1.2.3 would be represented as [1, 2, 3, 0]
    version: [u8; 4],
    /// SDK version that the app was built against
    sdk_version: [u8; 4],
    /// ABI version that the app was built against
    abi_version: u8,
    /// Type of binary payload (e.g., ARMV8M, X86_64)
    payload_type: u8,
    // Padding, reserved for future use
    reserved1: [u8; 2],
    /// Size of binary payload in bytes
    payload_size: U32<LittleEndian>,
    /// Chain hash of payload chunks processed in reverse order
    payload_hash: [u8; 32],
    /// Size of each chunk of the payload in bytes
    chunk_size: U16<LittleEndian>,
    /// Reserved field for runtime purposes (zeroed)
    reserved2: U16<LittleEndian>,
    // TODO logo
    // TODO bip32_paths
}

impl AppHeader {
    /// Fixed size of the app header in bytes.
    const APP_HEADER_SIZE: usize = 0x100;
    /// Magic number used to identify the app binary format in the header.
    const APP_HEADER_MAGIC: u32 = 0x415A5254; // TRZA
    /// Maximum length of the app identifier string in bytes.
    const APP_ID_MAX_LEN: usize = 32;
    /// Maximum length of the app name string in bytes.
    const APP_NAME_MAX_LEN: usize = 32;
    /// Maximum length of the vendor name string in bytes.
    const APP_VENDOR_MAX_LEN: usize = 32;
    /// Chunk size used for hashing the payload in bytes.
    const CHUNK_SIZE: usize = 2048;

    fn to_padded_bytes(&self) -> [u8; AppHeader::APP_HEADER_SIZE] {
        let mut bytes = [0u8; AppHeader::APP_HEADER_SIZE];
        bytes[..size_of::<AppHeader>()].copy_from_slice(self.as_bytes());
        bytes
    }
}

/// Retrieves the app version from the package metadata and converts it into a 4-byte array.
fn app_version(package: &Package) -> Result<[u8; 4]> {
    let ver = package.version.clone();
    Ok([
        ver.major
            .try_into()
            .context("Failed to convert major version to u8")?,
        ver.minor
            .try_into()
            .context("Failed to convert minor version to u8")?,
        ver.patch
            .try_into()
            .context("Failed to convert patch version to u8")?,
        0,
    ])
}

/// Retrieves the app identifier from the package metadata.
fn app_identifier(package: &Package) -> Result<[u8; AppHeader::APP_ID_MAX_LEN]> {
    let id = package
        .metadata
        .get("trezor")
        .and_then(|m| m.get("id"))
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow::anyhow!("App identifier not found in Cargo.toml"))?;

    let id_bytes = id.as_bytes();

    ensure!(
        id_bytes.len() <= AppHeader::APP_ID_MAX_LEN,
        "App identifier '{}' is too long (max {} bytes)",
        id,
        AppHeader::APP_ID_MAX_LEN
    );

    let mut result = [0u8; AppHeader::APP_ID_MAX_LEN];
    result[..id_bytes.len()].copy_from_slice(&id_bytes);

    Ok(result)
}

/// Retrieve the app name from the package metadata.
fn app_name(package: &Package) -> Result<[u8; AppHeader::APP_NAME_MAX_LEN]> {
    let name = package
        .metadata
        .get("trezor")
        .and_then(|m| m.get("name"))
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow::anyhow!("App name not found in Cargo.toml"))?;

    let name_bytes = name.as_bytes();

    ensure!(
        name_bytes.len() <= AppHeader::APP_NAME_MAX_LEN,
        "App name '{}' is too long (max {} bytes)",
        name,
        AppHeader::APP_NAME_MAX_LEN
    );

    let mut result = [0u8; AppHeader::APP_NAME_MAX_LEN];
    result[..name_bytes.len()].copy_from_slice(&name_bytes);

    Ok(result)
}

/// Retrieve the vendor name from the package metadata.
fn vendor_name(package: &Package) -> Result<[u8; AppHeader::APP_VENDOR_MAX_LEN]> {
    let vendor = package
        .metadata
        .get("trezor")
        .and_then(|m| m.get("vendor"))
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow::anyhow!("Vendor name not found in Cargo.toml"))?;

    let vendor_bytes = vendor.as_bytes();

    ensure!(
        vendor_bytes.len() <= AppHeader::APP_VENDOR_MAX_LEN,
        "Vendor name '{}' is too long (max {} bytes)",
        vendor,
        AppHeader::APP_VENDOR_MAX_LEN
    );

    let mut result = [0u8; AppHeader::APP_VENDOR_MAX_LEN];
    result[..vendor_bytes.len()].copy_from_slice(&vendor_bytes);

    Ok(result)
}

/// Loads an ELF file and extracts the binary payload and its type based on the architecture.
fn load_elf_payload(elf_path: &Path) -> Result<(AppBinaryType, Vec<u8>)> {
    let raw_elf = fs::read(elf_path)
        .with_context(|| format!("Failed to read the elf file {:?}", elf_path))?;

    let elf = object::File::parse(&*raw_elf)
        .with_context(|| format!("Failed to parse the elf file {:?}", elf_path))?;

    ensure!(
        elf.format() == object::BinaryFormat::Elf,
        "Unsupported binary format: {:?}",
        elf.format()
    );

    let payload = match elf.architecture() {
        object::Architecture::Arm => {
            let arm_binary = armv8m::Armv8mBinary::from_object_file(&elf)?;
            arm_binary.print_info();
            (AppBinaryType::ARMV8M, arm_binary.to_bytes()?)
        }
        object::Architecture::X86_64 => (AppBinaryType::X86_64, raw_elf),
        arch => anyhow::bail!("Unsupported architecture: {:?}", arch),
    };

    Ok(payload)
}

/// Computes the SHA256 hash of the payload in chunks, processing them in reverse order.
/// The approach allows checking the integrity of the payload during loading, by
/// chunks of the specified size.
pub fn hash_payload(payload: &[u8], chunk_size: usize) -> [u8; 32] {
    payload
        .chunks(chunk_size)
        .rev()
        .fold([0u8; 32], |prev_hash, chunk| {
            let mut hasher = sha2::Sha256::new();
            hasher.update(chunk);
            hasher.update(&prev_hash);
            hasher.finalize().into()
        })
}

pub fn convert_elf_to_bin(elf_path: &Path, package: &Package) -> Result<PathBuf> {
    let (payload_type, payload) = load_elf_payload(elf_path)?;

    let header = AppHeader {
        magic: U32::new(AppHeader::APP_HEADER_MAGIC),
        header_size: U32::new(AppHeader::APP_HEADER_SIZE as u32),
        id: app_identifier(package)?,
        app_name: app_name(package)?,
        vendor_name: vendor_name(package)?,
        model: [0; 4],
        version: app_version(package)?,
        sdk_version: [0; 4],
        abi_version: 1,
        payload_type: payload_type as u8,
        reserved1: [0; 2],
        payload_size: U32::new(payload.len() as u32),
        payload_hash: hash_payload(&payload, AppHeader::CHUNK_SIZE),
        chunk_size: U16::new(AppHeader::CHUNK_SIZE as u16),
        reserved2: U16::new(0),
    };

    let bin_path = elf_path.with_extension("bin");

    let bin_file = fs::File::create(&bin_path)
        .with_context(|| format!("Failed to create output file {:?}", bin_path))?;

    let mut writer = std::io::BufWriter::new(bin_file);

    writer
        .write_all(&header.to_padded_bytes())
        .context("Failed to write the app header to the output file")?;

    writer
        .write_all(&payload)
        .context("Failed to write the app binary data to the output file")?;

    Ok(bin_path)
}
