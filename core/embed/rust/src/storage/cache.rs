use core::ops::Deref;

use spin::{Mutex, MutexGuard};
use zeroize::{Zeroize, Zeroizing};

use crate::{lru::LruCache, trezorhal::random};

const MAX_SESSION_COUNT: usize = 10;
const SESSIONLESS_FLAG: usize = 0x100;

/// Generate cache tables objects.
///
/// Each field is specified as
/// `FIELD_NAME(length)`. Fields in the `altcoin` section will only be generated
/// for non-bitcoin-only build.
///
/// Example:
/// ```
/// cache_tables! {
///    some_kind_of_cache {
///       APP_COMMON_THING(32),
///       APP_BITCOIN_COINS(1)
///    } altcoin {
///       APP_ETHEREUM_THING(32)
///   }
/// }
/// ```
/// will generate the following:
/// ```
/// mod some_kind_of_cache {
///     pub enum Enum {
///         APP_COMMON_THING,
///         APP_BITCOIN_COINS,
///         APP_ETHEREUM_THING,
///     }
///
///     pub struct Table {
///         APP_COMMON_THING: Field<32>,
///         APP_BITCOIN_COINS: Field<1>,
///         APP_ETHEREUM_THING: Field<32>,
///     }
///
///     pub fn get_key(key: usize) -> Result<Enum, CacheError> { ... }
///
///     impl Table {
///        pub const fn new() -> Self { ... }
///        pub fn get(&self, key: Enum) -> Option<&[u8]> { ... }
///        pub fn set(&mut self, key: Enum, value: &[u8]) -> Result<(), CacheError> { ... }
///        pub fn unset(&mut self, key: Enum) { ... }
///        pub fn clear(&mut self) { ... }
///     }
/// }
/// ```
macro_rules! cache_tables {
    () => {};
    (
        $type_name:ident {
        $($entry:ident($length:expr)),*
        } $(altcoin {
        $($bo_entry:ident($bo_length:expr)),+
        })?;
        $($tail:tt)*
    ) => {
        mod $type_name {
            use super::{Field, CacheError};
            use num_traits::FromPrimitive;
            use zeroize::{Zeroize, ZeroizeOnDrop};

            #[allow(non_camel_case_types)]
            #[derive(Copy, Clone, Debug, PartialEq, Eq, FromPrimitive)]
            pub enum Enum {
                $($entry,)*
                $($(
                    #[cfg(not(feature = "bitcoin_only"))]
                    $bo_entry,
                )+)?
            }

            pub fn get_key(value: usize) -> Result<Enum, CacheError> {
                FromPrimitive::from_usize(value).ok_or(CacheError::InvalidKey)
            }

            #[allow(non_snake_case)]
            #[derive(Zeroize, ZeroizeOnDrop)]
            pub struct Table {
                $($entry: Field<$length>,)*
                $($(
                    #[cfg(not(feature = "bitcoin_only"))]
                    $bo_entry: Field<$bo_length>,
                )+)?
            }

            impl Table {
                pub const fn new() -> Self {
                    Self {
                        $($entry: Field::new(),)*
                        $($(
                            #[cfg(not(feature = "bitcoin_only"))]
                            $bo_entry: Field::new(),
                        )+)?
                    }
                }

                pub fn get(&self, key: Enum) -> Option<&[u8]> {
                    match key {
                        $(Enum::$entry => self.$entry.get(),)*
                        $($(
                            #[cfg(not(feature = "bitcoin_only"))]
                            Enum::$bo_entry => self.$bo_entry.get(),
                        )+)?
                    }
                }

                pub fn set(&mut self, key: Enum, value: &[u8]) -> Result<(), CacheError> {
                    match key {
                        $(Enum::$entry => self.$entry.set(value),)*
                        $($(
                            #[cfg(not(feature = "bitcoin_only"))]
                            Enum::$bo_entry => self.$bo_entry.set(value),
                        )+)?
                    }
                }

                pub fn unset(&mut self, key: Enum) {
                    match key {
                        $(Enum::$entry => self.$entry.unset(),)*
                        $($(
                            #[cfg(not(feature = "bitcoin_only"))]
                            Enum::$bo_entry => self.$bo_entry.unset(),
                        )+)?
                    }
                }

                pub fn clear(&mut self) {
                    $(self.$entry.unset();)*
                    $($(
                        #[cfg(not(feature = "bitcoin_only"))]
                        self.$bo_entry.unset();
                    )+)?
                }
            }
        }

        cache_tables! { $($tail)* }
    };
}

