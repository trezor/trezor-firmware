//! Converts an ELF executable file into a custom binary format suitable
//! for loading as a Trezor applet.
//!
//! The app binary format consists of a fixed-size header followed by the platform
//! specific executable binary.

use anyhow::{Context, Result, ensure};
use cargo_metadata::Package;
use object::Object;
use std::{
    fs,
    io::Write,
    mem::size_of,
    path::{Path, PathBuf},
};
use zerocopy::{IntoBytes, LittleEndian, U32};
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
///
#[repr(C)]
#[derive(IntoBytes, Immutable, Debug)]
struct AppHeader {
    /// Magic number to identify the app binary format
    magic: U32<LittleEndian>,
    /// Header size in bytes (contains AppHeader::APP_HEADER_SIZE)
    size: U32<LittleEndian>,
    /// Unique identifier of the app
    identifier: [u8; AppHeader::APP_ID_MAX_LEN],
    /// App version in the format major.minor.patch.build, each as a byte
    /// For example, version 1.2.3 would be represented as [1, 2, 3, 0]
    version: [u8; 4],
    /// SDK version that the app was built against
    sdk_version: [u8; 2],
    /// ABI version that the app was built against
    abi_version: u8,
    /// Type of binary payload (e.g., ARMV8M, X86_64)
    payload_type: u8,
    /// Size of binary payload in bytes
    payload_size: U32<LittleEndian>,
    // TODO app_name
    // TODO vendor_name
    // TODO logo
    // TODO model
    // TODO bip32_paths
}

impl AppHeader {
    /// Fixed size of the app header in bytes.
    const APP_HEADER_SIZE: usize = 0x100;
    /// Magic number used to identify the app binary format in the header.
    const APP_HEADER_MAGIC: u32 = 0x415A5254; // TRZA
    /// Maximum length of the app identifier string in bytes.
    const APP_ID_MAX_LEN: usize = 32;

    fn to_padded_bytes(&self) -> [u8; AppHeader::APP_HEADER_SIZE] {
        let mut bytes = [0u8; AppHeader::APP_HEADER_SIZE];
        bytes[..size_of::<AppHeader>()].copy_from_slice(self.as_bytes());
        bytes
    }
}

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

pub fn convert_elf_to_bin(elf_path: &Path, package: &Package) -> Result<PathBuf> {
    let (payload_type, payload) = load_elf_payload(elf_path)?;

    let header = AppHeader {
        magic: U32::new(AppHeader::APP_HEADER_MAGIC),
        size: U32::new(AppHeader::APP_HEADER_SIZE as u32),
        identifier: app_identifier(package)?,
        version: app_version(package)?,
        sdk_version: [0; 2],
        abi_version: 1,
        payload_type: payload_type as u8,
        payload_size: U32::new(payload.len() as u32),
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
