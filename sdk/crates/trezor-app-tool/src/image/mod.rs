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
    path::{Path, PathBuf},
};
use zerocopy::{U16, U32};

use crate::args::{Language, Model, TargetArch};

mod armv8m;
mod header;
mod metadata;

pub(crate) use header::{AppHeader, format_version};

impl TargetArch {
    /// Returns the architecture identifier stored in the app header.
    pub fn id(&self) -> u8 {
        match self {
            TargetArch::Armv8m => 0,
            TargetArch::LinuxX86_64 => 1,
            TargetArch::MacosAarch64 => 2,
        }
    }

    /// Returns the architecture with the given app-header identifier, the
    /// inverse of [`TargetArch::id`].
    pub fn from_id(id: u8) -> Option<Self> {
        match id {
            0 => Some(TargetArch::Armv8m),
            1 => Some(TargetArch::LinuxX86_64),
            2 => Some(TargetArch::MacosAarch64),
            _ => None,
        }
    }
}

/// Converts the ELF at `elf_path` into the app binary format Core loads:
/// prepends a fixed-size `AppHeader` (built from `package`'s
/// `[package.metadata.trezor]`, see [`crate::metadata`]) to the
/// architecture-specific payload -- the relocated ARMv8-M image from
/// [`crate::armv8m`] for a hardware build, or the raw ELF bytes as-is for an
/// x86-64 emulator build. `language` is recorded in the header as the
/// language the app was built for. Writes the result next to `elf_path` and returns
/// its path.
pub fn convert_elf_to_bin(
    elf_path: &Path,
    package: &Package,
    model: Option<Model>,
    language: Language,
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

    // The inbox is allocated out of the app's own heap at launch, so a
    // manifest that asks for an inbox larger than the heap it reserved can
    // never start. Catch it here rather than at load time on the device.
    let ipc_buffer_size = metadata::ipc_buffer_size(package)?;
    let heap_size = metadata::heap_size(package)?;
    ensure!(
        ipc_buffer_size <= heap_size,
        "IPC buffer size ({ipc_buffer_size} B) exceeds the app's heap size \
         ({heap_size} B); raise `heap-size` or lower `ipc-buffer-size` in \
         [package.metadata.trezor]"
    );

    let header = AppHeader {
        magic: U32::new(AppHeader::APP_HEADER_MAGIC),
        header_size: U32::new(AppHeader::APP_HEADER_SIZE as u32),
        id: pack_str(&metadata::app_identifier(package)?, "App identifier")?,
        app_name: pack_str(&metadata::app_name(package)?, "App name")?,
        vendor_name: pack_str(&metadata::vendor_name(package)?, "Vendor name")?,
        model: model.map_or([0; 4], |m| m.model_id_bytes()),
        version: pack_version(&metadata::app_version(package))?,
        sdk_version: pack_version(&metadata::sdk_version(package)?)?,
        abi_version: metadata::abi_version()?,
        target_arch: target_arch.id(),
        app_ring: metadata::app_ring(package)?,
        language: language as u8,
        code_size: U32::new(code.len() as u32),
        chunk_hash: hash_payload(&code, AppHeader::CHUNK_SIZE),
        data_size: U32::new(data_size),
        chunk_size: U16::new(AppHeader::CHUNK_SIZE as u16),
        curves: pack_str_array(&metadata::curves(package)?, "curves")?,
        paths: pack_str_array(&metadata::paths(package)?, "paths")?,
        reserved2: [0; 2],
        ipc_buffer_size: U32::new(ipc_buffer_size),
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

pub(crate) const EXT_APP: &str = "tapp";

/// Returns the path of the serialized app (`.tapp`) that [`crate::apptree`]
/// writes into `serialized_dir` for the app binary at `bin_path`.
pub fn serialized_app_path(bin_path: &Path, serialized_dir: &Path) -> Result<PathBuf> {
    let bytes = fs::read(bin_path)
        .with_context(|| format!("Failed to read the app binary {:?}", bin_path))?;
    let (header, _) = AppHeader::parse(&bytes)
        .with_context(|| format!("Failed to parse the app binary {:?}", bin_path))?;
    Ok(serialized_dir.join(serialized_app_relative_path(&header)?))
}

/// Returns the path of the serialized app with `header`, relative to the
/// serialized artifacts directory:
/// `<id>/<version>/<id>_<version>_sdk<major.minor>_<arch>_abi<abi>_<model>_<lang>.tapp`.
pub(crate) fn serialized_app_relative_path(header: &AppHeader) -> Result<PathBuf> {
    let id = header.id()?;
    let model = header.model()?;
    let version = format_version(&header.version());
    let sdk_version = format_version(&header.sdk_version()[..2]);

    let name = format!(
        "{id}_{version}_sdk{sdk_version}_{}_abi{}_{model}_{}.{EXT_APP}",
        header.target_arch()?.name(),
        header.abi_version(),
        header.language()?.name(),
    );

    Ok(Path::new(id).join(&version).join(name))
}

/// Converts one to four dot-separated numeric version components into the
/// 4-byte app-header form, padding omitted components with zeroes.
fn pack_version(version: &str) -> Result<[u8; 4]> {
    let mut packed = [0; 4];

    for (index, component) in version.split('.').enumerate() {
        ensure!(
            index < packed.len(),
            "Version '{version}' has more than 4 components"
        );
        ensure!(
            !component.is_empty(),
            "Version '{version}' has an empty component"
        );
        packed[index] = component.parse().with_context(|| {
            format!("Version '{version}' has an invalid component '{component}'")
        })?;
    }

    Ok(packed)
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
    hash_chain(payload, chunk_size)[0]
}

/// Returns every hash of the payload's hash chain, one more than there are
/// chunks. Entry `i` is the hash of chunk `i` chained with entry `i + 1`, and
/// the last entry, past the final chunk, is all zeroes. Entry 0 is the header's
/// `chunk_hash`; entry `i + 1` is the hash sent alongside chunk `i` when
/// loading, so Core can verify each chunk as it arrives.
pub(crate) fn hash_chain(payload: &[u8], chunk_size: usize) -> Vec<[u8; 32]> {
    let mut prev_hash = [0u8; 32];
    let mut hashes = vec![prev_hash];

    for chunk in payload.chunks(chunk_size).rev() {
        let mut hasher = sha2::Sha256::new();
        hasher.update(prev_hash);
        hasher.update(chunk);
        prev_hash = hasher.finalize().into();
        hashes.push(prev_hash);
    }

    hashes.reverse();
    hashes
}

#[cfg(test)]
mod tests {
    use super::*;
    use zerocopy::FromZeros;

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
        assert_eq!(pack_version("1.2.3").unwrap(), [1, 2, 3, 0]);
        assert_eq!(pack_version("0.1").unwrap(), [0, 1, 0, 0]);
        assert_eq!(pack_version("1.2.3.4").unwrap(), [1, 2, 3, 4]);
    }

    #[test]
    fn version_bytes_rejects_component_over_u8() {
        assert!(pack_version("256.0.0").is_err());
        assert!(pack_version("1.2.3.4.5").is_err());
    }

    #[test]
    fn empty_payload_hashes_to_zero() {
        // No chunks to hash, so the chain is just the zero hash -- this is
        // the "chunk_hash" a zero-length app would get.
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

    #[test]
    fn hash_chain_holds_every_link() {
        // Three chunks give four hashes: the chunk_hash, one per following
        // chunk, and the terminating zero hash.
        let payload = b"abcdefghij";
        let h2 = sha256_of(b"ij", [0u8; 32]);
        let h1 = sha256_of(b"efgh", h2);
        let h0 = sha256_of(b"abcd", h1);
        assert_eq!(hash_chain(payload, 4), vec![h0, h1, h2, [0u8; 32]]);
    }

    #[test]
    fn hash_chain_of_empty_payload_is_the_zero_hash() {
        assert_eq!(hash_chain(&[], 16), vec![[0u8; 32]]);
    }

    fn write_header(name: &str, model: Option<Model>, target_arch: TargetArch) -> PathBuf {
        let mut header = AppHeader::new_zeroed();
        header.magic = U32::new(AppHeader::APP_HEADER_MAGIC);
        header.header_size = U32::new(AppHeader::APP_HEADER_SIZE as u32);
        header.chunk_size = U16::new(AppHeader::CHUNK_SIZE as u16);
        header.id = pack_str("tron.trezor.com", "App id").unwrap();
        header.model = model.map_or([0; 4], Model::model_id_bytes);
        header.version = pack_version("0.1.0").unwrap();
        header.sdk_version = pack_version("0.1.2").unwrap();
        header.abi_version = 1;
        header.target_arch = target_arch.id();
        header.language = Language::CS as u8;

        let path = std::env::temp_dir().join(name);
        fs::write(&path, header.to_padded_bytes()).unwrap();
        path
    }

    #[test]
    fn serialized_app_path_matches_post_build_naming() {
        let bin = write_header(
            "serialized-path-t3w1.bin",
            Some(Model::T3W1),
            TargetArch::Armv8m,
        );
        let path = serialized_app_path(&bin, Path::new("serialized")).unwrap();
        assert_eq!(
            path,
            Path::new("serialized/tron.trezor.com/0.1.0.0")
                .join("tron.trezor.com_0.1.0.0_sdk0.1_armv8m_abi1_T3W1_cs.tapp")
        );
    }

    #[test]
    fn serialized_app_path_universal_emulator_app() {
        let bin = write_header("serialized-path-all.bin", None, TargetArch::LinuxX86_64);
        let path = serialized_app_path(&bin, Path::new("serialized")).unwrap();
        assert_eq!(
            path.file_name().unwrap(),
            "tron.trezor.com_0.1.0.0_sdk0.1_linux-x86_64_abi1__cs.tapp"
        );
    }
}
