use core::array::TryFromSliceError;
use core::convert::{TryFrom, TryInto};
use core::ops::{Deref, DerefMut};

use cstr_core::CStr;
use f4jumble;
use orchard::{
    keys::{
        FullViewingKey, IncomingViewingKey, OutgoingViewingKey, SpendAuthorizingKey, SpendingKey,
    },
    value::NoteValue,
    Address, Note,
};
use rand::SeedableRng;
use rand_chacha::ChaCha12Rng;

use group::ff::PrimeField;

use crate::error::Error;
use crate::micropython::{
    buffer::{Buffer, BufferMut},
    dict::Dict,
    gc::Gc,
    map::Map,
    obj::Obj,
    qstr::Qstr,
};
use crate::{trezorhal, util};

use pasta_curves::pallas;

macro_rules! try_parse_map {
    ($obj:ident) => {
        let dict: Gc<Dict> = $obj.try_into()?;
        let dict: &Dict = dict.deref();
        let $obj: &Map = dict.map();
    };
}

// TODO: move to micropython/obj.rs ?
impl<const N: usize> TryFrom<Obj> for [u8; N] {
    type Error = Error;
    fn try_from(obj: Obj) -> Result<[u8; N], Error> {
        let buffer: Buffer = obj.try_into()?;
        Ok(buffer.as_ref().try_into()?)
    }
}

// TODO: move to micropython/obj.rs ?
impl<const N: usize> TryFrom<[u8; N]> for Obj {
    type Error = Error;
    fn try_from(array: [u8; N]) -> Result<Obj, Error> {
        Ok((&array[..]).try_into()?)
    }
}

#[no_mangle]
pub extern "C" fn orchardlib_sign(sk: Obj, alpha: Obj, sighash: Obj) -> Obj {
    let block = || {
        let alpha: [u8; 32] = alpha.try_into()?;
        let alpha = pallas::Scalar::from_repr(alpha);
        let alpha = Option::from(alpha).ok_or(Error::TypeError)?;
        let sighash: [u8; 32] = sighash.try_into()?;
        let sk = get_sk(sk)?;
        let ask: SpendAuthorizingKey = (&sk).into();
        let mut rng = trezorhal::random::HardwareRandomness;
        let signature = ask.randomize(&alpha).sign(rng, &sighash);
        let signature_bytes: [u8; 64] = (&signature).into();
        Ok(signature_bytes.try_into()?)
    };
    unsafe { util::try_or_raise(block) }
}

fn parse_spend_info(spend_info: Obj) -> Result<(FullViewingKey, Note), Error> {
    //let spend_info: &Map = try_into_map!(spend_info)?;
    try_parse_map!(spend_info);
    let fvk_bytes: [u8; 96] = spend_info.get(Qstr::MP_QSTR_fvk)?.try_into()?;
    let fvk = FullViewingKey::from_bytes(&fvk_bytes).ok_or(Error::TypeError)?;
    let note: [u8; 115] = spend_info.get(Qstr::MP_QSTR_note)?.try_into()?;
    let note = orchard::hww::deserialize_note(note).ok_or(Error::TypeError)?; // TODO: Value Error
    Ok((fvk, note))
}

fn parse_output_info(
    output_info: Obj,
) -> Result<
    (
        Option<OutgoingViewingKey>,
        Address,
        NoteValue,
        Option<[u8; 512]>,
    ),
    Error,
> {
    //let output_info: &Map = try_into_map!(output_info)?;
    try_parse_map!(output_info);
    let ovk_flag: bool = output_info.get(Qstr::MP_QSTR_ovk_flag)?.try_into()?;
    let ovk: Option<OutgoingViewingKey> = if ovk_flag {
        let fvk_bytes: [u8; 96] = output_info.get(Qstr::MP_QSTR_fvk)?.try_into()?;
        let fvk = FullViewingKey::from_bytes(&fvk_bytes).ok_or(Error::TypeError)?;
        Some((&fvk).into())
    } else {
        None
    };
    let address: [u8; 43] = output_info.get(Qstr::MP_QSTR_address)?.try_into()?;
    let address = Address::from_raw_address_bytes(&address);
    let address = Option::from(address).ok_or(Error::TypeError)?; // TODO: ValueError

    let value: u64 = output_info.get(Qstr::MP_QSTR_value)?.try_into()?;
    let value = orchard::value::NoteValue::from_raw(value);

    let memo = output_info.get(Qstr::MP_QSTR_memo)?;
    let memo: Option<[u8; 512]> = if memo.is_none() {
        None
    } else {
        Some(memo.try_into()?)
    };
    Ok((ovk, address, value, memo))
}

fn load_rng(config: Obj) -> Result<ChaCha12Rng, Error> {
    //let config: &Map = try_into_map!(config)?;
    try_parse_map!(config);
    let seed: [u8; 32] = config.get(Qstr::MP_QSTR_seed)?.try_into()?;
    let mut rng = ChaCha12Rng::from_seed(seed);
    let pos: u64 = config.get(Qstr::MP_QSTR_pos)?.try_into()?;
    rng.set_word_pos(pos as u128);
    Ok(rng)
}

