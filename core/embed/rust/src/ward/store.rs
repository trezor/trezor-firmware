//! WARD offline store.
//!
//! Each record occupies one slot, i.e. one protected storage key in the
//! `APP_WARD` namespace, and is only ever accessible from its own scope (a
//! passphrase wallet and an app).
//!
//! Record layout:
//!
//! ```text
//! version: u8 | wallet_id[..8] | app_len: u8 | app | key_len: u16 LE | key | value
//! ```
//!
//! The first four fields form the header, the rest is the body of version 0.
//! The app identifier is an opaque byte string, scopes match only if their
//! app identifiers are equal.
//!
//! Records that are not of the current scope, not of version 0, or cannot be
//! parsed are never returned, written or deleted, they only count towards the
//! capacity limits. Nothing is ever evicted.

use super::error::Error;
use crate::io::{self, InputStream};
use crate::trezorhal::storage;

/// Storage namespace of the records.
const APP_WARD: u16 = 0x05;

/// Number of slots, i.e. the maximum number of records.
pub const MAX_RECORDS: u8 = 32;
/// Maximum total length of all records.
pub const MAX_TOTAL_BYTES: usize = 8192;
/// Maximum length of a single record, including its header.
pub const MAX_RECORD_LEN: usize = 2560;

/// Length of the wallet id.
const WALLET_ID_LEN: usize = 32;
/// Length of the wallet id prefix stored in the record header. Only a prefix
/// is stored to save space, 64 bits still make a collision between the
/// passphrase wallets of a device negligible.
const STORED_WALLET_ID_LEN: usize = 8;
/// Maximum length of the app identifier.
const MAX_APP_LEN: usize = u8::MAX as usize;

const VERSION: u8 = 0;

const _: () = assert!(MAX_RECORD_LEN <= u16::MAX as usize);
const _: () = assert!(STORED_WALLET_ID_LEN <= WALLET_ID_LEN);

fn appkey(slot: u8) -> u16 {
    (APP_WARD << 8) | u16::from(slot)
}

/// Identifier of a passphrase wallet.
pub type WalletId = [u8; WALLET_ID_LEN];

/// A passphrase wallet and an app.
#[derive(Clone, Copy, PartialEq)]
pub struct Scope<'a> {
    wallet_id: &'a [u8; STORED_WALLET_ID_LEN],
    app: &'a [u8],
}

impl<'a> Scope<'a> {
    pub fn new(wallet_id: &'a WalletId, app: &'a [u8]) -> Result<Self, Error> {
        if app.len() > MAX_APP_LEN {
            return Err(Error::InvalidScope);
        }
        Ok(Self {
            wallet_id: unwrap!(wallet_id.first_chunk()),
            app,
        })
    }
}

/// A version 0 record.
pub struct Record<'a> {
    pub scope: Scope<'a>,
    pub key: &'a [u8],
    pub value: &'a [u8],
}

impl<'a> Record<'a> {
    /// Decode a well-formed version 0 record of any scope.
    fn decode(bytes: &'a [u8]) -> Result<Self, io::Error> {
        let mut stream = InputStream::new(bytes);
        // header
        let version = stream.read_byte()?;
        let wallet_id = stream.read(STORED_WALLET_ID_LEN)?;
        let app_len = stream.read_byte()?;
        let app = stream.read(usize::from(app_len))?;
        if version != VERSION {
            return Err(io::Error::OutOfRange);
        }
        // version 0 body
        let key_len = stream.read_u16_le()?;
        let key = stream.read(usize::from(key_len))?;
        Ok(Self {
            scope: Scope {
                wallet_id: unwrap!(wallet_id.try_into()),
                app,
            },
            key,
            value: stream.rest(),
        })
    }

    fn len(&self) -> usize {
        1 + STORED_WALLET_ID_LEN + 1 + self.scope.app.len() + 2 + self.key.len() + self.value.len()
    }

