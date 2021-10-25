use crate::micropython::buffer::Buffer;
use crate::micropython::obj::Obj;
extern crate alloc;
use alloc::borrow::ToOwned;
use alloc::string::String;
use bech32::{self, ToBase32, Variant};
use core::convert::TryFrom;
use core::convert::TryInto;
use core::ops::Deref;
use orchard::keys::{FullViewingKey, SpendingKey};

fn bech32m_encode(hrp: &str, data: &[u8]) -> String {
    bech32::encode(hrp, data.to_base32(), Variant::Bech32m).expect("hrp is invalid")
}

#[no_mangle]
pub extern "C" fn zcash_get_fvk(seed: Obj, account: Obj) -> Obj {
    unimplemented!()
}

#[no_mangle]
pub extern "C" fn zcash_get_address(seed: Obj, account: Obj, diversifier_index: Obj) -> Obj {
    // TODO: some error handeling
    let seed = Buffer::try_from(seed).unwrap();
    let account: u32 = account.try_into().unwrap();
    let diversifier_index = u64::try_from(diversifier_index).unwrap();

    // TODO: some error handeling
    let sk = SpendingKey::from_zip32_seed(&seed.deref(), 133, account).unwrap();
    let fvk: FullViewingKey = (&sk).into();
    let addr = fvk.address_at(diversifier_index);
    let addr_bytes = addr.to_raw_address_bytes();

    // TODO: move bech32m to python level
    let addr_enc = bech32m_encode("otest", &addr_bytes);
    let addr_enc = addr_enc.to_owned();
    Obj::try_from(&addr_enc[..]).unwrap()
}