cache_tables! {
    session_cache {
        APP_COMMON_SEED(64),
        APP_COMMON_AUTH_TYPE(2),
        APP_COMMON_AUTH_DATA(128),
        APP_COMMON_NONCE(32)
    } altcoin {
        APP_COMMON_DERIVE_CARDANO(1),
        APP_CARDANO_ICARUS_SECRET(96),
        APP_CARDANO_ICARUS_TREZOR_SECRET(96),
        APP_MONERO_LIVE_REFRESH(1)
    };

    sessionless_cache {
        APP_COMMON_SEED_WITHOUT_PASSPHRASE(64),
        APP_COMMON_SAFETY_CHECKS_TEMPORARY(1),
        APP_COMMON_REQUEST_PIN_LAST_UNLOCK(4)
    };
}

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum CacheError {
    NoActiveSession,
    InvalidSessionId,
    InvalidValue,
    InvalidKey,
}

struct Cache {
    sessions: LruCache<SessionCache, MAX_SESSION_COUNT>,
    sessionless: sessionless_cache::Table,
    active_id: Option<SessionId>,
}

impl Cache {
    pub const fn new() -> Self {
        Self {
            sessions: LruCache::new(),
            sessionless: sessionless_cache::Table::new(),
            active_id: None,
        }
    }

    pub fn global() -> MutexGuard<'static, Self> {
        static GLOBAL_CACHE: Mutex<Cache> = Mutex::new(Cache::new());

        GLOBAL_CACHE.lock()
    }

    pub fn reset(&mut self) {
        self.active_id = None;
        self.sessionless.clear();
        self.sessions.reset();
    }

    pub fn start_session(&mut self, received_session_id_bytes: Option<&[u8]>) -> SessionId {
        // If we have received a session ID, take a look to the cache and return an ID
        // of existing entry.
        let received_id =
            received_session_id_bytes.and_then(|bytes| SessionId::try_from(bytes).ok());
        if let Some(received_id) = received_id {
            if self.sessions.find_first(&|s| s.id == received_id).is_some() {
                self.active_id = Some(received_id);
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
            self.sessions.drop_first(&|s| s.id == active_id);
            self.active_id = None;
        }
    }

    pub fn active_session(&mut self) -> Option<&mut SessionCache> {
        self.active_id
            .and_then(|id| self.sessions.find_first(&|s| s.id == id))
    }

    pub fn get(&mut self, key: usize) -> Result<Option<&[u8]>, CacheError> {
        if key & SESSIONLESS_FLAG == SESSIONLESS_FLAG {
            let key = sessionless_cache::get_key(key & !SESSIONLESS_FLAG)?;
            Ok(self.sessionless.get(key))
        } else if let Some(active_session) = self.active_session() {
            let key = session_cache::get_key(key)?;
            Ok(active_session.table.get(key))
        } else {
            Err(CacheError::NoActiveSession)
        }
    }

    pub fn set(&mut self, key: usize, value: &[u8]) -> Result<(), CacheError> {
        if key & SESSIONLESS_FLAG == SESSIONLESS_FLAG {
            let key = sessionless_cache::get_key(key & !SESSIONLESS_FLAG)?;
            self.sessionless.set(key, value)
        } else if let Some(active_session) = self.active_session() {
            let key = session_cache::get_key(key)?;
            active_session.table.set(key, value)
        } else {
            Err(CacheError::NoActiveSession)
        }
    }

    pub fn unset(&mut self, key: usize) -> Result<(), CacheError> {
        if key & SESSIONLESS_FLAG == SESSIONLESS_FLAG {
            let key = sessionless_cache::get_key(key & !SESSIONLESS_FLAG)?;
            self.sessionless.unset(key);
            Ok(())
        } else if let Some(active_session) = self.active_session() {
            let key = session_cache::get_key(key)?;
            active_session.table.unset(key);
            Ok(())
        } else {
            Err(CacheError::NoActiveSession)
        }
    }
}