    /// Encode the record into `buf`.
    fn encode(&self, buf: &mut heapless::VecView<u8>) -> Result<(), Error> {
        let app_len = u8::try_from(self.scope.app.len()).map_err(|_| Error::InvalidScope)?;
        let key_len = u16::try_from(self.key.len()).map_err(|_| Error::TooLarge)?;
        buf.clear();
        [
            &[VERSION][..],
            self.scope.wallet_id,
            &[app_len],
            self.scope.app,
            &key_len.to_le_bytes(),
            self.key,
            self.value,
        ]
        .into_iter()
        .try_for_each(|part| buf.extend_from_slice(part))
        .map_err(|_| Error::TooLarge)
    }
}

/// Buffer holding a record loaded from the storage.
pub type Buffer = heapless::Vec<u8, MAX_RECORD_LEN>;

/// A slot, as seen from a scope.
enum Slot<'a> {
    Empty,
    /// Holds a record of the given length that is not accessible from the
    /// scope: of another scope or version, malformed, or too large to load.
    Other(usize),
    /// Holds a version 0 record of the scope.
    Own(Record<'a>),
}

/// Access to the records of a scope. Operations returning record data borrow
/// it from a buffer provided by the caller.
pub struct Store<'a> {
    scope: Scope<'a>,
}

impl<'a> Store<'a> {
    /// The lock is only checked here, so the store must not be kept while the
    /// storage can be locked.
    pub fn new(scope: Scope<'a>) -> Result<Self, Error> {
        // A locked storage cannot be read and would look empty.
        if !storage::is_unlocked() {
            return Err(Error::Locked);
        }
        Ok(Self { scope })
    }

