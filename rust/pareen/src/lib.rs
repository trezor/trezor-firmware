//! Pareen is a small library for *par*ameterized inbetw*een*ing.
//! The intended application is in game programming, where you sometimes have
//! two discrete game states between which you want to transition smoothly
//! for visualization purposes.
//!
//! Pareen gives you tools for composing animations that are parameterized by
//! time (i.e. mappings from time to some animated value) without constantly
//! having to pass around time variables; it hides the plumbing, so that you
//! need to provide time only once: when evaluating the animation.
//!
//! Animations are composed similarly to Rust's iterators, so no memory
//! allocations are necessary.
//! ## Examples
//!
//! ```rust
//! # use assert_approx_eq::assert_approx_eq;
//! // An animation returning a constant value
//! let anim1 = pareen::constant(1.0f64);
//!
//! // Animations can be evaluated at any time
//! let value = anim1.eval(0.5);
//!
//! // Animations can be played in sequence
//! let anim2 = anim1.seq(0.7, pareen::prop(0.25) + 0.5);
//!
#![cfg_attr(
    any(feature = "std", feature = "libm"),
    doc = r##"
// Animations can be composed and transformed in various ways
let anim3 = anim2
    .lerp(pareen::circle().cos())
    .scale_min_max(5.0, 10.0)
    .backwards(1.0)
    .squeeze(0.5..=1.0);

let anim4 = pareen::cubic(&[1.0, 2.0, 3.0, 4.0]) - anim3;

let value = anim4.eval(1.0);
assert_approx_eq!(value, 0.0);
"##
)]
//! ```

#![no_std]

mod anim;
#[cfg(feature = "alloc")]
mod anim_box;
mod anim_with_dur;
mod arithmetic;
mod primitives;

pub mod stats;

#[cfg(all(feature = "easer", any(feature = "std", feature = "libm")))]
mod easer_combinators;

pub use anim::{cond, lerp, Anim, Fun};
#[cfg(feature = "alloc")]
pub use anim_box::AnimBox;
pub use anim_with_dur::{slice, AnimWithDur};
pub use primitives::{
    circle, constant, cubic, cycle, fun, half_circle, id, prop, quadratic, quarter_circle,
};
pub use stats::{simple_linear_regression, simple_linear_regression_with_slope};

#[cfg(all(feature = "easer", any(feature = "std", feature = "libm")))]
pub use easer;

#[cfg(all(feature = "easer", any(feature = "std", feature = "libm")))]
pub use easer_combinators::{ease_in, ease_in_out, ease_out};
