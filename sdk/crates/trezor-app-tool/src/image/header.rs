//! The fixed-size header at the beginning of every app image.

use anyhow::{Context, Result, anyhow, ensure};
use clap::ValueEnum;
use std::mem::size_of;
use zerocopy::{FromBytes, IntoBytes, LittleEndian, U16, U32};
use zerocopy_derive::{FromBytes, Immutable, IntoBytes};

use crate::args::{Language, TargetArch};

/// The app header is a fixed-size structure at the beginning of the application image
/// containing metadata about the app, such as segment sizes and addresses padded
/// with zeroes to ensure it is exactly APP_HEADER_SIZE bytes in size.
#[repr(C)]
#[derive(IntoBytes, FromBytes, Immutable, Debug)]
pub(crate) struct AppHeader {
    /// Magic number to identify the app binary format
    pub(super) magic: U32<LittleEndian>,
    /// Header size in bytes (contains AppHeader::APP_HEADER_SIZE)
    pub(super) header_size: U32<LittleEndian>,
    /// Unique identifier of the app (utf-8 encoded, zero-padded)
    pub(super) id: [u8; AppHeader::APP_ID_MAX_LEN],
    /// App name (utf-8 encoded, zero-padded)
    pub(super) app_name: [u8; AppHeader::APP_NAME_MAX_LEN],
    /// Vendor name (utf-8 encoded, zero-padded)
    pub(super) vendor_name: [u8; AppHeader::APP_VENDOR_MAX_LEN],
    /// Target model identifier (or zeroed for universal apps)
    pub(super) model: [u8; 4],
    /// App version in the format major.minor.patch.build, each as a byte
    /// For example, version 1.2.3 would be represented as [1, 2, 3, 0]
    pub(super) version: [u8; 4],
    /// SDK version that the app was built against
    pub(super) sdk_version: [u8; 4],
    /// ABI version that the app was built against
    pub(super) abi_version: u8,
    /// Target architecture of the binary payload (e.g., ARMV8M, X86_64)
    pub(super) target_arch: u8,
    /// Application privilege ring
    pub(super) app_ring: u8,
    /// Application language
    pub(super) language: u8,
    /// Size of binary payload (code + init and relocation data)
    pub(super) code_size: U32<LittleEndian>,
    /// Size of RAM required by the app
    /// (includes stack, heap, and static data)
    pub(super) data_size: U32<LittleEndian>,
    /// Hash of the first payload chunk
    pub(super) chunk_hash: [u8; 32],
    /// Size of each chunk of the binary payload in bytes
    pub(super) chunk_size: U16<LittleEndian>,
    /// Reserved field for runtime purposes (zeroed)
    pub(super) reserved2: [u8; 2],
    /// Curves used for the app (e.g., secp256k1, ed25519)
    /// (utf-8 encoded, zero-padded)
    pub(super) curves: [u8; AppHeader::APP_CURVES_MAX_LEN],
    /// Allowed BIP32 path prefixes
    /// Each path is a null-terminated string, and the array
    /// is zero-padded to a fixed size.
    pub(super) paths: [u8; AppHeader::APP_PATHS_MAX_LEN],
    /// Size, in bytes, of the IPC inbox Core registers for this app at
    /// launch. Always resolved here -- a 0 in the manifest is replaced by
    /// `metadata::IPC_BUFFER_DEFAULT_SIZE`, so the header never carries 0.
    pub(super) ipc_buffer_size: U32<LittleEndian>,
    // TODO logo
}

impl AppHeader {
    /// Fixed size of the app header in bytes.
    pub(super) const APP_HEADER_SIZE: usize = 0x200;
    /// Magic number used to identify the app binary format in the header.
    pub(super) const APP_HEADER_MAGIC: u32 = 0x415A5254; // TRZA
    /// Chunk size used for hashing the payload in bytes.
    pub(super) const CHUNK_SIZE: usize = 2048;
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

    /// Splits an app image into its parsed header and the payload that
    /// follows it. The payload starts at `header_size`, past the zero
    /// padding, not right after the struct.
    pub(crate) fn parse(image: &[u8]) -> Result<(Self, &[u8])> {
        let (header, _) = AppHeader::read_from_prefix(image)
            .map_err(|_| anyhow!("App image is too short to contain a header"))?;
        ensure!(
            header.magic.get() == AppHeader::APP_HEADER_MAGIC,
            "App image has an invalid header magic"
        );
        let header_size = header.header_size.get() as usize;
        ensure!(
            (size_of::<AppHeader>()..=image.len()).contains(&header_size),
            "App image has an invalid header size {header_size}"
        );
        ensure!(
            header.chunk_size.get() > 0,
            "App image has a zero chunk size"
        );
        Ok((header, &image[header_size..]))
    }