    /// Load `slot` into `buf`.
    fn load<'b>(&self, slot: u8, buf: &'b mut Buffer) -> Result<Slot<'b>, Error> {
        buf.clear();
        let Ok(len) = storage::get_length(appkey(slot)) else {
            return Ok(Slot::Empty);
        };
        if buf.resize(len, 0).is_ok() {
            storage::get(appkey(slot), buf).map_err(|_| Error::Storage)?;
        }
        Ok(match Record::decode(buf) {
            Ok(record) if record.scope == self.scope => Slot::Own(record),
            _ => Slot::Other(len),
        })
    }

    /// Find the first record of the scope at or after slot `start` that
    /// satisfies `pred`, return it together with its slot.
    fn find<'b>(
        &self,
        start: u8,
        pred: impl Fn(&Record) -> bool,
        buf: &'b mut Buffer,
    ) -> Result<Option<(u8, Record<'b>)>, Error> {
        for slot in start..MAX_RECORDS {
            if matches!(self.load(slot, buf)?, Slot::Own(record) if pred(&record)) {
                // Decoded again because the borrow checker rejects returning a
                // borrow of `buf` created before the condition, as `buf` is
                // borrowed mutably again in the next iteration, see
                // https://github.com/rust-lang/rust/issues/54663
                return Ok(Some((slot, unwrap!(Record::decode(buf)))));
            }
        }
        Ok(None)
    }

    /// Return the value stored under `key`, loaded into `buf`.
    pub fn get<'b>(&self, key: &[u8], buf: &'b mut Buffer) -> Result<Option<&'b [u8]>, Error> {
        let found = self.find(0, |record| record.key == key, buf)?;
        Ok(found.map(|(_, record)| record.value))
    }

    /// Return the next record from `cursor` on, loaded into `buf`, together
    /// with the cursor to continue with. Iteration starts with cursor 0. The
    /// order is unspecified, and so are the results if the records are modified
    /// in between.
    pub fn next<'b>(
        &self,
        cursor: u8,
        buf: &'b mut Buffer,
    ) -> Result<Option<(u8, Record<'b>)>, Error> {
        let found = self.find(cursor, |_| true, buf)?;
        Ok(found.map(|(slot, record)| (slot + 1, record)))
    }

    /// Store `value` under `key`, replacing an existing value in place.
    pub fn set(&self, key: &[u8], value: &[u8]) -> Result<(), Error> {
        let record = Record {
            scope: self.scope,
            key,
            value,
        };
        if record.len() > MAX_RECORD_LEN {
            return Err(Error::TooLarge);
        }

        let mut buf = Buffer::new();
        let mut used = 0;
        let mut existing = None;
        let mut empty = None;
        for slot in 0..MAX_RECORDS {
            match self.load(slot, &mut buf)? {
                Slot::Empty => empty = empty.or(Some(slot)),
                Slot::Other(len) => used += len,
                Slot::Own(stored) => {
                    used += stored.len();
                    if existing.is_none() && stored.key == key {
                        existing = Some((slot, stored.len()));
                    }
                }
            }
        }

        let (slot, freed) = match (existing, empty) {
            (Some((slot, old_len)), _) => (slot, old_len),
            (None, Some(slot)) => (slot, 0),
            (None, None) => return Err(Error::Full),
        };
        if used - freed + record.len() > MAX_TOTAL_BYTES {
            return Err(Error::Full);
        }

        record.encode(&mut buf)?;
        storage::set(appkey(slot), &buf).map_err(|_| Error::Storage)
    }

    /// Delete the record stored under `key`, return whether there was one.
    pub fn delete(&self, key: &[u8]) -> Result<bool, Error> {
        let mut buf = Buffer::new();
        let Some((slot, _)) = self.find(0, |record| record.key == key, &mut buf)? else {
            return Ok(false);
        };
        storage::delete(appkey(slot)).map_err(|_| Error::Storage)?;
        Ok(true)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const WALLET_A: WalletId = [0xaa; WALLET_ID_LEN];
    const WALLET_B: WalletId = [0xbb; WALLET_ID_LEN];
    const APP: &[u8] = b"\x01";
    const OTHER_APP: &[u8] = b"\x02";

    /// Length of a record of `APP` with a one-byte key and an empty value.
    const MIN_RECORD_LEN: usize = 1 + STORED_WALLET_ID_LEN + 1 + APP.len() + 2 + 1;

    fn init() {
        storage::init();
        storage::wipe();
    }

    fn scope(wallet_id: &'static WalletId, app: &'static [u8]) -> Scope<'static> {
        Scope::new(wallet_id, app).unwrap()
    }

    fn open(scope: Scope) -> Store {
        Store::new(scope).unwrap()
    }

    fn get(scope: Scope, key: &[u8]) -> Option<Vec<u8>> {
        let mut buf = Buffer::new();
        open(scope).get(key, &mut buf).unwrap().map(<[u8]>::to_vec)
    }

    fn set(scope: Scope, key: &[u8], value: &[u8]) -> Result<(), Error> {
        open(scope).set(key, value)
    }

    fn delete(scope: Scope, key: &[u8]) -> bool {
        open(scope).delete(key).unwrap()
    }

    fn entries(scope: Scope) -> Vec<(Vec<u8>, Vec<u8>)> {
        let store = open(scope);
        let mut buf = Buffer::new();
        let mut cursor = 0;
        let mut result = Vec::new();
        while let Some((next, record)) = store.next(cursor, &mut buf).unwrap() {
            result.push((record.key.to_vec(), record.value.to_vec()));
            cursor = next;
        }
        result
    }

    fn raw(slot: u8) -> Option<Vec<u8>> {
        let len = storage::get_length(appkey(slot)).ok()?;
        let mut buf = vec![0; len];
        storage::get(appkey(slot), &mut buf).unwrap();
        Some(buf)
    }

    fn plant(slot: u8, record: &[u8]) {
        storage::set(appkey(slot), record).unwrap();
    }

    fn encoded(scope: Scope, key: &[u8], value: &[u8]) -> Vec<u8> {
        let mut buf = Buffer::new();
        Record { scope, key, value }.encode(&mut buf).unwrap();
        buf.to_vec()
    }

    /// Value that makes a record of `APP` with a one-byte key `len` bytes long.
    fn value_for_len(len: usize) -> Vec<u8> {
        vec![0x42; len - MIN_RECORD_LEN]
    }

    #[test]
    fn test_round_trip() {
        init();
        let s = scope(&WALLET_A, APP);
        assert_eq!(get(s, b"key"), None);
        assert_eq!(entries(s), vec![]);

        set(s, b"key", b"value").unwrap();
        set(s, b"", b"").unwrap();
        assert_eq!(get(s, b"key"), Some(b"value".to_vec()));
        assert_eq!(get(s, b"ke"), None);
        assert_eq!(get(s, b""), Some(vec![]));

        set(s, b"key", b"longer value").unwrap();
        assert_eq!(get(s, b"key"), Some(b"longer value".to_vec()));
        assert_eq!(entries(s).len(), 2);

        assert!(delete(s, b"key"));
        assert!(!delete(s, b"key"));
        assert_eq!(entries(s), vec![(vec![], vec![])]);
    }

    #[test]
    fn test_scope_validation() {
        assert!(Scope::new(&WALLET_A, &[0; MAX_APP_LEN]).is_ok());
        assert_eq!(
            Scope::new(&WALLET_A, &[0; MAX_APP_LEN + 1]).err(),
            Some(Error::InvalidScope)
        );
    }

    #[test]
    fn test_max_record_len() {
        init();
        let s = scope(&WALLET_A, APP);
        set(s, b"k", &value_for_len(MAX_RECORD_LEN)).unwrap();
        assert_eq!(
            set(s, b"l", &value_for_len(MAX_RECORD_LEN + 1)),
            Err(Error::TooLarge)
        );
    }

    #[test]
    fn test_max_records() {
        init();
        let s = scope(&WALLET_A, APP);
        for i in 0..MAX_RECORDS {
            set(s, &[i], b"").unwrap();
        }
        assert_eq!(set(s, b"new", b""), Err(Error::Full));

        // Replacing does not need a free slot, deleting frees one.
        set(s, &[0], b"replaced").unwrap();
        assert!(delete(s, &[1]));
        set(s, b"new", b"").unwrap();
        assert_eq!(entries(s).len(), usize::from(MAX_RECORDS));
    }

    #[test]
    fn test_max_total_bytes() {
        init();
        let s = scope(&WALLET_A, APP);
        let other = scope(&WALLET_B, APP);
        // records of equal length that together fill the budget exactly
        const RECORD_LEN: usize = 1024;
        const _: () = assert!(MAX_TOTAL_BYTES.is_multiple_of(RECORD_LEN));
        let value = value_for_len(RECORD_LEN);
        for i in 0..MAX_TOTAL_BYTES / RECORD_LEN {
            set(s, &[i as u8], &value).unwrap();
        }
        // The budget is shared by all scopes.
        assert_eq!(set(other, b"x", b""), Err(Error::Full));

        // Replacing frees the old record's bytes, deleting too.
        set(s, &[0], &value).unwrap();
        assert_eq!(
            set(s, &[0], &value_for_len(RECORD_LEN + 1)),
            Err(Error::Full)
        );
        assert!(delete(s, &[0]));
        set(other, b"x", b"").unwrap();
    }

    #[test]
    fn test_other_records() {
        init();
        let s = scope(&WALLET_A, APP);
        let others = [
            // other scopes
            encoded(scope(&WALLET_B, APP), b"key", b"value"),
            encoded(scope(&WALLET_A, OTHER_APP), b"key", b"value"),
            // unknown version
            {
                let mut r = encoded(s, b"key", b"value");
                r[0] = VERSION + 1;
                r
            },
            // malformed
            {
                let mut r = encoded(s, b"key", b"");
                r.pop();
                r
            },
            vec![],
            // too large to load
            vec![0; MAX_RECORD_LEN + 1],
        ];
        for (slot, other) in others.iter().enumerate() {
            plant(slot as u8, other);
        }
        assert_eq!(get(s, b"key"), None);
        assert_eq!(entries(s), vec![]);
        assert!(!delete(s, b"key"));

        // They are never overwritten.
        set(s, b"key", b"new").unwrap();
        for (slot, other) in others.iter().enumerate() {
            assert_eq!(raw(slot as u8).as_ref(), Some(other));
        }
        assert_eq!(get(s, b"key"), Some(b"new".to_vec()));
    }

    #[test]
    fn test_other_records_capacity() {
        let s = scope(&WALLET_A, APP);
        // They count towards the total length...
        init();
        plant(0, &[0; MAX_TOTAL_BYTES]);
        assert_eq!(set(s, b"k", b""), Err(Error::Full));

        // ...and take up slots.
        init();
        for slot in 0..MAX_RECORDS {
            plant(slot, &[]);
        }
        assert_eq!(set(s, b"k", b""), Err(Error::Full));
    }
}
