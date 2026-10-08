//! Reads and validates an app's `[package.metadata.trezor]` fields from its
//! `Cargo.toml`.

use anyhow::{Context, Result, ensure};
use cargo_metadata::{MetadataCommand, Package};

/// Upper bound on an app's IPC inbox, mirroring the kernel's
/// `IPC_MAX_BUFFER_SIZE` (`core/embed/sys/ipc/inc/sys/ipc.h`). `ipc_register`
/// refuses anything larger.
pub const IPC_BUFFER_MAX_SIZE: u64 = 64 * 1024;

/// Smallest inbox we accept. Anything below this cannot hold even a single
/// API reply plus framing, so it is always a mistake.
pub const IPC_BUFFER_MIN_SIZE: u64 = 256;

/// Inbox size used when an app does not declare `ipc-buffer-size` (or sets it
/// to 0).
///
/// Sized off the fixed API traffic, not off wire messages: the largest reply
/// Core sends back over IPC is the 111-byte xpub from
/// `CryptoV1::get_xpub`, and UI replies are a handful of bytes each. With the
/// 12-byte `ipc_queue_item_t` header that is ~128 bytes for the biggest single
/// message, so 1 KiB leaves 8x headroom for queued replies.
///
/// An app that receives host wire messages through the same inbox needs more
/// than this and must say so explicitly -- there is no way to guess how large
/// its protocol messages get.
pub const IPC_BUFFER_DEFAULT_SIZE: u64 = 1024;

/// Retrieves the app version from the package metadata.
pub fn app_version(package: &Package) -> String {
    package.version.to_string()
}

/// Retrieves the app identifier from the package metadata.
pub fn app_identifier(package: &Package) -> Result<String> {
    metadata_string(package, "id")
}

/// Retrieve the app name from the package metadata.
pub fn app_name(package: &Package) -> Result<String> {
    metadata_string(package, "name")
}

/// Retrieve the vendor name from the package metadata.
pub fn vendor_name(package: &Package) -> Result<String> {
    metadata_string(package, "vendor")
}

/// Retrieves the stack size from the package metadata
pub fn stack_size(package: &Package) -> Result<u32> {
    let stack_size = metadata_number(package, "stack-size")?;

    ensure!(
        stack_size <= 256 * 1024,
        "Stack size {} is too large (max 256kB)",
        stack_size
    );

    Ok(stack_size as u32)
}

/// Retrieve the heap size from the package metadata
pub fn heap_size(package: &Package) -> Result<u32> {
    let heap_size = metadata_number(package, "heap-size")?;

    ensure!(
        heap_size <= 256 * 1024,
        "Heap size {} is too large (max 256kB)",
        heap_size
    );

    Ok(heap_size as u32)
}

/// Retrieve the IPC inbox size, in bytes, from the package metadata.
///
/// The key is optional; a missing entry or an explicit 0 means "no opinion"
/// and yields [`IPC_BUFFER_DEFAULT_SIZE`].
///
/// The value must be a power of two. That is not an IPC requirement -- the
/// kernel queue is a plain byte ring -- but the inbox is allocated as
/// `[usize]`, so its byte size has to be a multiple of `size_of::<usize>()`,
/// which is 4 on the ARM target and 8 on the x86-64 emulator. Requiring a
/// power of two satisfies both with one rule instead of a target-dependent
/// alignment check.
pub fn ipc_buffer_size(package: &Package) -> Result<u32> {
    let size = match optional_metadata_number(package, "ipc-buffer-size")? {
        None | Some(0) => IPC_BUFFER_DEFAULT_SIZE,
        Some(size) => size,
    };

    ensure!(
        size >= IPC_BUFFER_MIN_SIZE,
        "IPC buffer size {} is too small (min {} bytes)",
        size,
        IPC_BUFFER_MIN_SIZE
    );

    ensure!(
        size <= IPC_BUFFER_MAX_SIZE,
        "IPC buffer size {} is too large (max {} bytes)",
        size,
        IPC_BUFFER_MAX_SIZE
    );

    ensure!(
        size.is_power_of_two(),
        "IPC buffer size {} must be a power of two",
        size
    );

    Ok(size as u32)
}

