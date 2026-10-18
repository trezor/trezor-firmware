#[cfg(feature = "app_loading")]
use rkyv::{rancor::Failure, Archived};
#[cfg(feature = "app_loading")]
use trezor_app_sdk::structs::{Slice, TrezorCryptoEnum, TrezorCryptoResultRef};

#[cfg(feature = "app_loading")]
use crate::micropython::gc::Gc;
use crate::micropython::macros::{obj_fn_kw, obj_module};
use crate::micropython::map::Map;
use crate::micropython::module::Module;
use crate::micropython::obj::Obj;
use crate::micropython::qstr::Qstr;
#[cfg(feature = "app_loading")]
use crate::micropython::{error::Error, list::List, util};

#[cfg(feature = "app_loading")]
extern "C" fn new_deserialize_crypto_message(
    n_args: usize,
    args: *const Obj,
    kwargs: *mut Map,
) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let obj: Obj = kwargs.get(Qstr::MP_QSTR_data)?;

        let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });

        fn obj_from_dp_slice(slice: &Archived<Slice<u32>>) -> Obj {
            let slice = slice.as_ref();
            let mut list = unwrap!(List::with_capacity(slice.len()));

            for &item in slice {
                unwrap!(list.append(unwrap!(Obj::try_from(item.to_native()))));
            }
            unwrap!(List::alloc(unsafe { list.as_slice() })).into()
        }

        let archived = rkyv::access::<Archived<TrezorCryptoEnum>, Failure>(data)
            .map_err(|_| Error::ValueError(c"Invalid crypto message"))?;

        let result: Obj = match archived {
            Archived::<TrezorCryptoEnum>::GetXpub {
                address_n,
                xpub_magic,
            } => {
                let dp_obj = obj_from_dp_slice(address_n);
                let magic_obj = unwrap!(Obj::try_from(xpub_magic.to_native()));
                (dp_obj, magic_obj).try_into()?
            }
            Archived::<TrezorCryptoEnum>::GetPublicKey {
                address_n,
                compressed,
            } => {
                let dp_obj = obj_from_dp_slice(address_n);
                let compressed_obj = unwrap!(Obj::try_from(*compressed));
                (dp_obj, compressed_obj).try_into()?
            }
            Archived::<TrezorCryptoEnum>::SignDigest {
                address_n,
                digest,
                compressed,
                canonical,
            } => {
                let digest_obj = Obj::try_from(digest.as_slice())?;
                (
                    obj_from_dp_slice(address_n),
                    digest_obj,
                    Obj::try_from(*compressed)?,
                    Obj::from(*canonical),
                )
                    .try_into()?
            }
            Archived::<TrezorCryptoEnum>::GetAddressMac {
                address_n,
                address,
                slip44,
            } => (
                obj_from_dp_slice(address_n),
                Obj::try_from(address.as_ref())?,
                Obj::try_from(slip44.to_native())?,
            )
                .try_into()?,
            Archived::<TrezorCryptoEnum>::VerifyNonceCache { nonce } => {
                Obj::try_from(nonce.as_ref())?
            }
            Archived::<TrezorCryptoEnum>::CheckAddressMac {
                address_n,
                mac,
                address,
                slip44,
            } => (
                obj_from_dp_slice(address_n),
                Obj::try_from(mac.as_ref())?,
                Obj::try_from(address.as_ref())?,
                Obj::try_from(slip44.to_native())?,
            )
                .try_into()?,
        };

        Ok(result)
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[cfg(not(feature = "app_loading"))]
extern "C" fn new_deserialize_crypto_message(
    _n_args: usize,
    _args: *const Obj,
    _kwargs: *mut Map,
) -> Obj {
    unimplemented!()
}

#[cfg(feature = "app_loading")]
extern "C" fn new_send_crypto_result(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let obj: Obj = kwargs.get(Qstr::MP_QSTR_result)?;

        let ipc_callback: Option<Obj> = kwargs
            .get(Qstr::MP_QSTR_ipc_cb)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let ipc_cb = unwrap!(ipc_callback.map(|cb| {
            move |bytes: Obj| {
                unwrap!(cb.call_with_n_args(&[bytes]));
            }
        }));

        // Map MicroPython CryptoResult object to Rust enum for serialization
        let msg = if obj.is_str() {
            let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });
            match data.len() {
                111 => TrezorCryptoResultRef::Xpub(unwrap!(data.try_into())),
                _ => {
                    log::debug!("Unexpected data length for crypto result: {}", data.len());
                    return Err(Error::TypeError);
                }
            }
        } else if obj.is_bytes() {
            let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(obj) });
            match data.len() {
                32 => TrezorCryptoResultRef::AddressMac(unwrap!(data.try_into())),
                65 => TrezorCryptoResultRef::Signature(unwrap!(data.try_into())),
                _ => {
                    log::debug!("Unexpected data length for crypto result: {}", data.len());
                    return Err(Error::TypeError);
                }
            }
        } else if obj.is_immediate() {
            TrezorCryptoResultRef::Boolean(unwrap!(bool::try_from(obj)))
        } else {
            log::debug!("Tuple serialization for crypto result");
            // Expect a (type_tag: int, bytes) tuple for ambiguous lengths (e.g. 65 bytes)
            let list: Gc<List> = obj.try_into()?;
            log::debug!("Tuple length: {}", list.len());
            assert!(
                list.len() == 2,
                "Expected a tuple of (type_tag: int, bytes)"
            );
            log::debug!("Getting tag");
            let tag_obj = list.get(0)?;
            let tag: u8 = unwrap!(tag_obj.try_into());
            log::debug!("Tag: {}", tag);
            log::debug!("Getting bytes");
            let bytes_obj = list.get(1)?;
            let data = unwrap!(unsafe { crate::micropython::buffer::get_buffer(bytes_obj) });
            log::debug!("Data length: {}", data.len());
            match tag {
                0 => {
                    assert!(
                        data.len() == 32 || data.len() == 33 || data.len() == 65,
                        "Expected public key to be 32, 33 or 65 bytes"
                    );
                    TrezorCryptoResultRef::PublicKey(unwrap!(data.try_into()))
                }
                _ => {
                    log::debug!("Unexpected type tag for crypto result: {}", tag);
                    return Err(Error::TypeError);
                }
            }
        };

        let bytes = crate::util::archive::to_bytes_obj(&msg)?;
        //Send the response back via the ipc_cb callback
        ipc_cb(bytes);

        Ok(Obj::const_none())
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

#[cfg(not(feature = "app_loading"))]
extern "C" fn new_send_crypto_result(_n_args: usize, _args: *const Obj, _kwargs: *mut Map) -> Obj {
    unimplemented!()
}

#[no_mangle]
pub static mp_module_trezorcrypto_api: Module = obj_module! {

    /// mock:global
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorcrypto_api.to_obj(),

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
