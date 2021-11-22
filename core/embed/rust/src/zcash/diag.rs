use crate::micropython::{buffer::Buffer, obj::Obj};
use crate::util;
use core::{convert::TryFrom, ops::Deref};
use group::GroupEncoding;
use orchard::keys::{
    FullViewingKey, NullifierDerivingKey, SpendAuthorizingKey, SpendValidatingKey, SpendingKey,
};
use orchard::primitives::sinsemilla::{CommitDomain, HashDomain};

pub const COMMIT_IVK_PERSONALIZATION: &str = "z.cash:Orchard-CommitIvk";

fn as_u32_le(array: &[u8]) -> u32 {
    ((array[0] as u32) << 0)
        + ((array[1] as u32) << 8)
        + ((array[2] as u32) << 16)
        + ((array[3] as u32) << 24)
}

fn as_u32_be(array: &[u8]) -> u32 {
    ((array[0] as u32) << 24)
        + ((array[1] as u32) << 16)
        + ((array[2] as u32) << 8)
        + ((array[3] as u32) << 0)
}

#[no_mangle]
pub extern "C" fn zcash_diag(ins: Obj, data: Obj) -> Obj {
    let block = || {
        let ins = Buffer::try_from(ins)?;
        let ins = ins.deref();
        let data = Buffer::try_from(data)?;
        let data = data.deref();
        let nothing = [0u8; 0];
        let obj = match ins {
            b"hello_rust" => Obj::try_from(&b"hello from the rust"[..])?,
            b"fvk" => {
                let seed = [0u8; 32];
                let sk = SpendingKey::from_zip32_seed(&seed, 1, 0).unwrap();
                let fvk: FullViewingKey = (&sk).into();
                let fvk_bytes: [u8; 96] = fvk.to_bytes();
                Obj::try_from(&fvk_bytes[..])?
            }
            b"hash" => {
                let p = HashDomain::new("mytest");
                let m = [true; 96 * 8];
                let q = p.hash_to_point(m.iter().cloned()).unwrap();
                Obj::try_from(&q.to_bytes()[..])?
            }
            b"addr" => {
                let seed = [0u8; 32];
                let sk = SpendingKey::from_zip32_seed(&seed, 1, 0).unwrap();
                let fvk: FullViewingKey = (&sk).into();
                let addr = fvk.address_at(0u32);
                let addr_bytes = addr.to_raw_address_bytes();
                Obj::try_from(&addr_bytes[..])?
            }
            b"commit" => {
                let domain = CommitDomain::new(COMMIT_IVK_PERSONALIZATION);
                Obj::try_from(&nothing[..])?
            }
            b"nk" => {
                let seed = [0u8; 32];
                let sk = SpendingKey::from_zip32_seed(&seed, 1, 0).unwrap();
                let nk: NullifierDerivingKey = (&sk).into();
                Obj::try_from(&nk.to_bytes()[..])?
            }
            b"ask" => {
                let seed = [0u8; 32];
                let sk = SpendingKey::from_bytes(seed).unwrap();
                let ask: SpendAuthorizingKey = (&sk).into();
                Obj::try_from(&b"ask computed"[..])?
            }
            b"ak" => {
                let seed = [0u8; 32];
                let sk = SpendingKey::from_bytes(seed).unwrap();
                let ask: SpendAuthorizingKey = (&sk).into();
                let ak: SpendValidatingKey = (&ask).into();
                Obj::try_from(&ak.to_bytes()[..])?
            }
            b"alloc" => {
                let size = as_u32_be(data) as usize;
                let _ = vec![0u8; size];
                Obj::try_from(&b"allocation successed"[..])?
            }
            _ => Obj::try_from(&b"unknown instruction"[..])?,
        };
        Ok(obj)
    };
    unsafe { util::try_or_raise(block) }
}