/// Retrieves the app ring from the package metadata
pub fn app_ring(package: &Package) -> Result<u8> {
    let ring = metadata_number(package, "app-ring")?;

    ensure!(
        ring <= 2,
        "App ring {} is invalid (must be 0, 1, or 2)",
        ring
    );

    Ok(ring as u8)
}

/// Retrieves the curves from the package metadata
/// (array of strings, e.g. ["secp256k1", "ed25519"])
pub fn curves(package: &Package) -> Result<Vec<String>> {
    metadata_string_array(package, "curves")
}

/// Retrieves the allowed paths from the package metadata
pub fn paths(package: &Package) -> Result<Vec<String>> {
    metadata_string_array(package, "paths")
}

/// Retrieves the SDK version of the `trezor-app-sdk` dependency
/// from the package metadata.
pub fn sdk_version(package: &Package) -> Result<String> {
    let sdk = dependency_package(package, "trezor-app-sdk")?;
    metadata_string(&sdk, "sdk-version")
}

/// Retrieves the ABI version used by the app.
pub fn abi_version() -> Result<u8> {
    std::env::var("TREZOR_APP_TOOLING_ABI_VERSION").map_or(Ok(1), |v| {
        v.parse::<u8>().context("Failed to parse ABI version")
    })
}

fn metadata_string(package: &Package, key: &str) -> Result<String> {
    let value = package
        .metadata
        .get("trezor")
        .and_then(|m| m.get(key))
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow::anyhow!("{} not found in Cargo.toml", key))?;

    Ok(value.to_string())
}

fn metadata_string_array(package: &Package, key: &str) -> Result<Vec<String>> {
    let values = package
        .metadata
        .get("trezor")
        .and_then(|m| m.get(key))
        .and_then(|v| v.as_array())
        .ok_or_else(|| anyhow::anyhow!("{} not found in Cargo.toml", key))?;

    values
        .iter()
        .map(|v| {
            v.as_str()
                .map(str::to_string)
                .ok_or_else(|| anyhow::anyhow!("{key} must be an array of strings"))
        })
        .collect()
}

/// Like [`metadata_number`], but returns `None` instead of failing when the
/// key is absent.
fn optional_metadata_number(package: &Package, key: &str) -> Result<Option<u64>> {
    if package
        .metadata
        .get("trezor")
        .and_then(|m| m.get(key))
        .is_none()
    {
        return Ok(None);
    }
    metadata_number(package, key).map(Some)
}

fn metadata_number(package: &Package, key: &str) -> Result<u64> {
    let value = package
        .metadata
        .get("trezor")
        .and_then(|m| m.get(key))
        .ok_or_else(|| anyhow::anyhow!("{} not found in Cargo.toml", key))?;

    if let Some(value) = value.as_u64() {
        return Ok(value);
    }

    value
        .as_str()
        .ok_or_else(|| anyhow::anyhow!("{} must be a number in Cargo.toml", key))?
        .parse::<u64>()
        .with_context(|| format!("Failed to parse {key}"))
}

/// Returns the [`Package`] of `package`'s dependency called `name`, so its
/// version and `[package.metadata]` can be read.
///
/// The `Package` values handled by this tool come from a `no_deps` metadata
/// query, which lists workspace members only, so the dependency graph is
/// resolved here for the package's manifest.
pub fn dependency_package(package: &Package, name: &str) -> Result<Package> {
    let dep = package
        .dependencies
        .iter()
        .find(|dep| dep.name == name)
        .ok_or_else(|| anyhow::anyhow!("Dependency {} not found in Cargo.toml", name))?;

    let metadata = MetadataCommand::new()
        .manifest_path(&package.manifest_path)
        .exec()
        .context("Failed to read cargo metadata")?;

    metadata
        .packages
        .into_iter()
        .find(|p| p.name == dep.name && dep.req.matches(&p.version))
        .ok_or_else(|| anyhow::anyhow!("Package {} not found in the dependency graph", name))
}
