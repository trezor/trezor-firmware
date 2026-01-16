pub const CREDENTIAL_PRIVKEY_LENGTH: usize = 32;

pub struct FoundCredential<'a> {
    pub local_static_privkey: &'a [u8; CREDENTIAL_PRIVKEY_LENGTH],
    pub auth_credential: &'a [u8],
}

/// Host-side credential store.
/// Basically a set of (`remote_static_pubkey`, `local_static_privkey`, `auth_credential`).
pub trait CredentialStore {
    /// Find a record such that `remote_static_pubkey` satisfies
    /// `masked_static_pubkey == X25519(SHA-256(remote_static_pubkey || ephemeral_pubkey), remote_static_pubkey)`.
    /// If found, write `local_static_privkey` and `auth_credential` to `dest` and return the written subslices.
    fn lookup<'a>(
        &self,
        ephemeral_pubkey: &[u8],
        masked_static_pubkey: &[u8],
        dest: &'a mut [u8],
    ) -> Option<FoundCredential<'a>>;
}

/// Never finds a matching credential.
pub struct NullCredentialStore;

impl CredentialStore for NullCredentialStore {
    fn lookup<'a>(
        &self,
        _ephemeral: &[u8],
        _masked_static: &[u8],
        _dest: &'a mut [u8],
    ) -> Option<FoundCredential<'a>> {
        None
    }
}