pub struct SessionCache {
    id: SessionId,
    table: session_cache::Table,
}

impl SessionCache {
    fn new(id: SessionId) -> Self {
        Self {
            id,
            table: session_cache::Table::new(),
        }
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

#[derive(Default, Zeroize)]
struct Field<const N: usize> {
    data: Option<Zeroizing<[u8; N]>>,
    length: u16,
}

impl<const N: usize> Field<N> {
    pub const fn new() -> Self {
        Self {
            data: None,
            length: 0,
        }
    }

    fn set(&mut self, value: &[u8]) -> Result<(), CacheError> {
        if value.len() > N {
            return Err(CacheError::InvalidValue);
        }
        let mut content = [0; N];
        content[..value.len()].copy_from_slice(value);
        self.data = Some(Zeroizing::new(content));
        self.length = value.len() as u16;
        Ok(())
    }

    fn get(&self) -> Option<&[u8]> {
        self.data.as_ref().map(|d| &d[..self.length as usize])
    }

    fn unset(&mut self) {
        self.data = None;
        self.length = 0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    cache_tables! {
        test_cache_table {
            FOO(10),
            BAR(1),
            QUUX(0)
        };
    }

    #[test]
    fn test_table_enum() {
        let foo = test_cache_table::Enum::FOO as usize;
        assert_eq!(
            test_cache_table::get_key(foo),
            Ok(test_cache_table::Enum::FOO)
        );
        assert_eq!(test_cache_table::get_key(1000), Err(CacheError::InvalidKey));
    }

    #[test]
    fn test_field_get_set() {
        let mut field = Field::<10>::new();
        assert_eq!(field.get(), None);
        let arr10 = [1u8, 2, 3, 4, 5, 6, 7, 8, 9, 10];
        assert_eq!(field.set(&arr10), Ok(()));
        assert_eq!(field.get(), Some(&arr10[..]));

        let arr3 = [1u8, 2, 3];
        assert_eq!(field.set(&arr3), Ok(()));
        assert_eq!(field.get(), Some(&arr3[..]));

        let arr11 = [1u8; 11];
        assert_eq!(field.set(&arr11), Err(CacheError::InvalidValue));

        field.unset();
        assert_eq!(field.get(), None);

        let mut field0 = Field::<0>::new();
        assert_eq!(field0.get(), None);
        assert_eq!(field0.set(&[]), Ok(()));
        assert_eq!(field0.get(), Some(&[][..]));
    }

    #[test]
    fn test_table_get_set() {
        let mut table = test_cache_table::Table::new();
        assert_eq!(table.get(test_cache_table::Enum::FOO), None);

        let arr10 = [1u8, 2, 3, 4, 5, 6, 7, 8, 9, 10];
        assert_eq!(table.set(test_cache_table::Enum::FOO, &arr10), Ok(()));
        assert_eq!(table.get(test_cache_table::Enum::FOO), Some(&arr10[..]));

        assert_eq!(table.get(test_cache_table::Enum::BAR), None);
        let arr1 = [1u8];
        assert_eq!(table.set(test_cache_table::Enum::BAR, &arr1), Ok(()));
        assert_eq!(table.get(test_cache_table::Enum::BAR), Some(&arr1[..]));
        assert_eq!(table.get(test_cache_table::Enum::FOO), Some(&arr10[..]));

        table.unset(test_cache_table::Enum::FOO);
        assert_eq!(table.get(test_cache_table::Enum::FOO), None);
        assert_eq!(table.get(test_cache_table::Enum::BAR), Some(&arr1[..]));

        table.clear();
        assert_eq!(table.get(test_cache_table::Enum::FOO), None);
        assert_eq!(table.get(test_cache_table::Enum::BAR), None);
    }
}
