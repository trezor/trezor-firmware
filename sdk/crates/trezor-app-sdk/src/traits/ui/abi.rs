//! Pins the `UiV1` ABI to a recorded file, `abi/ui_v1.json`.
//!
//! An app and the firmware are built apart, so the vtable and the types it
//! carries must not change by accident. The test writes three things down and
//! compares them with the file:
//!
//! - `layout`: stabby's report of each pinned type, its fields and their types
//!   nested all the way down. It has no sizes, so it reads the same on every
//!   target, and the same report means the same layout. The vtable's report
//!   names its methods in slot order but not their signatures, so each type a
//!   method takes or returns is pinned on its own.
//! - `discriminants`: the number of every variant, which the report leaves out
//!   and core reads to tell the variants apart.
//! - `words`: the size of the types with a reserved variant, in words, so a
//!   reader sees how much room they take.
//!
//! A change shows up as a diff of that file, which review then accepts, or the
//! change becomes a new version instead. Record an intended change with
//! `make sdk_abi`.

use std::collections::HashSet;
use std::string::{String, ToString};
use std::vec::Vec;
use std::{format, fs, vec};

use stabby::IStable;
use stabby::abi::report::{TyTy, TypeReport};

use super::{
    Answer, DoneRequest, FieldKind, ProgressV1, ReviewRequest, SourceRef, TrezorUiEnumV1,
    TrezorUiResultV1, UiV1Vtable, VerifyRequest, WireField,
};
use crate::Result;
use crate::modui::TextSource;
use crate::structs::{OptStrSlice, Slice, StrSlice};

const FIXTURE: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/abi/ui_v1.json");

/// The pinned types, by the name they are recorded under.
fn pinned() -> Vec<(&'static str, &'static TypeReport)> {
    vec![
        ("UiV1Vtable", <UiV1Vtable as IStable>::REPORT),
        ("TrezorUiEnumV1", <TrezorUiEnumV1 as IStable>::REPORT),
        ("TrezorUiResultV1", <TrezorUiResultV1 as IStable>::REPORT),
        ("ProgressV1", <ProgressV1 as IStable>::REPORT),
    ]
}

/// One line per type, indented by depth, fields in source order. A type
/// already written in full is written again by name only.
fn render(
    label: &str,
    report: &TypeReport,
    depth: usize,
    seen: &mut HashSet<String>,
    out: &mut Vec<String>,
) {
    let kind = match report.tyty {
        TyTy::Struct => String::from("Struct"),
        TyTy::Enum(repr) => format!("Enum({repr})"),
        TyTy::Union => String::from("Union"),
    };
    let version = match report.version {
        0 => String::new(),
        version => format!(" v{version}"),
    };
    let head = format!(
        "{:indent$}{label}{kind} {}::{}{version}",
        "",
        report.module,
        report.name,
        indent = depth * 2
    );
    if !seen.insert(report.to_string()) {
        out.push(format!("{head} (as above)"));
        return;
    }
    out.push(head);
    // stabby lists the fields last first.
    let fields: Vec<_> = report.fields().collect();
    for field in fields.into_iter().rev() {
        render(&format!("{}: ", field.name), field.ty, depth + 1, seen, out);
    }
}

fn layout(report: &TypeReport) -> Vec<String> {
    let mut lines = Vec::new();
    render("", report, 0, &mut HashSet::new(), &mut lines);
    lines
}

/// `name = number` for each variant, checked against the report so that no
/// variant is left out or misnamed.
fn numbered(report: &TypeReport, variants: &[(&str, u8)]) -> Vec<String> {
    let mut names: Vec<&str> = report.fields().map(|field| field.name.as_str()).collect();
    names.reverse();
    let listed: Vec<&str> = variants.iter().map(|(name, _)| *name).collect();
    assert_eq!(listed, names, "{}: list every variant here", report.name);
    variants
        .iter()
        .map(|(name, number)| format!("{name} = {number}"))
        .collect()
}

/// The tag of a `#[repr(C, u8)]` enum: its first byte.
fn tag<T>(value: &T) -> u8 {
    // SAFETY: only called on `#[repr(C, u8)]` enums, whose first byte is the
    // tag, and `value` is a live reference.
    unsafe { *(value as *const T).cast::<u8>() }
}

/// A source that is never read; it only has to exist.
struct Unread;

impl TextSource for Unread {
    fn read(&self, _offset: u32, _buf: &mut [u8]) -> Result<()> {
        Ok(())
    }
}

