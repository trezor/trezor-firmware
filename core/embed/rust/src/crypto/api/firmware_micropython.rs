use crate::{
    error::Error,
    micropython::{
        buffer::StrBuffer,
        list::List,
        macros::{obj_fn_kw, obj_module},
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        util,
    },
    strutil::TString,
};

use core::mem::MaybeUninit;
use rkyv::{
    api::low::to_bytes_in_with_alloc,
    rancor::Failure,
    ser::{allocator::SubAllocator, writer::Buffer},
    util::Align,
};
use trezor_structs::{
    ArchivedDerivationPath, ArchivedShortString, ArchivedTrezorCryptoEnum, ArchivedTypedHash,
    DerivationPath, LongString, TrezorCryptoResult,
};

// TODO preparation for the complete Rust implementation of TrezorCrypto API
extern "C" fn new_process_crypto_message(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let obj: Obj = kwargs.get(Qstr::MP_QSTR_data)?;
        let ipc_callback: Option<Obj> = kwargs
            .get(Qstr::MP_QSTR_ipc_cb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;
        let ipc_cb = ipc_callback
            .map(|cb| {
                move |bytes: &[u8]| {
                    cb.call_with_n_args(&[bytes.try_into().unwrap()]).unwrap();
                }
            })
            .unwrap();

        let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });

        // Safe helper to convert archived string to TString using Deref
        fn tstr_from_archived(s: &ArchivedShortString) -> TString<'static> {
            unsafe { StrBuffer::from_ptr_and_len(s.data.as_ptr(), s.len as usize) }.into()
        }

        // Deserialize the rkyv archived data directly from the static buffer
        let archived = unsafe { rkyv::access_unchecked::<ArchivedTrezorCryptoEnum>(data) };

        // Access the archived data zero-copy using safe Deref access
        let result = match archived {
            ArchivedTrezorCryptoEnum::GetXpub { address_n: _ } => {
                TrezorCryptoResult::Xpub(LongString::from_str("dummy").unwrap_or_default())
            }
            _ => TrezorCryptoResult::None,
        };

        let mut arena = [MaybeUninit::<u8>::uninit(); 200];
        let mut out = Align([MaybeUninit::<u8>::uninit(); 200]);

        let bytes = to_bytes_in_with_alloc::<_, _, Failure>(
            &result,
            Buffer::from(&mut *out),
            SubAllocator::new(&mut arena),
        )
        .unwrap();

        //Send the response back via the ipc_cb callback
        ipc_cb(bytes.as_ref());

        Ok(Obj::const_none())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_deserialize_derivation_path(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let obj: Obj = kwargs.get(Qstr::MP_QSTR_data)?;

        let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });

        // Safe helper to convert archived string to DerivationPath using Deref
        fn dp_from_archived(s: &ArchivedDerivationPath) -> DerivationPath {
            let slice = unsafe {
                core::slice::from_raw_parts(s.data.as_ptr() as *const u32, s.len as usize)
            };
            DerivationPath::from_slice(slice).unwrap_or_default()
        }

        // Deserialize the rkyv archived data directly from the static buffer
        let archived = unsafe { rkyv::access_unchecked::<ArchivedTrezorCryptoEnum>(data) };

        // Access the archived data zero-copy using safe Deref access
        let result = match archived {
            ArchivedTrezorCryptoEnum::GetXpub { address_n } => dp_from_archived(address_n),
            _ => return Err(Error::TypeError),
        };

        // Convert to Python list of integers
        let mut tuple_objs = heapless::Vec::<Obj, 10>::new();
        for i in 0..(result.as_slice().len() as usize) {
            result
                .as_slice()
                .get(i)
                .map(|&x| unwrap!(tuple_objs.push(unwrap!(x.try_into()))))
                .ok_or(Error::TypeError)?;
        }

        let list = List::alloc(&tuple_objs)?;

        Ok(list.into())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_deserialize_crypto_message(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let obj: Obj = kwargs.get(Qstr::MP_QSTR_data)?;

        let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });

        // Safe helper to convert archived string to DerivationPath using Deref
        fn dp_from_archived(s: &ArchivedDerivationPath) -> DerivationPath {
            let slice = unsafe {
                core::slice::from_raw_parts(s.data.as_ptr() as *const u32, s.len as usize)
            };
            DerivationPath::from_slice(slice).unwrap_or_default()
        }

        fn obj_from_dp(dp: &DerivationPath) -> Obj {
            let mut tuple_objs = heapless::Vec::<Obj, 10>::new();
            for i in 0..(dp.as_slice().len() as usize) {
                dp.as_slice()
                    .get(i)
                    .map(|&x| unwrap!(tuple_objs.push(unwrap!(x.try_into()))))
                    .ok_or(Error::TypeError)
                    .unwrap();
            }
            List::alloc(&tuple_objs).unwrap().into()
        }

        fn obj_from_archived_hash(s: &ArchivedTypedHash) -> Obj {
            let bytes =
                unsafe { core::slice::from_raw_parts(s.data.as_ptr(), s.data.len() as usize) };
            // Convert the bytes to a Python bytes object
            unwrap!(bytes.try_into())
        }

        // Deserialize the rkyv archived data directly from the static buffer
        let archived = unsafe { rkyv::access_unchecked::<ArchivedTrezorCryptoEnum>(data) };

        // Access the archived data zero-copy using safe Deref access
        let result: Obj = match archived {
            ArchivedTrezorCryptoEnum::GetXpub { address_n } => {
                let dp = dp_from_archived(address_n);
                (Obj::try_from(0i32)?, obj_from_dp(&dp)).try_into()?
            }
            ArchivedTrezorCryptoEnum::GetEthPubkeyHash { address_n } => {
                let dp = dp_from_archived(address_n);
                (Obj::try_from(1i32)?, obj_from_dp(&dp)).try_into()?
            }
            ArchivedTrezorCryptoEnum::SignTypedHash { address_n, hash } => {
                let dp = dp_from_archived(address_n);
                let hash_obj = obj_from_archived_hash(hash);
                (Obj::try_from(2i32)?, obj_from_dp(&dp), hash_obj).try_into()?
            }
        };

        Ok(result)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn new_send_crypto_result(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let obj: Obj = kwargs.get(Qstr::MP_QSTR_result)?;

        let ipc_callback: Option<Obj> = kwargs
            .get(Qstr::MP_QSTR_ipc_cb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let ipc_cb = ipc_callback
            .map(|cb| {
                move |bytes: &[u8]| {
                    cb.call_with_n_args(&[bytes.try_into().unwrap()]).unwrap();
                }
            })
            .unwrap();

        // Map MicroPython CryptoResult object to Rust enum for serialization
        let msg = if obj.is_str() {
            let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });
            TrezorCryptoResult::Xpub(unwrap!(LongString::from_str(unwrap!(
                core::str::from_utf8(data)
            ))))
        } else {
            let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });
            match data.len() {
                64 => TrezorCryptoResult::Signature(data.try_into().unwrap()),
                20 => TrezorCryptoResult::EthPubkeyHash(data.try_into().unwrap()),
                _ => return Err(Error::TypeError),
            }
        };

        let mut arena = [MaybeUninit::<u8>::uninit(); 200];
        let mut out = Align([MaybeUninit::<u8>::uninit(); 200]);

        let bytes = to_bytes_in_with_alloc::<_, _, Failure>(
            &msg,
            Buffer::from(&mut *out),
            SubAllocator::new(&mut arena),
        )
        .unwrap();

        //Send the response back via the ipc_cb callback
        ipc_cb(bytes.as_ref());

        Ok(Obj::const_none())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
