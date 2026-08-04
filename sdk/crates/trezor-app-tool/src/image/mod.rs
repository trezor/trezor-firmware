//! Converts an ELF executable file into a custom binary format suitable
//! for loading as a Trezor applet.
//!
//! The app binary format consists of a fixed-size header followed by the platform
//! specific executable binary.

use anyhow::{Context, Result, ensure};
use cargo_metadata::{Package, semver::Version};
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

use crate::args::{Model, TargetArch};

mod armv8m;
mod metadata;

impl TargetArch {
    /// Returns the architecture identifier stored in the app header.
    pub fn id(&self) -> u8 {
        match self {
            TargetArch::Armv8m => 0,
            TargetArch::LinuxX86_64 => 1,
            TargetArch::MacosAarch64 => 2,
        }
    }
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
    /// Curves used for the app (e.g., secp256k1, ed25519)
    /// (utf-8 encoded, zero-padded)
    curves: [u8; AppHeader::APP_CURVES_MAX_LEN],
    /// Allowed BIP32 path prefixes
    /// Each path is a null-terminated string, and the array
    /// is zero-padded to a fixed size.
    paths: [u8; AppHeader::APP_PATHS_MAX_LEN],
    // TODO logo
}

impl AppHeader {
    /// Fixed size of the app header in bytes.
    const APP_HEADER_SIZE: usize = 0x200;
    /// Magic number used to identify the app binary format in the header.
    const APP_HEADER_MAGIC: u32 = 0x415A5254; // TRZA
    /// Chunk size used for hashing the payload in bytes.
    const CHUNK_SIZE: usize = 2048;
    /// Maximum length, in bytes, of the packed app identifier.
    const APP_ID_MAX_LEN: usize = 32;
    /// Maximum length, in bytes, of the packed app name.
    const APP_NAME_MAX_LEN: usize = 32;
    /// Maximum length, in bytes, of the packed vendor name.
    const APP_VENDOR_MAX_LEN: usize = 32;
    /// Maximum total length, in bytes, of the packed, null-terminated curve list.
    const APP_CURVES_MAX_LEN: usize = 64;
    /// Maximum total length, in bytes, of the packed, null-terminated path list.
    const APP_PATHS_MAX_LEN: usize = 256;

    fn to_padded_bytes(&self) -> [u8; AppHeader::APP_HEADER_SIZE] {
        let mut bytes = [0u8; AppHeader::APP_HEADER_SIZE];
        bytes[..size_of::<AppHeader>()].copy_from_slice(self.as_bytes());
        bytes
    }
}

