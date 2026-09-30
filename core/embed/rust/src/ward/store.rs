//! WARD offline store.
//!
//! Each record occupies one slot, i.e. one protected storage key in the
//! `APP_WARD` namespace, and is only ever accessible from its own scope (a
//! passphrase wallet and an app).
//!
//! Record layout:
//!
//! ```text
//! version: u8 | wallet_id[..8] | app: u8 | key_len: u16 BE | key | value
//! ```
//!
//! The first three fields form the frozen header, which never changes, so
//! that records of any version can be attributed to their scope. The rest is
//! the body of version 0.
//!
//! Records that are not of the current scope, not of version 0, or cannot be
//! parsed are never returned, written or deleted, they only count towards the
//! capacity limits. Nothing is ever evicted.

use zeroize::Zeroizing;

use super::error::Error;
use crate::trezorhal::storage;

/// Storage namespace of the records.
const APP_WARD: u16 = 0x05;

/// Number of slots, i.e. the maximum number of records.
pub const MAX_RECORDS: usize = 32;
/// Maximum total length of all records.
pub const MAX_TOTAL_BYTES: usize = 8192;
/// Maximum length of a single record, including its header.
pub const MAX_RECORD_LEN: usize = 2560;

/// Length of the wallet id passed by the caller.
pub const WALLET_ID_LEN: usize = 32;
/// Length of the wallet id prefix stored in the record header.
const STORED_WALLET_ID_LEN: usize = 8;

const VERSION: u8 = 0;
const HEADER_LEN: usize = 1 + STORED_WALLET_ID_LEN + 1;
const KEY_OFFSET: usize = HEADER_LEN + 2;

const _: () = assert!(MAX_RECORDS <= 0x100);
const _: () = assert!(MAX_RECORD_LEN <= u16::MAX as usize);

fn appkey(slot: usize) -> u16 {
    (APP_WARD << 8) | slot as u16
}

/// A passphrase wallet and an app.
#[derive(Clone, Copy, PartialEq)]
#[cfg_attr(test, derive(Debug))]
pub struct Scope {
    wallet_id: [u8; STORED_WALLET_ID_LEN],
    app: u8,
}

impl Scope {
    pub fn new(wallet_id: &[u8], app: u8) -> Result<Self, Error> {
        if wallet_id.len() != WALLET_ID_LEN {
            return Err(Error::InvalidWalletId);
        }
        let mut stored = [0; STORED_WALLET_ID_LEN];
        stored.copy_from_slice(&wallet_id[..STORED_WALLET_ID_LEN]);
        Ok(Self {
            wallet_id: stored,
            app,
        })
    }
}

/// A version 0 record.
#[cfg_attr(test, derive(Debug, PartialEq))]
pub struct Record<'a> {
    pub scope: Scope,
    pub key: &'a [u8],
    pub value: &'a [u8],
}

impl<'a> Record<'a> {
    /// Decode a well-formed version 0 record of any scope.
    fn decode(bytes: &'a [u8]) -> Option<Self> {
        let (header, body) = bytes.split_at_checked(HEADER_LEN)?;
        if header[0] != VERSION {
            return None;
        }
        let mut wallet_id = [0; STORED_WALLET_ID_LEN];
        wallet_id.copy_from_slice(&header[1..HEADER_LEN - 1]);
        let scope = Scope {
            wallet_id,
            app: header[HEADER_LEN - 1],
        };
        let (key_len, rest) = body.split_first_chunk()?;
        let (key, value) = rest.split_at_checked(usize::from(u16::from_be_bytes(*key_len)))?;
        Some(Self { scope, key, value })
    }

    fn len(&self) -> usize {
        KEY_OFFSET + self.key.len() + self.value.len()
    }

