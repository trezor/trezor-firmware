# Changelog

## Version 0.3.3 (2023-08-01)

- Add support for `no_std`

## Version 0.3.2 (2023-06-03)

- Bump version

## Version 0.3.1 (2022-08-31)

- Fix docs

## Version 0.3.0 (2022-08-31)

- Make operator overloading of `Mul`, `Add` and `Sub` more flexible.
  This may break compilation in some cases, since types are more generic now.
- Add `AnimWithDur` for easier composition of animations that have a fixed duration
- Internal refactoring: split into multiple modules
- Implement `Anim::{fst,snd,copied}`
- Implement `AnimWithDur::{sum,mean}` and simple linear regression
- Implement `Anim::{into_fn,into_box_fn}`

## Version 0.2.6 (2020-08-17)

- Make exponential slowdown of compile times less likely
- Add `cycle`
- Add `quadratic`

## Version 0.2.5 (2020-07-18)

- Add `Anim::repeat`, `Anim::hold` and `Anim::seq_continue`
- Allow boxed animations
- Expose `easer` library

## Version 0.2.4 (2020-07-16)

Yanked.

## Version 0.2.3 (2020-04-28)

- Fix compilation issue on rustc 1.43.0 (<https://github.com/leod/pareen/pull/7>)

## Version 0.2.1 (2020-01-18)

- Implement `Anim::as_ref`

## Version 0.2.0 (2020-01-13)

- `squeeze` no longer switches to a default value outside of the given range.
 Use `squeeze_and_surround` as a replacement.

## Version 0.1.3 (2019-12-03)

- Render README.md on crates.io

## Version 0.1.2 (2019-12-02)

- No change

## Version 0.1.1 (2019-12-02)

- Improve documentation

## Version 0.1.0 (2019-12-02)

- Initial version
