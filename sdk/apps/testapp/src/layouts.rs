//! One handler per modui layout: build the layout's parameters from the
//! request, call the layout, and hand its answer back.
//!
//! The API reference's examples are in [`crate::showcase`].

use core::str;

use trezor_app_sdk::modui::{self, Details, Extra, Field};
use trezor_app_sdk::{Error, Result, WireDecode, WireEncode, wire_request_raw};

use crate::ProstCodec;
use crate::alloc_types::Vec;
use crate::proto::messages::MessageType;
use crate::proto::testapp::{self as wire, ui_result::Reply};

// ============================================================================
// Handlers
// ============================================================================

pub fn review(m: wire::Review) -> Result<wire::UiResult> {
    decided(run_review(&m))
}

pub fn danger(m: wire::Danger) -> Result<wire::UiResult> {
    let fields = fields(&m.fields)?;
    decided(modui::danger(&m.step, &m.title, &fields))
}

pub fn details(m: wire::Details) -> Result<wire::UiResult> {
    let fields = fields(&m.fields)?;
    match modui::details(&m.step, &m.title, &fields) {
        Ok(Details::Show) => answer(Reply::ShowDetails),
        Ok(Details::Skip) => answer(Reply::Confirmed),
        Err(e) if e.code() == Error::Cancelled.code() => answer(Reply::Cancelled),
        Err(e) => Err(e),
    }
}

pub fn verify_address(m: wire::VerifyAddress) -> Result<wire::UiResult> {
    decided(modui::verify_address(
        &m.step,
        &m.value,
        m.account.as_deref(),
        m.path.as_deref(),
    ))
}

pub fn verify_pubkey(m: wire::VerifyPubkey) -> Result<wire::UiResult> {
    decided(modui::verify_pubkey(
        &m.step,
        &m.value,
        m.account.as_deref(),
        m.path.as_deref(),
    ))
}

pub fn done(m: wire::Done) -> Result<wire::UiResult> {
    modui::done(&m.step, &m.text);
    answer(Reply::Confirmed)
}

/// Runs a progress for as long as the host keeps it going: each tick asks the
/// host what next, and the progress ends when the host says so — or when the
/// exchange fails, since leaving the closure drops the progress either way.
pub fn show_progress(m: wire::ShowProgress) -> Result<wire::UiResult> {
    modui::progress(&m.label, m.total, |progress| -> Result<()> {
        loop {
            let tick = ProstCodec::encode(&wire::ProgressTick {});
            let (id, data) = wire_request_raw(&tick, MessageType::ProgressTick as u16)?;
            match (id as i32).try_into() {
                Ok(MessageType::ProgressStep) => {
                    let step: wire::ProgressStep = ProstCodec::decode(&data)?;
                    progress.step(step.units());
                }
                Ok(MessageType::ProgressLabel) => {
                    let label: wire::ProgressLabel = ProstCodec::decode(&data)?;
                    progress.label(&label.label);
                }
                Ok(MessageType::ProgressEnd) => {
                    let _: wire::ProgressEnd = ProstCodec::decode(&data)?;
                    return Ok(());
                }
                _ => return Err(Error::InvalidMessage),
            }
        }
    })?;
    // A progress asks nothing; it answers only that it ran.
    answer(Reply::Confirmed)
}

// ============================================================================
// Layouts
// ============================================================================

fn run_review(m: &wire::Review) -> Result<()> {
    let fields = fields(&m.fields)?;
    let extras = Extras::new(&m.extras)?;
    let offered = extras.as_slice();
    let review = modui::review(&m.step, &m.title, &fields).extras(&offered);
    if m.is_final() {
        review.confirm_final()
    } else {
        review.confirm()
    }
}

// ============================================================================
// Conversions
// ============================================================================

/// One wire fact as a [`Field`]. A text kind must carry UTF-8, and every kind
/// but a note and a warning must carry a label; anything else is refused before
/// the layout is called.
fn field(f: &wire::Field) -> Result<Field<'_>> {
    let text = || str::from_utf8(&f.value).map_err(|_| Error::InvalidArgument);
    Ok(match f.kind() {
        wire::FieldKind::Text => Field::text(label(f)?, text()?),
        wire::FieldKind::Amount => Field::amount(label(f)?, text()?),
        wire::FieldKind::Address => Field::address(label(f)?, text()?),
        wire::FieldKind::Data => Field::data(label(f)?, &f.value),
        wire::FieldKind::Note => Field::note(text()?),
        wire::FieldKind::Warning => Field::warning(text()?),
    })
}

fn fields(items: &[wire::Field]) -> Result<Vec<Field<'_>>> {
    items.iter().map(field).collect()
}

fn label(f: &wire::Field) -> Result<&str> {
    f.label.as_deref().ok_or(Error::InvalidArgument)
}

/// The extras of one review, kept alive while the review borrows them.
struct Extras<'a> {
    labels: Vec<&'a str>,
    fields: Vec<Vec<Field<'a>>>,
}

impl<'a> Extras<'a> {
    fn new(items: &'a [wire::Extra]) -> Result<Self> {
        Ok(Self {
            labels: items.iter().map(|item| item.label.as_str()).collect(),
            fields: items
                .iter()
                .map(|item| fields(&item.fields))
                .collect::<Result<_>>()?,
        })
    }

    /// One [`Extra`] per menu entry, borrowing the facts kept in `self`.
    fn as_slice(&self) -> Vec<Extra<'_>> {
        self.labels
            .iter()
            .zip(&self.fields)
            .map(|(&label, facts)| Extra::new(label, facts))
            .collect()
    }
}

/// A layout's answer, as the host receives it. A cancel is a reply on this
/// wire; any other error, such as a request the layout refuses, stays an
/// error and reaches the host as a `Failure`.
fn decided(outcome: Result<()>) -> Result<wire::UiResult> {
    match outcome {
        Ok(()) => answer(Reply::Confirmed),
        Err(e) if e.code() == Error::Cancelled.code() => answer(Reply::Cancelled),
        Err(e) => Err(e),
    }
}

fn answer(reply: Reply) -> Result<wire::UiResult> {
    Ok(wire::UiResult {
        reply: reply as i32,
    })
}