    /// Encode the record into `buf`.
    fn encode<const N: usize>(&self, buf: &mut heapless::Vec<u8, N>) -> Result<(), Error> {
        let key_len = u16::try_from(self.key.len()).map_err(|_| Error::TooLarge)?;
        buf.clear();
        [
            &[VERSION][..],
            &self.scope.wallet_id,
            &[self.scope.app],
            &key_len.to_be_bytes(),
            self.key,
            self.value,
        ]
        .into_iter()
        .try_for_each(|part| buf.extend_from_slice(part))
        .map_err(|_| Error::TooLarge)
    }
}

/// Access to the records of a scope. The buffer holds the plaintext of the
/// last record loaded, and is zeroized on drop.
pub struct Store {
    scope: Scope,
    buf: Zeroizing<heapless::Vec<u8, MAX_RECORD_LEN>>,
}

impl Store {
    pub fn new(scope: Scope) -> Result<Self, Error> {
        // A locked storage cannot be read and would look empty.
        if !storage::is_unlocked() {
            return Err(Error::Locked);
        }
        Ok(Self {
            scope,
            buf: Zeroizing::new(heapless::Vec::new()),
        })
    }

    /// Load `slot` into the buffer, return the length of the stored record,
    /// or `None` if the slot is empty. Records that do not fit into the
    /// buffer are not loaded, leaving the buffer empty.
    fn load(&mut self, slot: usize) -> Result<Option<usize>, Error> {
        self.buf.clear();
        let Ok(len) = storage::get_length(appkey(slot)) else {
            return Ok(None);
        };
        if self.buf.resize(len, 0).is_ok() {
            storage::get(appkey(slot), &mut self.buf).map_err(|_| Error::Storage)?;
        }
        Ok(Some(len))
    }