pub static mp_module_trezorcrypto_api: Module = obj_module! {
    /// def process_crypto_message(
    ///     *,
    ///     data: bytes,
    ///     ipc_cb: Callable[[bytes], None],
    /// ) -> bytes:
    ///     """Process an IPC message by deserializing it and dispatching to the appropriate crypto function.
    ///         The response is serialized and sent via the ipc_cb callback.
    ///     """
    Qstr::MP_QSTR_process_crypto_message => obj_fn_kw!(0, new_process_crypto_message).as_obj(),

    /// def send_crypto_result(
    ///     *,
    ///     result: CryptoResult,
    ///     ipc_cb: Callable[[bytes], None],
    /// ) -> bytes:
    ///     """Serialize a crypto result (e.g. CryptoResult) into bytes and send it back via the ipc_cb callback."""
    Qstr::MP_QSTR_send_crypto_result => obj_fn_kw!(0, new_send_crypto_result).as_obj(),

    /// def deserialize_derivation_path(
    ///     *,
    ///     data: bytes,
    /// ) -> List[int]:
    ///     """Deserialize a derivation path from bytes and return it as a list of integers."""
    Qstr::MP_QSTR_deserialize_derivation_path => obj_fn_kw!(0, new_deserialize_derivation_path).as_obj(),


    /// def deserialize_crypto_message(
    ///     *,
    ///     data: bytes,
    /// ) -> Obj:
    ///     """Deserialize a crypto message from bytes and return it as a MicroPython object."""
    Qstr::MP_QSTR_deserialize_crypto_message => obj_fn_kw!(0, new_deserialize_crypto_message).as_obj(),
};
