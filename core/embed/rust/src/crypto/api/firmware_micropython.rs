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
    ArchivedBufferN, ArchivedDerivationPath, ArchivedShortString, ArchivedStringN, ArchivedTrezorCryptoEnum, ArchivedTypedHash, DerivationPath, LongString, ShortString, TrezorCryptoResult
};

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
                unwrap!(dp
                    .as_slice()
                    .get(i)
                    .map(|&x| unwrap!(tuple_objs.push(unwrap!(x.try_into()))))
                    .ok_or(Error::TypeError));
            }
            unwrap!(List::alloc(&tuple_objs)).into()
        }

        fn slice_from_archived<'a, const N: usize>(s: &'a ArchivedBufferN<N>) -> &'a [u8] {
            let buf = unsafe { core::slice::from_raw_parts::<u8>(s.data.as_ptr(), s.len as usize) };
            buf
        }

        fn str_from_archived<'a, const N: usize>(s: &'a ArchivedStringN<N>) -> &'a str {
            let str = unsafe { unwrap!(core::str::from_utf8(slice_from_archived(s))) };
            str
        }

        fn buffer_from_archived<const N: usize>(s: &ArchivedBufferN<N>) -> Obj {
            let slice = slice_from_archived(s);
            let mut tuple_objs = heapless::Vec::<Obj, N>::new();
            for i in 0..(slice.len() as usize) {
                unwrap!(slice
                    .get(i)
                    .map(|&x| unwrap!(tuple_objs.push(unwrap!(x.try_into()))))
                    .ok_or(Error::TypeError));
            }
            Obj::from(unwrap!(List::alloc(&tuple_objs)))
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
                obj_from_dp(&dp)
            }
            ArchivedTrezorCryptoEnum::GetEthPubkeyHash {
                address_n,
                encoded_network,
                encoded_token,
            } => {
                let dp = dp_from_archived(address_n);
                let network_obj = match encoded_network.as_ref() {
                    Some(network) => buffer_from_archived(network),
                    None => Obj::const_none(),
                };
                let token_obj = match encoded_token.as_ref() {
                    Some(token) => buffer_from_archived(token),
                    None => Obj::const_none(),
                };
                (obj_from_dp(&dp), network_obj, token_obj).try_into()?
            }
            ArchivedTrezorCryptoEnum::SignTypedHash {
                address_n,
                hash,
                encoded_network,
                encoded_token,
            } => {
                let dp = dp_from_archived(address_n);
                let hash_obj = obj_from_archived_hash(hash);
                let network_obj = match encoded_network.as_ref() {
                    Some(network) => buffer_from_archived(network),
                    None => Obj::const_none(),
                };
                let token_obj = match encoded_token.as_ref() {
                    Some(token) => buffer_from_archived(token),
                    None => Obj::const_none(),
                };
                (obj_from_dp(&dp), hash_obj, network_obj, token_obj).try_into()?
            }
            ArchivedTrezorCryptoEnum::GetAddressMac {
                address_n,
                address,
                encoded_network,
            } => {
                let dp = dp_from_archived(address_n);
                let address_str = str_from_archived(address);
                let buffer_obj = match encoded_network.as_ref() {
                    Some(network) => buffer_from_archived(network),
                    None => Obj::const_none(),
                };
                (obj_from_dp(&dp), address_str.try_into()?, buffer_obj).try_into()?
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

        let ipc_cb = unwrap!(ipc_callback.map(|cb| {
            move |bytes: &[u8]| {
                unwrap!(cb.call_with_n_args(&[unwrap!(bytes.try_into())]));
            }
        }));

        // Map MicroPython CryptoResult object to Rust enum for serialization
        let msg = if obj.is_str() {
            let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });
            TrezorCryptoResult::Xpub(unwrap!(LongString::from_str(unwrap!(
                core::str::from_utf8(data)
            ))))
        } else if let Ok(false) = bool::try_from(obj) {
            TrezorCryptoResult::Failed(ShortString::from_str("Crypto function failed").unwrap_or_default())
        } else {
            let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });
            dbg_println!("Data with length: {}", data.len());
            match data.len() {
                64 => TrezorCryptoResult::Signature(unwrap!(data.try_into())),
                32 => TrezorCryptoResult::AddressMac(unwrap!(data.try_into())),
                20 => TrezorCryptoResult::EthPubkeyHash(unwrap!(data.try_into())),
                _ => return Err(Error::TypeError),
            }
        };

        let mut arena = [MaybeUninit::<u8>::uninit(); 200];
        let mut out = Align([MaybeUninit::<u8>::uninit(); 200]);

        let bytes = unwrap!(to_bytes_in_with_alloc::<_, _, Failure>(
            &msg,
            Buffer::from(&mut *out),
            SubAllocator::new(&mut arena),
        ));
        //Send the response back via the ipc_cb callback
        ipc_cb(bytes.as_ref());

        Ok(Obj::const_none())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[no_mangle]
pub static mp_module_trezorcrypto_api: Module = obj_module! {

    /// def send_crypto_result(
    ///     *,
    ///     result: CryptoResult,
    ///     ipc_cb: Callable[[bytes], None],
    /// ) -> bytes:
    ///     """Serialize a crypto result (e.g. CryptoResult) into bytes and send it back via the ipc_cb callback."""
    Qstr::MP_QSTR_send_crypto_result => obj_fn_kw!(0, new_send_crypto_result).as_obj(),



    /// def deserialize_crypto_message(
    ///     *,
    ///     data: bytes,
    /// ) -> Obj:
    ///     """Deserialize a crypto message from bytes and return it as a MicroPython object."""
    Qstr::MP_QSTR_deserialize_crypto_message => obj_fn_kw!(0, new_deserialize_crypto_message).as_obj(),
};
