//! Reads and validates an app's `[package.metadata.trezor]` fields from its
//! `Cargo.toml`.

use anyhow::{Context, Result, ensure};
use cargo_metadata::Package;
use cargo_metadata::semver::Version;

/// Retrieves the app version from the package metadata.
pub fn app_version(package: &Package) -> &Version {
    &package.version
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
