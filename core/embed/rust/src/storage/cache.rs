use core::ops::Deref;

use spin::{Mutex, MutexGuard};
use zeroize::Zeroizing;

use crate::{lru::LruCache, trezorhal::random};

pub enum CacheError {
    InvalidSessionId,
    InvalidValue,
}

pub struct Cache {
    sessions: LruCache<SessionCache, 10>,
    active_id: Option<SessionId>,
}

impl Cache {
    pub const fn new() -> Self {
        Self {
            sessions: LruCache::new(),
            active_id: None,
        }
    }

    pub fn global() -> MutexGuard<'static, Self> {
        static GLOBAL_CACHE: Mutex<Cache> = Mutex::new(Cache::new());

        GLOBAL_CACHE.lock()
    }

    pub fn start_session(&mut self, received_session_id_bytes: Option<&[u8]>) -> SessionId {
        // If we have received a session ID, take a look to the cache and return an ID
        // of existing entry.
        let received_session_id =
            received_session_id_bytes.and_then(|bytes| SessionId::try_from(bytes).ok());
        if let Some(received_id) = received_session_id {
            if self.sessions.find(|s| s.id == Some(received_id)).is_some() {
                return received_id;
            }
        }
        // Either we haven't received an ID, or the entry doesn't exist (because of
        // previous eviction). Create a new session.
        let id = SessionId::random();
        self.sessions.insert(SessionCache::new(id));
        self.active_id = Some(id);
        id
    }

    pub fn end_session(&mut self) {
        if let Some(active_id) = self.active_id {
            if let Some(active_session) = self.sessions.find(|s| s.id == Some(active_id)) {
                active_session.clear();
            }
            self.active_id = None;
        }
    }

    pub fn has_active_session(&self) -> bool {
        self.active_id.is_some()
    }
}

pub struct SessionCache {
    id: Option<SessionId>,
    fields: Option<SessionFields>,
}

impl SessionCache {
    fn new(id: SessionId) -> Self {
        Self {
            id: Some(id),
            fields: Some(SessionFields::default()),
        }
    }

    fn clear(&mut self) {
        self.id = None;
        self.fields = None;
    }
}

#[derive(Copy, Clone, Eq, PartialEq)]
pub struct SessionId([u8; Self::LENGTH]);

impl SessionId {
    const LENGTH: usize = 32;

    fn random() -> Self {
        let mut id = [0; Self::LENGTH];
        random::bytes(&mut id);
        Self(id)
    }
}

impl Deref for SessionId {
    type Target = [u8; Self::LENGTH];

    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl TryFrom<&[u8]> for SessionId {
    type Error = CacheError;

    fn try_from(value: &[u8]) -> Result<Self, Self::Error> {
        Ok(Self(
            value
                .try_into()
                .map_err(|_| Self::Error::InvalidSessionId)?,
        ))
    }
}

#[derive(Default)]
struct SessionFields {
    seed: Field<64>,
    auth_type: Field<2>,
    auth_data: Field<128>,
    nonce: Field<32>,

    #[cfg(not(feature = "bitcoin_only"))]
    derive_cardano: Field<1>,
    #[cfg(not(feature = "bitcoin_only"))]
    cardano_icarus_secret: Field<96>,
    #[cfg(not(feature = "bitcoin_only"))]
    cardano_icarus_trezor_secret: Field<96>,
    #[cfg(not(feature = "bitcoin_only"))]
    monero_live_refresh: Field<1>,
}

#[derive(Default)]
struct Field<const N: usize> {
    data: Option<Zeroizing<[u8; N]>>,
}

impl<const N: usize> Field<N> {
    fn set(&mut self, value: &[u8]) -> Result<(), CacheError> {
        self.data = Some(Zeroizing::new(
            value.try_into().map_err(|_| CacheError::InvalidValue)?,
        ));
        Ok(())
    }

    fn unset(&mut self) {
        self.data = None;
    }
}