    pub(crate) fn id(&self) -> Result<&str> {
        unpack_str(&self.id, "App id")
    }

    pub(crate) fn model(&self) -> Result<&str> {
        unpack_str(&self.model, "Model")
    }

    pub(crate) fn version(&self) -> [u8; 4] {
        self.version
    }

    pub(crate) fn sdk_version(&self) -> [u8; 4] {
        self.sdk_version
    }

    pub(crate) fn abi_version(&self) -> u8 {
        self.abi_version
    }

    pub(crate) fn target_arch(&self) -> Result<TargetArch> {
        TargetArch::from_id(self.target_arch)
            .with_context(|| format!("Unknown target architecture {}", self.target_arch))
    }

    pub(crate) fn language(&self) -> Result<Language> {
        Language::value_variants()
            .iter()
            .copied()
            .find(|&language| language as u8 == self.language)
            .with_context(|| format!("Unknown language {}", self.language))
    }

    pub(super) fn to_padded_bytes(&self) -> [u8; AppHeader::APP_HEADER_SIZE] {
        let mut bytes = [0u8; AppHeader::APP_HEADER_SIZE];
        bytes[..size_of::<AppHeader>()].copy_from_slice(self.as_bytes());
        bytes
    }
}

/// Formats packed version components as a dot-separated string.
pub(crate) fn format_version(version: &[u8]) -> String {
    version
        .iter()
        .map(u8::to_string)
        .collect::<Vec<_>>()
        .join(".")
}

/// Decodes a zero-padded utf-8 string from the app header.
fn unpack_str<'a>(bytes: &'a [u8], label: &str) -> Result<&'a str> {
    std::str::from_utf8(bytes)
        .with_context(|| format!("{label} is not valid utf-8"))
        .map(|string| string.trim_end_matches('\0'))
}

#[cfg(test)]
mod tests {
    use super::*;
    use zerocopy::FromZeros;

    fn image(header: &AppHeader, payload: &[u8]) -> Vec<u8> {
        [&header.to_padded_bytes()[..], payload].concat()
    }

    fn valid_header() -> AppHeader {
        let mut header = AppHeader::new_zeroed();
        header.magic = U32::new(AppHeader::APP_HEADER_MAGIC);
        header.header_size = U32::new(AppHeader::APP_HEADER_SIZE as u32);
        header.chunk_size = U16::new(AppHeader::CHUNK_SIZE as u16);
        header
    }

    #[test]
    fn parse_splits_payload_after_padding() {
        let image = image(&valid_header(), b"payload");
        let (_, payload) = AppHeader::parse(&image).unwrap();
        assert_eq!(payload, b"payload");
    }

    #[test]
    fn parse_rejects_short_image() {
        let image = image(&valid_header(), b"");
        assert!(AppHeader::parse(&image[..size_of::<AppHeader>() - 1]).is_err());
    }

    #[test]
    fn parse_rejects_bad_magic() {
        let mut header = valid_header();
        header.magic = U32::new(0);
        assert!(AppHeader::parse(&image(&header, b"")).is_err());
    }

    #[test]
    fn parse_rejects_zero_chunk_size() {
        let mut header = valid_header();
        header.chunk_size = U16::new(0);
        assert!(AppHeader::parse(&image(&header, b"")).is_err());
    }

    #[test]
    fn parse_rejects_header_size_out_of_range() {
        let mut header = valid_header();
        header.header_size = U32::new(size_of::<AppHeader>() as u32 - 1);
        assert!(AppHeader::parse(&image(&header, b"")).is_err());

        header.header_size = U32::new(AppHeader::APP_HEADER_SIZE as u32 + 1);
        assert!(AppHeader::parse(&image(&header, b"")).is_err());
    }

    #[test]
    fn unpack_str_trims_padding() {
        assert_eq!(unpack_str(b"abc\0\0\0", "App id").unwrap(), "abc");
        assert_eq!(unpack_str(b"\0\0\0\0", "Model").unwrap(), "");
    }

    #[test]
    fn unknown_enum_ids_are_rejected() {
        let mut header = valid_header();
        header.target_arch = 0xff;
        header.language = 0xff;
        assert!(header.target_arch().is_err());
        assert!(header.language().is_err());
    }

    #[test]
    fn version_formatting() {
        assert_eq!(format_version(&[0, 1, 0, 0]), "0.1.0.0");
        assert_eq!(format_version(&[0, 1]), "0.1");
    }
}
