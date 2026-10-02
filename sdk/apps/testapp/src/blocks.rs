//! One handler per modui block: build the block's parameters from the
//! request, call the block, and hand its reply back as it came.

use trezor_app_sdk::modui::{
    self, Commitment, ExtraItem, Property, UiReply, confirm, notice, progress,
};
use trezor_app_sdk::{Error, Result, WireDecode, WireEncode, wire_request_raw};

use crate::ProstCodec;
use crate::alloc_types::Vec;
use crate::proto::messages::MessageType;
use crate::proto::testapp::{self as wire, ui_result::Reply};

// ============================================================================
// Handlers
// ============================================================================

pub fn confirm_action(m: wire::ConfirmAction) -> Result<wire::UiResult> {
    reply(run_confirm_action(&m)?)
}

pub fn confirm_value(m: wire::ConfirmValue) -> Result<wire::UiResult> {
    reply(run_confirm_value(&m)?)
}

pub fn confirm_data(m: wire::ConfirmData) -> Result<wire::UiResult> {
    let extras = Extras::new(&m.extras);
    reply(modui::confirm::data(modui::confirm::Data::new(
        &m.title,
        &m.data,
        m.subtitle.as_deref(),
        &m.br,
        &extras.items(),
        m.cancel(),
    ))?)
}

pub fn confirm_properties(m: wire::ConfirmProperties) -> Result<wire::UiResult> {
    reply(run_confirm_properties(&m)?)
}

pub fn confirm_summary(m: wire::ConfirmSummary) -> Result<wire::UiResult> {
    reply(run_confirm_summary(&m)?)
}

pub fn show_notice(m: wire::ShowNotice) -> Result<wire::UiResult> {
    reply(run_show_notice(&m)?)
}

/// Runs a progress for as long as the host keeps it going: each tick asks the
/// host what next, and the progress ends when the host says so — or when the
/// exchange fails, since leaving the closure drops the progress either way.
pub fn show_progress(m: wire::ShowProgress) -> Result<wire::UiResult> {
    let total = m
        .total
        .map_or(progress::Total::Unknown, progress::Total::Units);
    modui::progress::run_with(&m.label, total, |progress| -> Result<()> {
        loop {
            let tick = ProstCodec::encode(&wire::ProgressTick {});
            let (id, data) = wire_request_raw(&tick, MessageType::ProgressTick as u16)?;
            match (id as i32).try_into() {
                Ok(MessageType::ProgressStep) => {
                    let step: wire::ProgressStep = ProstCodec::decode(&data)?;
                    progress.step(step.units());
                }
                Ok(MessageType::ProgressEnd) => {
                    let _: wire::ProgressEnd = ProstCodec::decode(&data)?;
                    return Ok(());
                }
                _ => return Err(Error::InvalidMessage),
            }
        }
    })??;
    // A progress asks nothing; it answers only that it ran.
    reply(UiReply::Confirmed)
}

pub fn confirm_linear_flow(m: wire::ConfirmLinearFlow) -> Result<wire::UiResult> {
    // No block takes `back` yet, so the flag each step gets goes nowhere.
    let steps: Vec<_> = m
        .steps
        .iter()
        .map(|step| move |_back: bool| run_step(step))
        .collect();
    let steps: Vec<&dyn Fn(bool) -> Result<UiReply>> = steps
        .iter()
        .map(|step| step as &dyn Fn(bool) -> Result<UiReply>)
        .collect();
    reply(modui::flow::linear(&steps)?)
}

// ============================================================================
// Blocks
// ============================================================================

fn run_confirm_action(m: &wire::ConfirmAction) -> Result<UiReply> {
    let extras = Extras::new(&m.extras);
    modui::confirm::action(modui::confirm::Action::new(
        &m.title,
        &m.action,
        m.description.as_deref(),
        m.subtitle.as_deref(),
        commitment(m.commitment()),
        &m.br,
        &extras.items(),
    ))
}

fn run_confirm_value(m: &wire::ConfirmValue) -> Result<UiReply> {
    let footer = match (m.footer_hint.as_deref(), m.footer_warning.as_deref()) {
        (None, None) => None,
        (Some(hint), None) => Some(confirm::Footer::Hint(hint)),
        (None, Some(warning)) => Some(confirm::Footer::Warning(warning)),
        (Some(_), Some(_)) => {
            return Err(Error::ValueError(
                "set footer_hint or footer_warning, not both",
            ));
        }
    };
    let kind = match m.kind() {
        wire::ValueKind::Text => confirm::ValueKind::Text,
        wire::ValueKind::Address => confirm::ValueKind::Address,
    };
    let extras = Extras::new(&m.extras);
    modui::confirm::value(modui::confirm::Value::new(
        &m.title,
        &m.value,
        kind,
        m.subtitle.as_deref(),
        m.description.as_deref(),
        footer,
        commitment(m.commitment()),
        &m.br,
        &extras.items(),
    ))
}