    /// The loaded record, if it is a version 0 record of the scope.
    fn loaded(&self) -> Option<Record<'_>> {
        let record = Record::decode(&self.buf)?;
        (record.scope == self.scope).then_some(record)
    }

    /// Find the first record of the scope at or after slot `start` that
    /// satisfies `pred`, return it together with its slot.
    fn find(
        &mut self,
        start: usize,
        pred: impl Fn(&Record) -> bool,
    ) -> Result<Option<(usize, Record<'_>)>, Error> {
        for slot in start..MAX_RECORDS {
            self.load(slot)?;
            if self.loaded().is_some_and(|record| pred(&record)) {
                // Decoded again because the borrow checker rejects returning a
                // borrow of `self` created before the condition, as `self` is
                // borrowed mutably again in the next iteration, see
                // https://github.com/rust-lang/rust/issues/54663
                return Ok(self.loaded().map(|record| (slot, record)));
            }
        }
        Ok(None)
    }

    /// Return the value stored under `key`.
    pub fn get(&mut self, key: &[u8]) -> Result<Option<&[u8]>, Error> {
        let found = self.find(0, |record| record.key == key)?;
        Ok(found.map(|(_, record)| record.value))
    }

    /// Return the first record at or after slot `start`, together with its
    /// slot.
    pub fn next(&mut self, start: usize) -> Result<Option<(usize, Record<'_>)>, Error> {
        self.find(start, |_| true)
    }

    /// Store `value` under `key`, replacing an existing value in place.
    pub fn set(&mut self, key: &[u8], value: &[u8]) -> Result<(), Error> {
        let record = Record {
            scope: self.scope,
            key,
            value,
        };
        if record.len() > MAX_RECORD_LEN {
            return Err(Error::TooLarge);
        }

        let mut used = 0;
        let mut own = None;
        let mut empty = None;
        for slot in 0..MAX_RECORDS {
            let Some(len) = self.load(slot)? else {
                empty = empty.or(Some(slot));
                continue;
            };
            used += len;
            if own.is_none() && self.loaded().is_some_and(|record| record.key == key) {
                own = Some((slot, len));
            }
        }

        let (slot, freed) = match (own, empty) {
            (Some((slot, old_len)), _) => (slot, old_len),
            (None, Some(slot)) => (slot, 0),
            (None, None) => return Err(Error::Full),
        };
        if used - freed + record.len() > MAX_TOTAL_BYTES {
            return Err(Error::Full);
        }

        record.encode(&mut *self.buf)?;
        storage::set(appkey(slot), &self.buf).map_err(|_| Error::Storage)
    }

    /// Delete the record stored under `key`, return whether there was one.
    pub fn delete(&mut self, key: &[u8]) -> Result<bool, Error> {
        let Some((slot, _)) = self.find(0, |record| record.key == key)? else {
            return Ok(false);
        };
        storage::delete(appkey(slot)).map_err(|_| Error::Storage)?;
        Ok(true)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const WALLET_A: [u8; WALLET_ID_LEN] = [0xaa; WALLET_ID_LEN];
    const WALLET_B: [u8; WALLET_ID_LEN] = [0xbb; WALLET_ID_LEN];
    const APP: u8 = 1;
    const OTHER_APP: u8 = 2;

    /// Wallet id and app of a scope.
    type TestScope = (&'static [u8], u8);

    fn init() {
        storage::init();
        storage::wipe();
        storage::lock();
        assert!(storage::unlock("", None));
    }

    fn scope(wallet_id: &'static [u8], app: u8) -> TestScope {
        (wallet_id, app)
    }

    fn open(scope: &TestScope) -> Store {
        Store::new(Scope::new(scope.0, scope.1).unwrap()).unwrap()
    }

    fn get(scope: &TestScope, key: &[u8]) -> Option<Vec<u8>> {
        open(scope).get(key).unwrap().map(<[u8]>::to_vec)
    }

    fn set(scope: &TestScope, key: &[u8], value: &[u8]) -> Result<(), Error> {
        open(scope).set(key, value)
    }

    fn delete(scope: &TestScope, key: &[u8]) -> bool {
        open(scope).delete(key).unwrap()
    }

    fn entries(scope: &TestScope) -> Vec<(Vec<u8>, Vec<u8>)> {
        let mut store = open(scope);
        let mut start = 0;
        let mut result = Vec::new();
        while let Some((slot, record)) = store.next(start).unwrap() {
            result.push((record.key.to_vec(), record.value.to_vec()));
            start = slot + 1;
        }
        result
    }

    fn raw(slot: usize) -> Option<Vec<u8>> {
        let len = storage::get_length(appkey(slot)).ok()?;
        let mut buf = vec![0; len];
        storage::get(appkey(slot), &mut buf).unwrap();
        Some(buf)
    }

    fn plant(slot: usize, record: &[u8]) {
        storage::set(appkey(slot), record).unwrap();
    }

    fn record(version: u8, wallet_id: &[u8], app: u8, key: &[u8], value: &[u8]) -> Vec<u8> {
        let mut record = vec![version];
        record.extend_from_slice(&wallet_id[..STORED_WALLET_ID_LEN]);
        record.push(app);
        record.extend_from_slice(&(key.len() as u16).to_be_bytes());
        record.extend_from_slice(key);
        record.extend_from_slice(value);
        record
    }

    /// Value that makes a record with a one-byte key exactly `len` bytes long.
    fn value_for(len: usize) -> Vec<u8> {
        vec![0x42; len - KEY_OFFSET - 1]
    }

    #[test]
    fn test_record_encode_decode() {
        let scope = Scope::new(&WALLET_A, APP).unwrap();
        let mut buf = heapless::Vec::<u8, MAX_RECORD_LEN>::new();
        for (key, value) in [(&b"key"[..], &b"value"[..]), (b"", b"")] {
            let bytes = record(0, &WALLET_A, APP, key, value);
            let rec = Record { scope, key, value };
            assert_eq!(rec.len(), bytes.len());
            rec.encode(&mut buf).unwrap();
            assert_eq!(&buf[..], &bytes[..]);
            assert_eq!(Record::decode(&bytes), Some(rec));
        }
    }

    #[test]
    fn test_record_encode_too_large() {
        let record = Record {
            scope: Scope::new(&WALLET_A, APP).unwrap(),
            key: b"key",
            value: b"value",
        };
        let mut buf = heapless::Vec::<u8, 19>::new();
        assert_eq!(record.len(), 20);
        assert_eq!(record.encode(&mut buf), Err(Error::TooLarge));

        let key = vec![0; usize::from(u16::MAX) + 1];
        let record = Record {
            key: &key,
            ..record
        };
        let mut buf = heapless::Vec::<u8, MAX_RECORD_LEN>::new();
        assert_eq!(record.encode(&mut buf), Err(Error::TooLarge));
    }

    #[test]
    fn test_record_decode_malformed() {
        let bytes = record(0, &WALLET_A, APP, b"key", b"");
        // truncated key
        assert_eq!(Record::decode(&bytes[..bytes.len() - 1]), None);
        // truncated key length
        assert_eq!(Record::decode(&bytes[..KEY_OFFSET - 1]), None);
        // truncated header
        assert_eq!(Record::decode(&bytes[..HEADER_LEN - 1]), None);
        assert_eq!(Record::decode(&[]), None);
        // unknown version
        assert_eq!(
            Record::decode(&record(1, &WALLET_A, APP, b"key", b"")),
            None
        );
    }

    #[test]
    fn test_round_trip() {
        init();
        let s = scope(&WALLET_A, APP);
        assert_eq!(get(&s, b"key"), None);
        assert_eq!(entries(&s), vec![]);

        set(&s, b"key", b"value").unwrap();
        assert_eq!(get(&s, b"key"), Some(b"value".to_vec()));
        assert_eq!(get(&s, b"ke"), None);
        assert_eq!(get(&s, b"key2"), None);
        assert_eq!(entries(&s), vec![(b"key".to_vec(), b"value".to_vec())]);
        assert_eq!(raw(0), Some(record(0, &WALLET_A, APP, b"key", b"value")));

        set(&s, b"", b"").unwrap();
        assert_eq!(get(&s, b""), Some(vec![]));
    }

    #[test]
    fn test_wallet_id_length() {
        assert_eq!(
            Scope::new(&WALLET_A[..WALLET_ID_LEN - 1], APP).err(),
            Some(Error::InvalidWalletId)
        );
        assert_eq!(
            Scope::new(&[0; WALLET_ID_LEN + 1], APP).err(),
            Some(Error::InvalidWalletId)
        );
    }

    #[test]
    fn test_isolation() {
        init();
        let scopes = [
            scope(&WALLET_A, APP),
            scope(&WALLET_B, APP),
            scope(&WALLET_A, OTHER_APP),
        ];
        for (i, s) in scopes.iter().enumerate() {
            set(s, b"key", &[i as u8]).unwrap();
        }
        for (i, s) in scopes.iter().enumerate() {
            assert_eq!(get(s, b"key"), Some(vec![i as u8]));
            assert_eq!(entries(s), vec![(b"key".to_vec(), vec![i as u8])]);
        }

        assert!(delete(&scopes[0], b"key"));
        assert_eq!(get(&scopes[0], b"key"), None);
        assert_eq!(get(&scopes[1], b"key"), Some(vec![1]));
        assert_eq!(get(&scopes[2], b"key"), Some(vec![2]));
    }

    #[test]
    fn test_overwrite_in_place() {
        init();
        let s = scope(&WALLET_A, APP);
        set(&s, b"a", b"1").unwrap();
        set(&s, b"b", b"2").unwrap();
        set(&s, b"a", b"longer value").unwrap();
        assert_eq!(
            raw(0),
            Some(record(0, &WALLET_A, APP, b"a", b"longer value"))
        );
        assert_eq!(raw(2), None);
        assert_eq!(
            entries(&s),
            vec![
                (b"a".to_vec(), b"longer value".to_vec()),
                (b"b".to_vec(), b"2".to_vec()),
            ]
        );
    }

    #[test]
    fn test_delete() {
        init();
        let s = scope(&WALLET_A, APP);
        assert!(!delete(&s, b"a"));
        set(&s, b"a", b"1").unwrap();
        set(&s, b"b", b"2").unwrap();
        assert!(delete(&s, b"a"));
        assert!(!delete(&s, b"a"));
        assert_eq!(raw(0), None);
        assert_eq!(get(&s, b"b"), Some(b"2".to_vec()));

        // The freed slot is reused.
        set(&s, b"c", b"3").unwrap();
        assert_eq!(raw(0), Some(record(0, &WALLET_A, APP, b"c", b"3")));
    }

    #[test]
    fn test_next() {
        init();
        let s = scope(&WALLET_A, APP);
        let other = scope(&WALLET_B, APP);
        set(&s, b"a", b"1").unwrap();
        set(&other, b"x", b"").unwrap();
        set(&s, b"b", b"2").unwrap();

        let mut store = open(&s);
        let (slot, record) = store.next(0).unwrap().unwrap();
        assert_eq!((slot, record.key, record.value), (0, &b"a"[..], &b"1"[..]));
        let (slot, record) = store.next(slot + 1).unwrap().unwrap();
        assert_eq!((slot, record.key, record.value), (2, &b"b"[..], &b"2"[..]));
        assert!(store.next(slot + 1).unwrap().is_none());
        assert!(store.next(MAX_RECORDS).unwrap().is_none());
        assert!(store.next(usize::MAX).unwrap().is_none());
    }

    #[test]
    fn test_long_key() {
        init();
        let s = scope(&WALLET_A, APP);
        let key = [0x55; 300];
        set(&s, &key, b"value").unwrap();
        assert_eq!(get(&s, &key), Some(b"value".to_vec()));
        assert_eq!(get(&s, &key[..299]), None);
        assert_eq!(entries(&s), vec![(key.to_vec(), b"value".to_vec())]);
    }

    #[test]
    fn test_max_record_len() {
        init();
        let s = scope(&WALLET_A, APP);
        let value = value_for(MAX_RECORD_LEN);
        set(&s, b"k", &value).unwrap();
        assert_eq!(get(&s, b"k"), Some(value.clone()));
        assert_eq!(
            set(&s, b"l", &value_for(MAX_RECORD_LEN + 1)),
            Err(Error::TooLarge)
        );
        assert_eq!(
            set(&s, b"k", &value_for(MAX_RECORD_LEN + 1)),
            Err(Error::TooLarge)
        );
        assert_eq!(get(&s, b"k"), Some(value));
    }

    #[test]
    fn test_max_records() {
        init();
        let s = scope(&WALLET_A, APP);
        for i in 0..MAX_RECORDS {
            set(&s, &[i as u8], b"").unwrap();
        }
        assert_eq!(set(&s, b"new", b""), Err(Error::Full));
        assert_eq!(get(&s, b"new"), None);

        // Replacing does not need a free slot.
        set(&s, &[0], b"replaced").unwrap();
        assert_eq!(get(&s, &[0]), Some(b"replaced".to_vec()));
        assert_eq!(entries(&s).len(), MAX_RECORDS);
    }

    #[test]
    fn test_max_total_bytes() {
        init();
        let s = scope(&WALLET_A, APP);
        let other = scope(&WALLET_B, APP);
        let full = MAX_TOTAL_BYTES / MAX_RECORD_LEN;
        for i in 0..full {
            set(&s, &[i as u8], &value_for(MAX_RECORD_LEN)).unwrap();
        }
        let rest = MAX_TOTAL_BYTES - full * MAX_RECORD_LEN;
        // The budget is shared by all scopes.
        assert_eq!(set(&other, b"x", &value_for(rest + 1)), Err(Error::Full));
        set(&other, b"x", &value_for(rest)).unwrap();
        assert_eq!(set(&s, b"y", &value_for(KEY_OFFSET + 1)), Err(Error::Full));
    }

    #[test]
    fn test_replace_accounting() {
        init();
        let s = scope(&WALLET_A, APP);
        let full = MAX_TOTAL_BYTES / MAX_RECORD_LEN;
        for i in 0..full {
            set(&s, &[i as u8], &value_for(MAX_RECORD_LEN)).unwrap();
        }
        let rest = MAX_TOTAL_BYTES - full * MAX_RECORD_LEN;
        set(&s, b"x", &value_for(rest)).unwrap();

        // The replaced record's bytes are freed.
        set(&s, b"x", &value_for(rest)).unwrap();
        set(&s, b"x", &value_for(rest - 1)).unwrap();
        set(&s, b"x", &value_for(rest)).unwrap();
        assert_eq!(set(&s, b"x", &value_for(rest + 1)), Err(Error::Full));
        assert_eq!(get(&s, b"x"), Some(value_for(rest)));
        set(&s, &[0], &value_for(KEY_OFFSET + 1)).unwrap();
        set(&s, b"x", &value_for(rest + 1)).unwrap();
    }

    #[test]
    fn test_other_records() {
        let s = scope(&WALLET_A, APP);
        let others = [
            // foreign
            record(0, &WALLET_B, APP, b"key", b"value"),
            record(0, &WALLET_A, OTHER_APP, b"key", b"value"),
            // unknown version
            record(1, &WALLET_A, APP, b"key", b"value"),
            // malformed
            {
                let mut r = record(0, &WALLET_A, APP, b"key", b"");
                r.truncate(r.len() - 1);
                r
            },
            record(0, &WALLET_A, APP, b"", b"")[..KEY_OFFSET - 1].to_vec(),
            // unattributable
            record(0, &WALLET_A, APP, b"", b"")[..HEADER_LEN - 1].to_vec(),
            vec![],
            // oversized
            record(0, &WALLET_A, APP, b"key", &[0; MAX_RECORD_LEN]),
        ];
        for other in &others {
            init();
            plant(0, other);
            assert_eq!(get(&s, b"key"), None);
            assert_eq!(entries(&s), vec![]);
            assert!(!delete(&s, b"key"));

            set(&s, b"key", b"new").unwrap();
            assert_eq!(raw(0).as_ref(), Some(other));
            assert_eq!(raw(1), Some(record(0, &WALLET_A, APP, b"key", b"new")));
            assert!(delete(&s, b"key"));
            assert_eq!(raw(0).as_ref(), Some(other));
        }
    }

    #[test]
    fn test_other_records_capacity() {
        init();
        let s = scope(&WALLET_A, APP);
        let oversized = vec![0; MAX_RECORD_LEN + 1];
        let full = MAX_TOTAL_BYTES / oversized.len();
        for slot in 0..full {
            plant(slot, &oversized);
        }
        let rest = MAX_TOTAL_BYTES - full * oversized.len();
        assert_eq!(set(&s, b"k", &value_for(rest + 1)), Err(Error::Full));
        set(&s, b"k", &value_for(rest)).unwrap();

        init();
        for slot in 0..MAX_RECORDS {
            plant(slot, &[]);
        }
        assert_eq!(set(&s, b"k", b""), Err(Error::Full));
        for slot in 0..MAX_RECORDS {
            assert_eq!(raw(slot), Some(vec![]));
        }
    }

    #[test]
    fn test_locked() {
        init();
        let s = scope(&WALLET_A, APP);
        set(&s, b"key", b"value").unwrap();
        storage::lock();
        let scope = Scope::new(&WALLET_A, APP).unwrap();
        assert_eq!(Store::new(scope).err(), Some(Error::Locked));
        assert!(storage::unlock("", None));
        assert_eq!(get(&s, b"key"), Some(b"value".to_vec()));
    }
}
