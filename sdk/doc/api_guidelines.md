# API Guidelines Checklist

This tracks conformance of `trezor-app-sdk` and `modular-xtask` to the
[Rust API Guidelines checklist](https://rust-lang.github.io/api-guidelines/checklist.html).
Both crates are intended for eventual publication to crates.io, so their public
API surface should hold up to this checklist before that happens.

## Status legend

| Symbol | Meaning |
| --- | --- |
| ✅ | Pass |
| ⚠️ | Partial — meets the guideline in some places, not others |
| ❌ | Fail |
| ➖ | N/A — guideline doesn't apply to this crate |
| ❓ | TBD — not yet audited |

## Methodology

Most of this checklist is design judgment (e.g. "Only smart pointers implement
`Deref`", "Sealed traits protect against downstream implementations") and
can't be verified mechanically. A small subset is checked automatically:

- **Documentation** — both crates now build with `#![warn(missing_docs)]`, so
  `cargo doc`/`cargo check` output flags public items lacking a doc comment.
  This only proves *presence* of a doc comment, not that it's a good one, and
  doesn't check for rustdoc examples (that check is nightly-only).
- **Debuggability** — `cargo clippy -- -W clippy::missing_debug_implementations`
  can be run manually to spot public types missing `Debug`; it isn't wired
  into CI yet.
- **Necessities** — `Cargo.toml` metadata fields are a plain presence check.

Everything else below is `❓ TBD` pending a manual read-through of each
module's public API. Don't treat a `❓` as a pass — it means nobody has
looked yet.

---

## Naming

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-CASE — Casing conforms to RFC 430 (`UpperCamelCase`, `snake_case`, `SCREAMING_SNAKE_CASE`) | ❓ | ❓ | |
| C-CONV — Ad-hoc conversions follow `as_`, `to_`, `into_` conventions | ❓ | ❓ | |
| C-GETTER — Getter names follow Rust convention (no `get_` prefix, except e.g. `Cell::get`) | ❓ | ❓ | |
| C-ITER — Methods that produce iterators follow `iter`, `iter_mut`, `into_iter` | ❓ | ❓ | |
| C-ITER-TY — Iterator type names match the methods that produce them | ❓ | ❓ | |
| C-FEATURE — Feature names are free of placeholder words | ❓ | ➖ | modular-xtask has no Cargo features |
| C-WORD-ORDER — Names use a consistent word order | ❓ | ❓ | |

## Interoperability

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-COMMON-TRAITS — Types eagerly implement common traits (`Copy`, `Clone`, `Eq`, `PartialEq`, `Ord`, `PartialOrd`, `Hash`, `Debug`, `Display`, `Default`) | ❓ | ❓ | |
| C-CONV-TRAITS — Conversions use the standard traits `From`, `AsRef`, `AsMut` | ❓ | ❓ | |
| C-COLLECT — Collections implement `FromIterator` and `Extend` | ❓ | ➖ | neither crate exposes custom collection types (TBC) |
| C-SERDE — Data structures implement `Serialize`/`Deserialize` | ❓ | ❓ | trezor-app-sdk uses `rkyv`, not serde — check whether that satisfies intent |
| C-SEND-SYNC — Types are `Send` and `Sync` where possible | ❓ | ❓ | trezor-app-sdk is `no_std` with `critical_section` — worth explicit review |
| C-GOOD-ERR — Error types are meaningful and well-behaved | ❓ | ❓ | |
| C-NUM-FMT — Binary number types provide `Hex`/`Octal`/`Binary` formatting | ❓ | ➖ | |
| C-RW-VALUE — Generic reader/writer functions take `R: Read` / `W: Write` by value | ➖ | ❓ | trezor-app-sdk is `no_std`, no `std::io::{Read,Write}` |

## Macros

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-EVOCATIVE — Input syntax is evocative of the output | ❓ | ➖ | trezor-app-sdk exports macros from `macros.rs` — needs review; modular-xtask exports none publicly |
| C-MACRO-ATTR — Item macros work anywhere an item is allowed | ❓ | ➖ | |
| C-ANYWHERE — Item macros work in statement position too | ❓ | ➖ | |
| C-MACRO-VIS — Item macros support visibility specifiers | ❓ | ➖ | |
| C-MACRO-TY — Item macros compose well for any user-defined types | ❓ | ➖ | |

## Documentation

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-CRATE-DOC — Crate-level docs are thorough and include examples | ⚠️ | ❓ | trezor-app-sdk has a crate-level doc comment (`lib.rs`) but no examples; modular-xtask has none |
| C-EXAMPLE — All public items have rustdoc examples | ❌ | ❌ | `structs.rs` (~27 pub items) is almost entirely undocumented; `args.rs`/`cargo.rs` in modular-xtask are undocumented. `#![warn(missing_docs)]` now flags these; fixing the backlog is follow-up work |
| C-QUESTION-MARK — Examples use `?`, not `try!`, not `unwrap` | ➖ | ➖ | no examples exist yet to check |
| C-FAILURE — Function docs include error, panic, safety considerations | ❓ | ❓ | |
| C-LINK — Prose contains hyperlinks to relevant things | ❓ | ❓ | |
| C-METADATA — `Cargo.toml` includes all common metadata (`authors`, `description`, `license`, `homepage`, `documentation`, `repository`, `readme`, `keywords`, `categories`) | ⚠️ | ⚠️ | Both have `description`+`license` now (see [Necessities](#necessities)); `homepage`/`documentation`/`repository`/`readme`/`keywords`/`categories`/`authors` are missing from both — fill in before actual publish |
| C-HTML-ROOT — Crate sets `html_root_url` attribute | ❌ | ❌ | not set in either crate |
| C-RELNOTES — Release notes document all significant changes | ❓ | ❓ | no CHANGELOG found for either crate |
| C-HIDDEN — Rustdoc doesn't show unhelpful implementation details | ❓ | ❓ | |

## Predictability

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-SMART-PTR — Smart pointers don't add inherent methods | ❓ | ➖ | |
| C-CONV-SPECIFIC — Conversions live on the most specific type involved | ❓ | ❓ | |
| C-METHOD — Functions with a clear receiver are methods | ❓ | ❓ | |
| C-NO-OUT — Functions don't take out-parameters | ❓ | ❓ | |
| C-OVERLOAD — Operator overloads are unsurprising | ❓ | ➖ | |
| C-DEREF — Only smart pointers implement `Deref`/`DerefMut` | ❓ | ➖ | |
| C-CTOR — Constructors are static, inherent methods (e.g. `new()`) | ❓ | ❓ | |

## Flexibility

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-INTERMEDIATE — Functions expose intermediate results to avoid duplicate work | ❓ | ❓ | |
| C-CALLER-CONTROL — Caller decides where to copy and place data | ❓ | ❓ | relevant given `no_std`/no-alloc constraints on some feature combos |
| C-GENERIC — Functions minimize assumptions about parameters via generics | ❓ | ❓ | |
| C-OBJECT — Traits are object-safe if they may be useful as a trait object | ❓ | ❓ | |

## Type safety

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-NEWTYPE — Newtypes provide static distinctions | ❓ | ❓ | |
| C-CUSTOM-TYPE — Arguments convey meaning through types, not `bool`/`Option` | ❓ | ❓ | |
| C-BITFLAG — Types for a set of flags are `bitflags`, not enums | ❓ | ➖ | |
| C-BUILDER — Builders enable construction of complex values | ❓ | ➖ | modular-xtask's `Cmd`/args types are driven by `clap`, not a hand-rolled builder |

## Dependability

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-VALIDATE — Functions validate their arguments | ❓ | ❓ | |
| C-DTOR-FAIL — Destructors never fail | ❓ | ❓ | |
| C-DTOR-BLOCK — Destructors that may block have alternatives | ❓ | ❓ | |

## Debuggability

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-DEBUG — All public types implement `Debug` | ❓ | ❓ | run `cargo clippy -- -W clippy::missing_debug_implementations` in each crate and record findings here |
| C-DEBUG-NONEMPTY — `Debug` representation is never empty | ❓ | ❓ | |

## Future proofing

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-SEALED — Sealed traits protect against downstream implementations | ❓ | ❓ | |
| C-STRUCT-PRIVATE — Structs have private fields | ⚠️ | ❓ | `structs.rs` types have `pub` fields by design — they're the shared wire-format types read directly from archived `rkyv` form by core, so this is a deliberate, documented exception rather than an oversight; confirm the rest of the crate follows the guideline normally |
| C-NEWTYPE-HIDE — Newtypes encapsulate implementation details | ❓ | ❓ | |
| C-STRUCT-BOUNDS — Data structures don't duplicate derived trait bounds | ❓ | ❓ | |

## Necessities

| Item | trezor-app-sdk | modular-xtask | Notes |
| --- | --- | --- | --- |
| C-STABLE — Public dependencies of a stable crate are stable | ❓ | ❓ | neither crate has hit 1.0 yet (`version = "0.1.0"`) so this is less pressing today |
| C-PERMISSIVE — Crate and its dependencies have a permissive license | ✅ | ✅ | both now set `license = "GPL-3.0-only"`, matching this monorepo's `COPYING`/`LICENSE.md`. Note: GPL-3.0 is an unusual choice for a crate meant to be depended on (as opposed to an application) — worth a deliberate decision from whoever owns crates.io publishing, not just a default carried over from consistency |

---

## Follow-up work (not done in this pass)

- Fill in every `❓` row above by reading the actual module in question against
  the guideline's intent. Candidate modules: `structs.rs`, `ui.rs`, `crypto.rs`,
  `wire.rs`, `ipc.rs`, `service.rs`, `mock.rs`, `app_runtime.rs`, `log.rs`,
  `macros.rs`, `util.rs`, `print.rs`, `sysevent.rs`, `core_services.rs`,
  `low_level_api.rs`, `critical_section.rs`, `alloc_types.rs` (trezor-app-sdk);
  `args.rs`, `cargo.rs`, `helpers.rs`, `metadata.rs`, `armv8m.rs`, `binary.rs`,
  `postbuild.rs`, `pystyle.rs`, `translations.rs`, `upload.rs`,
  `device_tests.rs` (modular-xtask).
- Clear the `missing_docs` backlog, then flip `#![warn(missing_docs)]` to
  `#![deny(missing_docs)]` (or add `-D warnings` to the `cargo doc`/`cargo
  clippy` Makefile invocations) so regressions fail CI.
- Decide on and add the missing `Cargo.toml` metadata fields
  (`repository`, `keywords`, `categories`, `homepage`, `documentation`,
  `readme`, `authors`) before actual crates.io publication.
- Consider `cargo-deny`, `cargo-semver-checks`, and `cargo-license` for
  ongoing license/semver enforcement — none are set up in this repo yet.