fn request_numbers() -> Vec<String> {
    let s: StrSlice = "".into();
    let verify = VerifyRequest {
        step: s,
        value: s,
        account: OptStrSlice::NONE,
        path: OptStrSlice::NONE,
    };
    let variants = [
        (
            "Review",
            tag(&TrezorUiEnumV1::Review(ReviewRequest {
                step: s,
                title: s,
                fields: Slice::new(&[]),
                extras: Slice::new(&[]),
                answer: Answer::Confirm,
            })),
        ),
        ("VerifyAddress", tag(&TrezorUiEnumV1::VerifyAddress(verify))),
        ("VerifyPubkey", tag(&TrezorUiEnumV1::VerifyPubkey(verify))),
        (
            "Done",
            tag(&TrezorUiEnumV1::Done(DoneRequest { step: s, text: s })),
        ),
        ("Reserved", tag(&TrezorUiEnumV1::Reserved([0; 16]))),
    ];
    // Core tells the requests apart by these constants.
    let consts = [
        TrezorUiEnumV1::REVIEW,
        TrezorUiEnumV1::VERIFY_ADDRESS,
        TrezorUiEnumV1::VERIFY_PUBKEY,
        TrezorUiEnumV1::DONE,
    ];
    for ((name, number), constant) in variants.iter().zip(consts) {
        assert_eq!(u16::from(*number), constant, "TrezorUiEnumV1::{name}");
    }
    numbered(<TrezorUiEnumV1 as IStable>::REPORT, &variants)
}

fn field_numbers() -> Vec<String> {
    let s: StrSlice = "".into();
    let source = Unread;
    let variants = [
        (
            "Text",
            WireField::Text { label: s, value: s },
            FieldKind::Text,
        ),
        (
            "Amount",
            WireField::Amount {
                label: s,
                value: s,
                ticker: s,
            },
            FieldKind::Amount,
        ),
        (
            "Address",
            WireField::Address { label: s, value: s },
            FieldKind::Address,
        ),
        (
            "TextSource",
            WireField::TextSource {
                label: s,
                len: 0,
                source: SourceRef::new((&source).into()),
            },
            FieldKind::TextSource,
        ),
        ("Note", WireField::Note { text: s }, FieldKind::Note),
        (
            "Warning",
            WireField::Warning { text: s },
            FieldKind::Warning,
        ),
    ];
    // Each kind has the number of its variant.
    for (name, field, kind) in &variants {
        assert_eq!(tag(field), *kind as u8, "WireField::{name}");
    }
    let mut numbers: Vec<(&str, u8)> = variants
        .iter()
        .map(|(name, field, _)| (*name, tag(field)))
        .collect();
    numbers.push(("Reserved", tag(&WireField::Reserved([0; 8]))));
    numbered(<WireField as IStable>::REPORT, &numbers)
}

fn discriminants() -> Vec<(&'static str, Vec<String>)> {
    vec![
        ("TrezorUiEnumV1", request_numbers()),
        ("WireField", field_numbers()),
        (
            "Answer",
            numbered(
                <Answer as IStable>::REPORT,
                &[
                    ("Confirm", Answer::Confirm as u8),
                    ("Strong", Answer::Strong as u8),
                    ("Danger", Answer::Danger as u8),
                    ("Details", Answer::Details as u8),
                ],
            ),
        ),
        (
            "TrezorUiResultV1",
            numbered(
                <TrezorUiResultV1 as IStable>::REPORT,
                &[
                    ("Confirmed", TrezorUiResultV1::Confirmed as u8),
                    ("Cancelled", TrezorUiResultV1::Cancelled as u8),
                    ("ShowDetails", TrezorUiResultV1::ShowDetails as u8),
                ],
            ),
        ),
    ]
}

fn words<T>() -> usize {
    core::mem::size_of::<T>().div_ceil(core::mem::size_of::<usize>())
}

fn quote(line: &str) -> String {
    format!("\"{}\"", line.replace('\\', "\\\\").replace('"', "\\\""))
}

/// A JSON object of string lists, one string per line.
fn section(name: &str, entries: &[(&str, Vec<String>)]) -> String {
    let entries: Vec<String> = entries
        .iter()
        .map(|(key, lines)| {
            let lines: Vec<String> = lines
                .iter()
                .map(|line| format!("      {}", quote(line)))
                .collect();
            format!("    {}: [\n{}\n    ]", quote(key), lines.join(",\n"))
        })
        .collect();
    format!("  {}: {{\n{}\n  }}", quote(name), entries.join(",\n"))
}

/// The file as it should read.
fn expected() -> String {
    let layouts: Vec<(&str, Vec<String>)> = pinned()
        .into_iter()
        .map(|(name, report)| (name, layout(report)))
        .collect();
    let sizes = format!(
        "  \"words\": {{\n    \"TrezorUiEnumV1\": {},\n    \"WireField\": {}\n  }}",
        words::<TrezorUiEnumV1>(),
        words::<WireField>()
    );
    format!(
        "{{\n{},\n{},\n{}\n}}\n",
        section("layout", &layouts),
        section("discriminants", &discriminants()),
        sizes
    )
}

#[test]
fn the_ui_abi_matches_the_recorded_one() {
    let expected = expected();
    if std::env::var_os("TREZOR_ABI_RECORD").is_some() {
        fs::write(FIXTURE, &expected).unwrap();
        return;
    }
    let recorded = fs::read_to_string(FIXTURE).unwrap_or_default();
    assert!(
        recorded == expected,
        "the UiV1 ABI changed. If that is intended and nothing shipped with the old \
         layout, record it with `make sdk_abi` and let review accept the diff of \
         {FIXTURE}. Otherwise make the change a new version (`…V2` with its own \
         `…_v2` method)."
    );
}
