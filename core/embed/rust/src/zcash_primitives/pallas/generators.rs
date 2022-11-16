//! Precomputed Orchard generators.

use crate::{
    error::Error,
    micropython::{ffi, obj::Obj, qstr::Qstr, typ::Type, util, wrap::Wrappable},
};
use pasta_curves::{
    arithmetic::CurveAffine,
    pallas::{Affine, Point},
    Fp,
};

pub static GENERATORS_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_generators,
    attr_fn: attr_fn,
};

unsafe extern "C" fn attr_fn(_self_in: Obj, attr: ffi::qstr, dest: *mut Obj) {
    let block = || {
        let attr = Qstr::from_u16(attr as _);
        let (x, y) = get_by_name(attr)?;
        let affine_point: Affine = unwrap!(Option::from(Affine::from_xy(x, y)));
        let point: Point = affine_point.into();
        unsafe {
            if dest.read().is_null() {
                // Load attribute.
                dest.write(point.wrap()?);
                Ok(())
            } else {
                // Set attribute.
                Err(Error::TypeError)
            }
        }
    };
    unsafe { util::try_or_raise(block) }
}

#[inline]
fn get_by_name(name: Qstr) -> Result<(Fp, Fp), Error> {
    match name {
        Qstr::MP_QSTR_SPENDING_KEY_BASE => Ok((
            Fp::from_raw([
                0x8d1a7284b875c963,
                0xc7f0ce37b70a10c,
                0x3b8d187c3e5f445f,
                0x375523b328f1d606,
            ]),
            Fp::from_raw([
                0x4ce33e817b0c3bc9,
                0xdfc914fec005bdd8,
                0x7b10bcfcfed624fb,
                0x1ad0357fdf1a66db,
            ]),
        )),
        Qstr::MP_QSTR_NULLIFIER_K_BASE => Ok((
            Fp::from_raw([
                0xd36f6aa7e447ca75,
                0x5e7eb192ccb5db9b,
                0x2e375571faf4c9cf,
                0x25e7aa169ca8198d,
            ]),
            Fp::from_raw([
                0x2db8dce21ae001cc,
                0x5fe0a49ec1c1b433,
                0x880473442008ff75,
                0x155c1f851b1a3384,
            ]),
        )),
        Qstr::MP_QSTR_VALUE_COMMITMENT_VALUE_BASE => Ok((
            Fp::from_raw([
                0x2aa7bd6e3af94367,
                0xfe04a37f2b5a7c8c,
                0xf7a86a704f9bb232,
                0x2f70597a8e3d0f42,
            ]),
            Fp::from_raw([
                0xa413c47eaf5af28e,
                0x1d9ea766a7ffe3db,
                0x1e917f63136d6c42,
                0x2d0e5169311919af,
            ]),
        )),
        Qstr::MP_QSTR_VALUE_COMMITMENT_RANDOMNESS_BASE => Ok((
            Fp::from_raw([
                0xec3c668883c5a91,
                0x406ed745ee90802f,
                0x4f66235bea8d2048,
                0x7f444550fa409bb,
            ]),
            Fp::from_raw([
                0xe2f46c8a772d9ca,
                0x279229f1f3928146,
                0x21562cc9e46fb7c2,
                0x24136777af26628c,
            ]),
        )),
        Qstr::MP_QSTR_NOTE_COMMITMENT_BASE => Ok((
            Fp::from_raw([
                0x2c022c480ffc6e13,
                0x239ec55cfc14a47c,
                0xcd239fab936f3df2,
                0x26b206c328a94533,
            ]),
            Fp::from_raw([
                0xc34153c622cf37e3,
                0x79c7c07823e0dcf6,
                0xa9541a2f2366e1c6,
                0x3cde564b686dc04c,
            ]),
        )),
        Qstr::MP_QSTR_NOTE_COMMITMENT_Q => Ok((
            Fp::from_raw([
                0x320eba0940a8745d,
                0xc5960f5afd46dd2a,
                0xf79ff2b479b0ed5d,
                0x178007a056fbcd0d,
            ]),
            Fp::from_raw([
                0x87270a5a7349ac63,
                0x8822128881db5e9e,
                0x4ebec2d96ef4c92c,
                0x32a058938ac67083,
            ]),
        )),
        Qstr::MP_QSTR_IVK_COMMITMENT_BASE => Ok((
            Fp::from_raw([
                0x9823486e5ff8a118,
                0x2957fe2d31aedc7,
                0x1634290a40808948,
                0x25a22ccd5070134e,
            ]),
            Fp::from_raw([
                0x3fe793b3e37fdda9,
                0x6b4442fb1b58a6c7,
                0xc2c890c4284b5794,
                0x29cfd29966a2faeb,
            ]),
        )),
        Qstr::MP_QSTR_IVK_COMMITMENT_Q => Ok((
            Fp::from_raw([
                0x6bcb2f92790f82f2,
                0x421bcc245128a232,
                0x7dcc81b85aa241fa,
                0x5bc0cf14aa9c811,
            ]),
            Fp::from_raw([
                0xbe5ae5cecfaddebe,
                0x46c4351dc96da5f1,
                0xef59074620de054b,
                0x1b014cf6d41abee6,
            ]),
        )),
        _ => Err(Error::AttributeError(name)),
    }
}
