extern crate alloc;

use alloc::string::String;
use alloc::vec;
use alloc::vec::Vec;
use core::{fmt, usize};

use trezor_app_sdk::Result;
use uluru::LRUCache;

use crate::common::{paths::path_is_hardened, safety_checks::is_strict};

/// Error types for keychain operations
// #[derive(Debug, Clone, PartialEq, Eq)]
// pub enum KeychainError {
//     ForbiddenKeyPath,
//     NonHardenedOnEd25519,
// }

// impl fmt::Display for KeychainError {
//     fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
//         match self {
//             KeychainError::ForbiddenKeyPath => f.write_str("Forbidden key path"),
//             KeychainError::NonHardenedOnEd25519 => {
//                 f.write_str("Non-hardened paths unsupported on Ed25519")
//             }
//         }
//     }
// }

/// Path schema for validation
pub trait PathSchema {
    fn matches(&self, path: &[u32]) -> bool;
}

/// Main keychain for hierarchical key derivation with caching
pub struct Keychain {
    seed: Vec<u8>,
    curve: String,
    // schemas: Vec<Box<dyn PathSchema>>,
    cache: LRUCache<Vec<u32>, 10>,
    root_fingerprint: Option<u32>,
}

impl Keychain {
    pub fn new(
        seed: Vec<u8>,
        curve: String,
        // schemas: Vec<Box<dyn PathSchema>>,
    ) -> Self {
        Self {
            seed,
            curve,
            // schemas,
            cache: LRUCache::new(),
            root_fingerprint: None,
        }
    }

    /// Verify that the path is allowed by schemas
    fn verify_path(&self, path: &[u32]) -> Result<()> {
        // Check for Ed25519 non-hardened paths
        if self.curve.contains("ed25519") && path_is_hardened(path) {
            // TODO
            // raise DataError("Non-hardened paths unsupported on Ed25519")
            return Err(trezor_app_sdk::Error::InvalidArgument);
        }

        // Skip schema validation if not in strict mode
        if !is_strict() {
            return Ok(());
        }

        // Check if path matches any schema
        if self.is_in_keychain(path) {
            return Ok(());
        }

        Err(trezor_app_sdk::Error::InvalidArgument)
    }

    /// Check if path matches any registered schema
    fn is_in_keychain(&self, path: &[u32]) -> bool {
        self.schemas.iter().any(|schema| schema.matches(path))
    }

    /// Derive with caching using a prefix
    fn derive_with_cache<F>(&mut self, prefix_len: usize, path: &[u32], new_root: F) -> N
    where
        F: FnOnce() -> N,
    {
        let prefix: Vec<u32> = path.iter().take(prefix_len).cloned().collect();

        // Try to get cached prefix node
        let mut root = if let Some(cached) = self.cache.get(&prefix) {
            cached
        } else {
            // Create new root and derive prefix
            let mut n = new_root();
            n.derive_path(&prefix);
            self.cache.insert(prefix.clone(), n.clone());
            n
        };

        // Derive remaining suffix
        let suffix: Vec<u32> = path.iter().skip(prefix_len).cloned().collect();
        root.derive_path(&suffix);
        root
    }

    /// Get root fingerprint (derives m/0' to obtain it)
    pub fn root_fingerprint<F>(&mut self, from_seed: F) -> u32
    where
        F: FnOnce(&[u8], &str) -> N,
    {
        if let Some(fp) = self.root_fingerprint {
            return fp;
        }

        // Derive m/0' to obtain root fingerprint
        let hardened_zero = vec![0 | PathUtils::HARDENED];
        let mut n =
            self.derive_with_cache(0, &hardened_zero, || from_seed(&self.seed, &self.curve));

        let fp = n.fingerprint();
        self.root_fingerprint = Some(fp);
        fp
    }

    /// Derive a BIP-32 node from a path
    pub fn derive(&mut self, path: &[u32]) -> Result<N> {
        self.verify_path(path)?;
        // Ok(self.derive_with_cache(3, path, || from_seed(&self.seed, &self.curve)))
        Err(trezor_app_sdk::Error::InvalidArgument)
    }
}

/// Get a keychain instance (placeholder - implement with real seed retrieval)
pub fn get_keychain(
    curve: &str,
    // schemas: Vec<Box<dyn PathSchema>>,
) -> Result<Keychain> {
    // TODO: Implement real seed retrieval
    let seed = get_seed()?;
    Ok(Keychain::new(seed, curve.into()))
}

/// Placeholder for seed retrieval - implement with actual secure storage
fn get_seed() -> Result<Vec<u8>> {
    // TODO: Implement secure seed retrieval
    Err(trezor_app_sdk::Error::InvalidArgument)
}
