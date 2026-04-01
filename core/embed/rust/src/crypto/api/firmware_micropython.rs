use crate::{
    error::Error,
    micropython::{
        list::List,
        macros::{obj_fn_kw, obj_module},
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        util,
    },
};

use core::mem::MaybeUninit;
use rkyv::{
    api::low::to_bytes_in_with_alloc,
    rancor::Failure,
    ser::{allocator::SubAllocator, writer::Buffer},
    util::Align,
};
use trezor_structs::{ArchivedSlice, ArchivedTrezorCryptoEnum, String, TrezorCryptoResult};

extern "C" fn new_deserialize_crypto_message(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let obj: Obj = kwargs.get(Qstr::MP_QSTR_data)?;

        let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });

        fn obj_from_dp_slice(slice: &ArchivedSlice<u32>) -> Obj {
            let slice = slice.as_slice();
            let mut list = unwrap!(List::with_capacity(slice.len()));

            for &item in slice {
                unwrap!(list.append(unwrap!(Obj::try_from(item.to_native()))));
            }
            unwrap!(List::alloc(unsafe { list.as_slice() })).into()
        }

        // Deserialize the rkyv archived data directly from the static buffer
        let archived = unsafe { rkyv::access_unchecked::<ArchivedTrezorCryptoEnum>(data) };

        // Access the archived data zero-copy using safe Deref access
        let result: Obj = match archived {
            ArchivedTrezorCryptoEnum::GetXpub { address_n } => obj_from_dp_slice(address_n),
            ArchivedTrezorCryptoEnum::GetEthPubkeyHash {
                address_n,
                encoded_network,
                encoded_token,
            } => {
                let network_obj = match encoded_network.as_ref() {
                    Some(network) => Obj::try_from(network.as_slice())?,
                    None => Obj::const_none(),
                };
                let token_obj = match encoded_token.as_ref() {
                    Some(token) => Obj::try_from(token.as_slice())?,
                    None => Obj::const_none(),
                };
                (obj_from_dp_slice(address_n), network_obj, token_obj).try_into()?
            }
            ArchivedTrezorCryptoEnum::SignTypedHash {
                address_n,
                hash,
                encoded_network,
                encoded_token,
                chain_id,
            } => {
                let hash_obj = Obj::try_from(hash.as_slice())?;
                let network_obj = match encoded_network.as_ref() {
                    Some(network) => Obj::try_from(network.as_slice())?,
                    None => Obj::const_none(),
                };
                let token_obj = match encoded_token.as_ref() {
                    Some(token) => Obj::try_from(token.as_slice())?,
                    None => Obj::const_none(),
                };
                let chain_id_obj = match chain_id.as_ref() {
                    Some(id) => Obj::try_from(id.to_native())?,
                    None => Obj::const_none(),
                };
                (
                    obj_from_dp_slice(address_n),
                    hash_obj,
                    network_obj,
                    token_obj,
                    chain_id_obj,
                )
                    .try_into()?
            }
            ArchivedTrezorCryptoEnum::GetAddressMac {
                address_n,
                address,
                encoded_network,
            } => {
                let buffer_obj = match encoded_network.as_ref() {
                    Some(network) => Obj::try_from(network.as_slice())?,
                    None => Obj::const_none(),
                };
                (
                    obj_from_dp_slice(address_n),
                    address.as_str().try_into()?,
                    buffer_obj,
                )
                    .try_into()?
            }
            ArchivedTrezorCryptoEnum::VerifyNonceCache { nonce } => {
                Obj::try_from(nonce.as_slice())?
            }
            ArchivedTrezorCryptoEnum::CheckAddressMac {
                address_n,
                mac,
                address,
                encoded_network,
            } => {
                let buffer_obj = match encoded_network.as_ref() {
                    Some(network) => Obj::try_from(network.as_slice())?,
                    None => Obj::const_none(),
                };
                (
                    obj_from_dp_slice(address_n),
                    mac.as_slice().try_into()?,
                    address.as_str().try_into()?,
                    buffer_obj,
                )
                    .try_into()?
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
            let slice = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });
            TrezorCryptoResult::Xpub(unwrap!(String::from_slice(slice)))
        } else if obj.is_bytes() {
            let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });
            dbg_println!("Data with length: {}", data.len());
            match data.len() {
                65 => TrezorCryptoResult::Signature(unwrap!(data.try_into())),
                32 => TrezorCryptoResult::AddressMac(unwrap!(data.try_into())),
                20 => TrezorCryptoResult::EthPubkeyHash(unwrap!(data.try_into())),
                _ => {
                    dbg_println!("Unexpected data length for crypto result: {}", data.len());
                    return Err(Error::TypeError);
                }
            }
        } else if obj.is_immediate() {
            TrezorCryptoResult::Boolean(unwrap!(bool::try_from(obj)))
        } else {
            dbg_println!("Unexpected object type for crypto result");
            return Err(Error::TypeError);
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
    /// ) -> None:
    ///     """Serialize a crypto result (e.g. CryptoResult) into bytes and send it back via the ipc_cb callback."""
    Qstr::MP_QSTR_send_crypto_result => obj_fn_kw!(0, new_send_crypto_result).as_obj(),



    /// def deserialize_crypto_message(
    ///     *,
    ///     data: bytes,
    /// ) -> Obj:
    ///     """Deserialize a crypto message from bytes and return it as a MicroPython object."""
    Qstr::MP_QSTR_deserialize_crypto_message => obj_fn_kw!(0, new_deserialize_crypto_message).as_obj(),
};
