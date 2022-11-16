//! The Poseidon permutation lightweight implementation
//! Poseidon specification: https://eprint.iacr.org/2019/458
//! Orchard instantiation: https://zips.z.cash/protocol/protocol.pdf#poseidonhash

use core::{iter, ops::Deref};

use crate::micropython::{
    gc::Gc,
    map::Map,
    module::Module,
    obj::Obj,
    qstr::Qstr,
    util,
    wrap::{Wrappable, Wrapped},
};
use constants::MDS;
use pasta_curves::{arithmetic::FieldExt, group::ff::Field, Fp};

mod constants;
mod constants_gen;
#[cfg(test)]
mod tests;
use constants_gen::ConstantsGenerator;

/// The type used to hold permutation state.
type State = [Fp; 3];

#[inline]
fn sbox(x: Fp) -> Fp {
    x.pow_vartime(&[5])
}

#[inline]
fn full_round_sbox_layer(state: &mut State) {
    state[0] = sbox(state[0]);
    state[1] = sbox(state[1]);
    state[2] = sbox(state[2]);
}

#[inline]
fn half_round_sbox_layer(state: &mut State) {
    state[0] = sbox(state[0]);
}

#[inline]
fn add_round_constants(state: &mut State, rcs: &State) {
    state[0] += rcs[0];
    state[1] += rcs[1];
    state[2] += rcs[2];
}

#[inline]
fn apply_mds(state: &mut State) {
    let mut new_state = [Fp::zero(); 3];
    for i in 0..3 {
        for j in 0..3 {
            new_state[i] += MDS[i][j] * state[j];
        }
    }
    *state = new_state;
}

/// Runs the Poseidon permutation on the given state.
pub(crate) fn permute(state: &mut State) {
    let rounds = iter::empty()
        .chain(iter::repeat(true).take(4))
        .chain(iter::repeat(false).take(56))
        .chain(iter::repeat(true).take(4));

    let round_constants = ConstantsGenerator::new();

    for (is_full_round, rcs) in rounds.zip(round_constants) {
        add_round_constants(state, &rcs);
        if is_full_round {
            full_round_sbox_layer(state);
        } else {
            half_round_sbox_layer(state);
        }
        apply_mds(state);
    }
}

/// Poseidon hash
pub fn hash(x: Fp, y: Fp) -> Fp {
    let mut state = [x, y, Fp::from_u128((2 as u128) << 64)];
    permute(&mut state);
    state[0]
}

#[no_mangle]
unsafe extern "C" fn poseidon_wrapper(nk: Obj, rho: Obj) -> Obj {
    let block = || {
        let nk: Gc<Wrapped<Fp>> = nk.try_into()?;
        let nk: Fp = nk.deref().inner().clone();
        let rho: Gc<Wrapped<Fp>> = rho.try_into()?;
        let rho: Fp = rho.deref().inner().clone();

        hash(nk, rho).wrap()
    };
    unsafe { util::try_or_raise(block) }
}

#[no_mangle]
pub static mp_module_trezorposeidon: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorposeidon.to_obj(),
    /// def poseidon(x: Fp, y: Fp) -> Fp:
    ///     """Poseidon hash function."""
    Qstr::MP_QSTR_poseidon => obj_fn_2!(poseidon_wrapper).as_obj(),
};