/// Converts the ELF at `elf_path` into the app binary format Core loads:
/// prepends a fixed-size `AppHeader` (built from `package`'s
/// `[package.metadata.trezor]`, see [`crate::metadata`]) to the
/// architecture-specific payload -- the relocated ARMv8-M image from
/// [`crate::armv8m`] for a hardware build, or the raw ELF bytes as-is for an
/// x86-64 emulator build. Writes the result next to `elf_path` and returns
/// its path.
pub fn convert_elf_to_bin(
    elf_path: &Path,
    package: &Package,
    model: Option<Model>,
) -> Result<PathBuf> {
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
                TargetArch::Armv8m,
                arm_binary.to_bytes()?,
                arm_binary.ram_size(),
            )
        }
        object::Architecture::X86_64 => (TargetArch::LinuxX86_64, raw_elf, 0),
        object::Architecture::Aarch64 => (TargetArch::MacosAarch64, raw_elf, 0),
        arch => anyhow::bail!("Unsupported architecture: {:?}", arch),
    };

    let header = AppHeader {
        magic: U32::new(AppHeader::APP_HEADER_MAGIC),
        header_size: U32::new(AppHeader::APP_HEADER_SIZE as u32),
        id: pack_str(&metadata::app_identifier(package)?, "App identifier")?,
        app_name: pack_str(&metadata::app_name(package)?, "App name")?,
        vendor_name: pack_str(&metadata::vendor_name(package)?, "Vendor name")?,
        model: model.map_or([0; 4], |m| m.model_id_bytes()),
        version: pack_version(metadata::app_version(package))?,
        sdk_version: [0; 4],
        abi_version: 1,
        target_arch: target_arch.id(),
        app_ring: metadata::app_ring(package)?,
        reserved1: [0; 1],
        code_size: U32::new(code.len() as u32),
        chunk_hash: hash_payload(&code, AppHeader::CHUNK_SIZE),
        data_size: U32::new(data_size),
        chunk_size: U16::new(AppHeader::CHUNK_SIZE as u16),
        curves: pack_str_array(&metadata::curves(package)?, "curves")?,
        paths: pack_str_array(&metadata::paths(package)?, "paths")?,
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

/// Converts a semver version into the 4-byte `[major, minor, patch, 0]` header form.
fn pack_version(version: &Version) -> Result<[u8; 4]> {
    Ok([
        version
            .major
            .try_into()
            .context("Failed to convert major version to u8")?,
        version
            .minor
            .try_into()
            .context("Failed to convert minor version to u8")?,
        version
            .patch
            .try_into()
            .context("Failed to convert patch version to u8")?,
        0,
    ])
}

/// Packs a string into a fixed-size, zero-padded byte array.
fn pack_str<const MAX_LEN: usize>(string: &str, label: &str) -> Result<[u8; MAX_LEN]> {
    let bytes = string.as_bytes();

    ensure!(
        bytes.len() <= MAX_LEN,
        "{label} '{string}' is too long (max {MAX_LEN} bytes)"
    );

    let mut result = [0u8; MAX_LEN];
    result[..bytes.len()].copy_from_slice(bytes);

    Ok(result)
}

/// Packs a list of strings into a fixed-size byte array, each string
/// null-terminated and the remainder zero-padded.
fn pack_str_array<const MAX_LEN: usize>(strings: &[String], label: &str) -> Result<[u8; MAX_LEN]> {
    let mut result = [0u8; MAX_LEN];
    let mut offset = 0;

    for string in strings {
        let string_bytes = string.as_bytes();

        ensure!(
            offset + string_bytes.len() < MAX_LEN,
            "{label} are too long (max {MAX_LEN} bytes)"
        );

        result[offset..offset + string_bytes.len()].copy_from_slice(string_bytes);
        offset += string_bytes.len();
        result[offset] = 0; // Null terminator
        offset += 1;
    }

    Ok(result)
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
            hasher.update(prev_hash);
            hasher.update(chunk);
            hasher.finalize().into()
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sha256_of(chunk: &[u8], prev_hash: [u8; 32]) -> [u8; 32] {
        let mut hasher = sha2::Sha256::new();
        hasher.update(prev_hash);
        hasher.update(chunk);
        hasher.finalize().into()
    }

    fn strings(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn pack_str_zero_pads() {
        let packed: [u8; 8] = pack_str("abc", "App name").unwrap();
        assert_eq!(packed, *b"abc\0\0\0\0\0");
    }

    #[test]
    fn pack_str_exact_fit_is_allowed() {
        let packed: [u8; 3] = pack_str("abc", "App name").unwrap();
        assert_eq!(packed, *b"abc");
    }

    #[test]
    fn pack_str_rejects_too_long() {
        let err = pack_str::<2>("abc", "App name").unwrap_err();
        assert!(err.to_string().contains("App name 'abc' is too long"));
    }

    #[test]
    fn packs_strings_null_terminated_in_order() {
        let packed: [u8; 32] =
            pack_str_array(&strings(&["secp256k1", "ed25519"]), "curves").unwrap();

        assert_eq!(&packed[..10], b"secp256k1\0");
        assert_eq!(&packed[10..17], b"ed25519");
        assert_eq!(packed[17], 0);
        // Everything past the last terminator stays zero-padded.
        assert!(packed[18..].iter().all(|&b| b == 0));
    }

    #[test]
    fn empty_list_packs_to_all_zeros() {
        let packed: [u8; 8] = pack_str_array(&[], "curves").unwrap();
        assert_eq!(packed, [0u8; 8]);
    }

    #[test]
    fn rejects_when_total_length_exceeds_max_len() {
        // "secp256k1\0" is 10 bytes; MAX_LEN=9 can't fit it plus the terminator.
        let err = pack_str_array::<9>(&strings(&["secp256k1"]), "curves").unwrap_err();
        assert!(err.to_string().contains("too long"));
    }

    #[test]
    fn exact_fit_is_allowed() {
        // "ab\0" is exactly 3 bytes for MAX_LEN=3 -- the boundary must not
        // be off by one in either direction.
        let packed: [u8; 3] = pack_str_array(&strings(&["ab"]), "curves").unwrap();
        assert_eq!(packed, *b"ab\0");
    }

    #[test]
    fn version_bytes_layout() {
        let v = Version::new(1, 2, 3);
        assert_eq!(pack_version(&v).unwrap(), [1, 2, 3, 0]);
    }

    #[test]
    fn version_bytes_rejects_component_over_u8() {
        let v = Version::new(256, 0, 0);
        assert!(pack_version(&v).is_err());
    }

    #[test]
    fn empty_payload_hashes_to_zero() {
        // No chunks to fold over, so the fold's initial value comes through
        // unchanged -- this is the "chunk_hash" a zero-length app would get.
        assert_eq!(hash_payload(&[], 16), [0u8; 32]);
    }

    #[test]
    fn single_chunk_matches_sha256_of_chunk_plus_zero_hash() {
        let payload = b"hello world";
        let expected = sha256_of(payload, [0u8; 32]);
        assert_eq!(hash_payload(payload, payload.len()), expected);
    }

    #[test]
    fn chains_chunks_in_reverse_order() {
        // Two 4-byte chunks: the *last* chunk is hashed first (against the
        // zero hash), then the *first* chunk is hashed against that result
        // -- so the final hash commits to the whole payload, but each chunk
        // can be verified against the previous chunk's hash while loading,
        // in first-to-last order.
        let payload = b"abcdwxyz";
        let h_last = sha256_of(b"wxyz", [0u8; 32]);
        let h_first = sha256_of(b"abcd", h_last);
        assert_eq!(hash_payload(payload, 4), h_first);
    }

    #[test]
    fn uneven_final_chunk_is_hashed_as_is() {
        // 5 bytes with chunk_size=4 means chunks are [0..4] and [4..5]; the
        // trailing short chunk is still hashed on its own, not padded.
        let payload = b"abcde";
        let h_last = sha256_of(b"e", [0u8; 32]);
        let h_first = sha256_of(b"abcd", h_last);
        assert_eq!(hash_payload(payload, 4), h_first);
    }

    #[test]
    fn different_chunk_size_changes_the_hash() {
        let payload = b"abcdefgh";
        assert_ne!(hash_payload(payload, 4), hash_payload(payload, 8));
    }
}