fn run_confirm_properties(m: &wire::ConfirmProperties) -> Result<UiReply> {
    let props = properties(&m.props);
    let extras = Extras::new(&m.extras);
    modui::confirm::properties(modui::confirm::Properties::new(
        &m.title,
        &props,
        m.subtitle.as_deref(),
        commitment(m.commitment()),
        &m.br,
        &extras.items(),
        m.cancel(),
    ))
}

fn run_confirm_summary(m: &wire::ConfirmSummary) -> Result<UiReply> {
    let amount = m.amount_label.as_deref().zip(m.amount.as_deref());
    let fee = m.fee_label.as_deref().zip(m.fee.as_deref());
    let extras = Extras::new(&m.extras);
    modui::confirm::summary(modui::confirm::Summary::new(
        &m.title,
        amount,
        fee,
        &m.br,
        &extras.items(),
    ))
}

fn run_show_notice(m: &wire::ShowNotice) -> Result<UiReply> {
    let severity = match m.severity() {
        wire::Severity::Info => notice::Severity::Info,
        wire::Severity::Success => notice::Severity::Success,
        wire::Severity::Done => notice::Severity::Done,
        wire::Severity::Warning => notice::Severity::Warning,
        wire::Severity::Danger => notice::Severity::Danger,
    };
    let extras = Extras::new(&m.extras);
    modui::notice::show(modui::notice::Notice::new(
        severity,
        &m.title,
        &m.content,
        &m.br,
        &extras.items(),
        m.cancel(),
    ))
}

fn run_step(step: &wire::FlowStep) -> Result<UiReply> {
    match step {
        wire::FlowStep {
            confirm_action: Some(m),
            ..
        } => run_confirm_action(m),
        wire::FlowStep {
            confirm_value: Some(m),
            ..
        } => run_confirm_value(m),
        wire::FlowStep {
            confirm_properties: Some(m),
            ..
        } => run_confirm_properties(m),
        wire::FlowStep {
            confirm_summary: Some(m),
            ..
        } => run_confirm_summary(m),
        wire::FlowStep {
            show_notice: Some(m),
            ..
        } => run_show_notice(m),
        _ => Err(Error::ValueError("a flow step names no block")),
    }
}

// ============================================================================
// Conversions
// ============================================================================

fn commitment(c: wire::Commitment) -> Commitment {
    match c {
        wire::Commitment::Step => Commitment::Step,
        wire::Commitment::Final => Commitment::Final,
    }
}

fn properties(props: &[wire::Property]) -> Vec<Property<'_>> {
    props
        .iter()
        .map(|p| Property::new(&p.key, &p.value, p.mono()))
        .collect()
}

/// The extras of one request, kept alive while the block borrows them.
struct Extras<'a> {
    labels: Vec<&'a str>,
    props: Vec<Vec<Property<'a>>>,
}

impl<'a> Extras<'a> {
    fn new(items: &'a [wire::ExtraItem]) -> Self {
        Self {
            labels: items.iter().map(|item| item.label.as_str()).collect(),
            props: items.iter().map(|item| properties(&item.props)).collect(),
        }
    }

    fn items(&self) -> Vec<ExtraItem<'_>> {
        self.labels
            .iter()
            .zip(&self.props)
            .map(|(label, props)| ExtraItem::simple(label, props))
            .collect()
    }
}

/// The block's answer, as the host receives it.
fn reply(reply: UiReply) -> Result<wire::UiResult> {
    let (reply, choice) = match reply {
        UiReply::Confirmed => (Reply::Confirmed, None),
        UiReply::Cancelled => (Reply::Cancelled, None),
        UiReply::WantsMore => (Reply::WantsMore, None),
        UiReply::Choice(choice) => (Reply::Choice, Some(u32::from(choice))),
        UiReply::Forward => (Reply::Forward, None),
        UiReply::Backward => (Reply::Backward, None),
        UiReply::ConfirmedAll => (Reply::ConfirmedAll, None),
    };
    Ok(wire::UiResult {
        reply: reply as i32,
        choice,
    })
}