fn save_rng(rng: ChaCha12Rng, config: Obj) -> Result<(), Error> {
    let mut dict: Gc<Dict> = config.try_into()?;
    let mut map = unsafe { Gc::as_mut(&mut dict) }.map_mut();
    map.set_obj(
        Qstr::MP_QSTR_pos.into(),
        (rng.get_word_pos() as u64).try_into()?,
    );
    Ok(())
}

#[no_mangle]
pub extern "C" fn orchardlib_shield(action_info: Obj, rng_config: Obj) -> Obj {
    let block = || {
        //let action_info: &Map = try_into_map!(action_info)?;
        try_parse_map!(action_info);

        let spend_info = action_info
            .get(Qstr::MP_QSTR_spend_info)
            .and_then(parse_spend_info)
            .ok();

        let output_info = action_info
            .get(Qstr::MP_QSTR_output_info)
            .and_then(parse_output_info)
            .ok();

        //let rng = trezorhal::random::HardwareRandomness;
        let mut rng = load_rng(rng_config)?;
        let action = orchard::hww::shield(spend_info, output_info, &mut rng);
        save_rng(rng, rng_config)?;

        let items: [(Qstr, Obj); 8] = [
            (Qstr::MP_QSTR_cv, action.cv_net().to_bytes().try_into()?),
            (Qstr::MP_QSTR_nf, action.nullifier().to_bytes().try_into()?),
            (Qstr::MP_QSTR_rk, <[u8; 32]>::from(action.rk()).try_into()?),
            (Qstr::MP_QSTR_cmx, action.cmx().to_bytes().try_into()?),
            (
                Qstr::MP_QSTR_epk,
                action.encrypted_note().epk_bytes.try_into()?,
            ),
            (
                Qstr::MP_QSTR_enc_ciphertext,
                action.encrypted_note().enc_ciphertext.try_into()?,
            ),
            (
                Qstr::MP_QSTR_out_ciphertext,
                action.encrypted_note().out_ciphertext.try_into()?,
            ),
            (
                Qstr::MP_QSTR_alpha,
                action.authorization().alpha.to_repr().try_into()?,
            ),
        ];

        let mut result = Dict::alloc_with_capacity(8)?;
        let mut map = unsafe { Gc::as_mut(&mut result) }.map_mut();
        for (key, value) in items.iter() {
            map.set(*key, *value)?
        }

        Ok(Obj::from(result))
    };
    unsafe { util::try_or_raise(block) }
}

impl From<TryFromSliceError> for Error {
    fn from(_e: TryFromSliceError) -> Error {
        Error::OutOfRange
    }
}

/// Returns Orchard Full Viewing Key.
fn get_sk(sk: Obj) -> Result<SpendingKey, Error> {
    let sk_bytes: [u8; 32] = sk.try_into()?;

    // SpendingKey is not valid with a negligible probability.
    let sk = SpendingKey::from_bytes(sk_bytes);
    // conversion from CtOption to Option
    let sk: Option<SpendingKey> = sk.into();
    let sk = sk.ok_or_else(|| {
        let err_msg =
            unsafe { CStr::from_bytes_with_nul_unchecked("Invalid Spending Key\0".as_bytes()) };
        Error::ValueError(err_msg)
    })?;

    Ok(sk)
}

#[no_mangle]
pub extern "C" fn orchardlib_get_full_viewing_key(sk: Obj) -> Obj {
    let block = || {
        let sk = get_sk(sk)?;
        let fvk: FullViewingKey = (&sk).into();
        let fvk_bytes = fvk.to_bytes();
        let fvk_obj = Obj::try_from(&fvk_bytes[..])?;
        Ok(fvk_obj)
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn orchardlib_get_incoming_viewing_key(sk: Obj) -> Obj {
    let block = || {
        let sk = get_sk(sk)?;
        let fvk: FullViewingKey = (&sk).into();
        let ivk: IncomingViewingKey = (&fvk).into();
        let ivk_bytes = ivk.to_bytes();
        let ivk_obj = Obj::try_from(&ivk_bytes[..])?;
        Ok(ivk_obj)
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn orchardlib_get_address(sk: Obj, diversifier_index: Obj) -> Obj {
    let block = || {
        let sk = get_sk(sk)?;
        let fvk: FullViewingKey = (&sk).into();
        let diversifier_index: u64 = diversifier_index.try_into()?;
        let addr = fvk.address_at(diversifier_index);
        let addr_bytes = addr.to_raw_address_bytes();
        let addr_obj = Obj::try_from(&addr_bytes[..])?;
        Ok(addr_obj)
    };
    unsafe { util::try_or_raise(block) }
}

// Length of f4jumbled message must be in range 48..=4194368
impl From<f4jumble::Error> for Error {
    fn from(_e: f4jumble::Error) -> Error {
        Error::OutOfRange
    }
}

#[no_mangle]
pub extern "C" fn orchardlib_f4jumble(message: Obj) -> Obj {
    let block = || {
        let mut message: BufferMut = message.try_into()?;
        let _ = f4jumble::f4jumble_mut(message.deref_mut())?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub extern "C" fn orchardlib_f4jumble_inv(message: Obj) -> Obj {
    let block = || {
        let mut message: BufferMut = message.try_into()?;
        let _ = f4jumble::f4jumble_inv_mut(message.deref_mut())?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}
