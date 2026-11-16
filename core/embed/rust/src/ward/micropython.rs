use super::error::WARD_EXCEPTION_TYPE;
use super::store::{Buffer, Scope, Store};
use super::trie::{self, Digest, Refusal, Update, BATCH_MAX};
use crate::micropython::buffer::{get_buffer, get_buffer_mut};
use crate::micropython::gc::Gc;
use crate::micropython::list::List;
use crate::micropython::macros::{obj_fn_2, obj_fn_3, obj_fn_var, obj_module};
use crate::micropython::map::Map;
use crate::micropython::module::Module;
use crate::micropython::qstr::Qstr;
use crate::micropython::{util, Error, Obj};

fn store<'a>(wallet_id: &'a [u8], app: &'a [u8]) -> Result<Store<'a>, Error> {
    Ok(Store::new(Scope::new(wallet_id, app)?)?)
}

extern "C" fn ward_get(wallet_id: Obj, app: Obj, key: Obj) -> Obj {
    let block = || {
        // SAFETY: references are discarded at the end of this block.
        let (wallet_id, app, key) =
            unsafe { (get_buffer(wallet_id)?, get_buffer(app)?, get_buffer(key)?) };
        let mut buf = Buffer::new();
        store(wallet_id, app)?.get(key, &mut buf)?.try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ward_next_entry(wallet_id: Obj, app: Obj, cursor: Obj) -> Obj {
    let block = || {
        // SAFETY: references are discarded at the end of this block.
        let (wallet_id, app) = unsafe { (get_buffer(wallet_id)?, get_buffer(app)?) };
        let store = store(wallet_id, app)?;
        let cursor: u8 = cursor.try_into()?;
        let mut buf = Buffer::new();
        match store.next(cursor, &mut buf)? {
            Some((next, record)) => (next, record.key, record.value).try_into(),
            None => Ok(Obj::const_none()),
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ward_set(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        // SAFETY: references are discarded at the end of this block.
        let (wallet_id, app, key, value) = unsafe {
            (
                get_buffer(args[0])?,
                get_buffer(args[1])?,
                get_buffer(args[2])?,
                get_buffer(args[3])?,
            )
        };
        store(wallet_id, app)?.set(key, value)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn ward_delete(wallet_id: Obj, app: Obj, key: Obj) -> Obj {
    let block = || {
        // SAFETY: references are discarded at the end of this block.
        let (wallet_id, app, key) =
            unsafe { (get_buffer(wallet_id)?, get_buffer(app)?, get_buffer(key)?) };
        Ok(store(wallet_id, app)?.delete(key)?.into())
    };
    unsafe { util::try_or_raise(block) }
}

fn trie_error(error: trezor_ward::trie::Error) -> Error {
    use trezor_ward::trie::Error as E;
    Error::ValueError(match error {
        E::Length => c"WARD trie: malformed proof",
        E::Shape => c"WARD trie: proof split bits out of order",
        E::OffPath => c"WARD trie: proof is not the key's path",
        E::RootMismatch => c"WARD trie: proof does not match the root",
        E::ValueMismatch => c"WARD trie: value does not match the proof",
        E::OutOfOrder => c"WARD trie: entry out of order",
    })
}

fn refusal_error(error: Refusal) -> Error {
    match error {
        Refusal::Refused(error) => trie_error(error),
        Refusal::Absent => Error::ValueError(c"WARD trie: entry is absent"),
        Refusal::Present => Error::ValueError(c"WARD trie: entry is present"),
        Refusal::Batch => {
            Error::ValueError(c"WARD trie: batch is empty, too large or has a key twice")
        }
    }
}

/// Refuses a writable buffer that is also another argument: Rust would then
/// hold a mutable reference to bytes it also reads.
fn distinct(buf: Obj, others: &[Obj]) -> Result<(), Error> {
    if others.contains(&buf) {
        return Err(Error::ValueError(c"WARD trie: aliased buffer"));
    }
    Ok(())
}

/// A 32-byte digest or key.
///
/// SAFETY: the reference must be discarded before the object can be modified.
unsafe fn digest<'a>(obj: Obj) -> Result<&'a Digest, Error> {
    unsafe { get_buffer(obj) }?
        .try_into()
        .map_err(|_| Error::ValueError(c"WARD trie: expected 32 bytes"))
}

extern "C" fn ward_trie_lookup(root: Obj, key: Obj, proof: Obj) -> Obj {
    let block = || {
        // SAFETY: references are discarded at the end of this block.
        let (root, key, proof) = unsafe { (digest(root)?, digest(key)?, get_buffer(proof)?) };
        match trie::lookup(root, key, proof).map_err(trie_error)? {
            Some(commit) => commit.as_slice().try_into(),
            None => Ok(Obj::const_none()),
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ward_trie_set(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        // Read before any buffer is borrowed: it may run Python code.
        let present: bool = args[4].try_into()?;
        // SAFETY: references are discarded at the end of this block.
        let (root, key, proof, commit) = unsafe {
            (
                digest(args[0])?,
                digest(args[1])?,
                get_buffer(args[2])?,
                digest(args[3])?,
            )
        };
        let root = if present {
            trie::replace(root, key, proof, commit)
        } else {
            trie::insert(root, key, proof, commit)
        };
        root.map_err(refusal_error)?.as_slice().try_into()
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn ward_trie_remove(root: Obj, key: Obj, proof: Obj) -> Obj {
    let block = || {
        // SAFETY: references are discarded at the end of this block.
        let (root, key, proof) = unsafe { (digest(root)?, digest(key)?, get_buffer(proof)?) };
        trie::remove(root, key, proof)
            .map_err(refusal_error)?
            .as_slice()
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ward_trie_replace_all(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        let root = args[0];
        let (keys, proofs, commits): (Gc<List>, Gc<List>, Gc<List>) = (
            args[1].try_into()?,
            args[2].try_into()?,
            args[3].try_into()?,
        );
        // SAFETY: the lists are not modified while the slices are held.
        let (keys, proofs, commits) =
            unsafe { (keys.as_slice(), proofs.as_slice(), commits.as_slice()) };
        if keys.len() != proofs.len() || keys.len() != commits.len() || keys.len() > BATCH_MAX {
            return Err(Error::ValueError(
                c"WARD trie: batch is empty, too large or has a key twice",
            ));
        }
        // Every proof is written in place: each must be its own object.
        for (i, &proof) in proofs.iter().enumerate() {
            distinct(proof, &proofs[..i])?;
            distinct(proof, keys)?;
            distinct(proof, commits)?;
            distinct(proof, &[root])?;
        }
        // SAFETY: references are discarded at the end of this block, and every
        // proof is a different object from the others and from every other
        // argument.
        let root = unsafe { digest(root)? };
        let mut updates: heapless::Vec<Update, BATCH_MAX> = heapless::Vec::new();
        for i in 0..keys.len() {
            let update = unsafe {
                Update {
                    key: digest(keys[i])?,
                    proof: get_buffer_mut(proofs[i])?,
                    commit: digest(commits[i])?,
                }
            };
            // The length was checked against BATCH_MAX.
            let _ = updates.push(update);
        }
        trie::replace_all(root, &mut updates)
            .map_err(refusal_error)?
            .as_slice()
            .try_into()
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn ward_trie_walk_done(root: Obj, current: Obj) -> Obj {
    let block = || {
        // SAFETY: references are discarded at the end of this block.
        let root = unsafe { digest(root)? };
        let current = if current == Obj::const_none() {
            None
        } else {
            Some(unsafe { get_buffer(current)? })
        };
        Ok(trie::walk_done(root, current).map_err(trie_error)?.into())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ward_trie_walk_next_len(root: Obj, current: Obj, proof: Obj) -> Obj {
    let block = || {
        // SAFETY: references are discarded at the end of this block.
        let (root, proof) = unsafe { (digest(root)?, get_buffer(proof)?) };
        let current = if current == Obj::const_none() {
            None
        } else {
            Some(unsafe { get_buffer(current)? })
        };
        trie::walk_next_len(root, current, proof)
            .map_err(trie_error)?
            .try_into()
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn ward_trie_walk_next(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        distinct(args[3], &args[..3])?;
        distinct(args[1], &[args[0], args[2]])?;
        // SAFETY: references are discarded at the end of this block, and `current` and
        // `buf` are different objects from the others and from each other.
        let (root, proof, buf) = unsafe {
            (
                digest(args[0])?,
                get_buffer(args[2])?,
                get_buffer_mut(args[3])?,
            )
        };
        let current = if args[1] == Obj::const_none() {
            None
        } else {
            Some(unsafe { get_buffer_mut(args[1])? })
        };
        let (key, commit) = trie::walk_next(root, current, proof, buf).map_err(trie_error)?;
        (key.as_slice(), commit.as_slice()).try_into()
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezorward: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorward.to_obj(),

    /// WardError: type[Exception]
    Qstr::MP_QSTR_WardError => WARD_EXCEPTION_TYPE.as_type().as_obj(),

    /// def get(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes) -> bytes | None:
    ///     """
    ///     Return the value stored under `key` for the given wallet and app,
    ///     or None if there is no such record.
    ///     """
    Qstr::MP_QSTR_get => obj_fn_3!(ward_get).as_obj(),

    /// def next_entry(wallet_id: AnyBytes, app: AnyBytes, cursor: int) -> tuple[int, bytes, bytes] | None:
    ///     """
    ///     Return `(next_cursor, key, value)` of the next record of the given
    ///     wallet and app from `cursor` on, or None if there is none left.
    ///     The cursor is opaque: iteration starts with 0 and continues with
    ///     `next_cursor`. The order of the records is unspecified, and so are
    ///     the results if any store is modified in between.
    ///     """
    Qstr::MP_QSTR_next_entry => obj_fn_3!(ward_next_entry).as_obj(),

    /// def set(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes, value: AnyBytes) -> None:
    ///     """
    ///     Store `value` under `key` for the given wallet and app, replacing an
    ///     existing value in place. Raise WardError if the record does not fit.
    ///     """
    Qstr::MP_QSTR_set => obj_fn_var!(4, 4, ward_set).as_obj(),

    /// def delete(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes) -> bool:
    ///     """
    ///     Delete the record stored under `key` for the given wallet and app.
    ///     Return whether a record was deleted.
    ///     """
    Qstr::MP_QSTR_delete => obj_fn_3!(ward_delete).as_obj(),
    /// def trie_lookup(root: AnyBytes, key: AnyBytes, proof: AnyBytes) -> bytes | None:
    ///     """
    ///     Hold `proof` against the trusted `root` as the lookup path of `key` and
    ///     return the value digest stored under `key`, or None if `key` is absent.
    ///     Raise ValueError if the proof is refused.
    ///     """
    Qstr::MP_QSTR_trie_lookup => obj_fn_3!(ward_trie_lookup).as_obj(),

    /// def trie_set(root: AnyBytes, key: AnyBytes, proof: AnyBytes, commit: AnyBytes, present: bool) -> bytes:
    ///     """
    ///     Return the root after storing the value digest `commit` under `key`, held
    ///     against `root` by `proof`: a replacement if `present`, which `key` then
    ///     must be, else an insertion, which `key` must be absent for. Raise
    ///     ValueError if the proof is refused or `key` is not as required.
    ///     """
    Qstr::MP_QSTR_trie_set => obj_fn_var!(5, 5, ward_trie_set).as_obj(),

    /// def trie_remove(root: AnyBytes, key: AnyBytes, proof: AnyBytes) -> bytes:
    ///     """
    ///     Return the root after removing `key`, which `proof` must show present
    ///     under `root`; the empty root if it was the last entry. Raise ValueError
    ///     otherwise.
    ///     """
    Qstr::MP_QSTR_trie_remove => obj_fn_3!(ward_trie_remove).as_obj(),

    /// def trie_replace_all(root: AnyBytes, keys: list[bytes], proofs: list[bytearray], commits: list[bytes]) -> bytes:
    ///     """
    ///     Return the root after a batch of replacements: `keys[i]`'s value
    ///     digest becomes `commits[i]`, every `proofs[i]` against `root`. The
    ///     updates are made in turn, each proof held against the root the ones
    ///     before left, and the proofs are brought up to date in place. Raise
    ///     ValueError if a proof is refused, a key is absent or named twice, or
    ///     the batch is empty or larger than the queue.
    ///     """
    Qstr::MP_QSTR_trie_replace_all => obj_fn_var!(4, 4, ward_trie_replace_all).as_obj(),

    /// def trie_walk_done(root: AnyBytes, current: AnyBytes | None) -> bool:
    ///     """
    ///     Whether the key-order walk of the tree with `root`, at the entry the full
    ///     proof `current` proves (None: before the first), is over.
    ///     """
    Qstr::MP_QSTR_trie_walk_done => obj_fn_2!(ward_trie_walk_done).as_obj(),

    /// def trie_walk_next_len(root: AnyBytes, current: AnyBytes | None, proof: AnyBytes) -> int:
    ///     """
    ///     The length of the full proof `trie_walk_next` writes for `proof`.
    ///     """
    Qstr::MP_QSTR_trie_walk_next_len => obj_fn_3!(ward_trie_walk_next_len).as_obj(),

    /// def trie_walk_next(root: AnyBytes, current: bytearray | None, proof: AnyBytes, buf: bytearray) -> tuple[bytes, bytes]:
    ///     """
    ///     Accept `proof`, full or cut below where it parts from `current`, as the
    ///     entry after `current` (the first entry if None), and write its full proof
    ///     into `buf` of `trie_walk_next_len` bytes. Return the entry's key and value
    ///     digest. Raise ValueError if the proof is refused or out of order.
    ///     """
    Qstr::MP_QSTR_trie_walk_next => obj_fn_var!(4, 4, ward_trie_walk_next).as_obj(),
};
