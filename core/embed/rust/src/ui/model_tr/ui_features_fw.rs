use crate::{
    error::Error,
    micropython::gc::Gc,
    strutil::TString,
    ui::{
        component::{
            text::paragraphs::{Paragraph, Paragraphs},
            ComponentExt, Timeout,
        },
        layout::obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
        ui_features_fw::UIFeaturesFirmware,
    },
};

use super::{
    component::{Frame, PassphraseEntry, PinEntry, WordlistEntry, WordlistType},
    theme, ModelTRFeatures,
};

impl UIFeaturesFirmware for ModelTRFeatures {
    fn request_bip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(
            Frame::new(
                prompt,
                prefill_word
                    .map(|s| WordlistEntry::prefilled_word(s, WordlistType::Bip39, can_go_back)),
            )
            .with_title_centered(),
        );
        Ok(layout)
    }

    fn request_slip39(
        prompt: TString<'static>,
        prefill_word: TString<'static>,
        can_go_back: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(
            Frame::new(
                prompt,
                prefill_word
                    .map(|s| WordlistEntry::prefilled_word(s, WordlistType::Slip39, can_go_back)),
            )
            .with_title_centered(),
        );
        Ok(layout)
    }

    fn request_pin(
        prompt: TString<'static>,
        subprompt: TString<'static>,
        allow_cancel: bool,
        warning: bool,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout = RootComponent::new(PinEntry::new(prompt, subprompt));
        Ok(layout)
    }

    fn request_passphrase(
        prompt: TString<'static>,
        max_len: u32,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let layout =
            RootComponent::new(Frame::new(prompt, PassphraseEntry::new()).with_title_centered());
        Ok(layout)
    }

    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        _button: TString<'static>,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let content = Frame::new(
            title,
            Paragraphs::new([Paragraph::new(&theme::TEXT_NORMAL, description)]),
        );
        let obj = if time_ms == 0 {
            // No timer, used when we only want to draw the dialog once and
            // then throw away the layout object.
            LayoutObj::new(content)?
        } else {
            // Timeout.
            let timeout = Timeout::new(time_ms);
            LayoutObj::new((timeout, content.map(|_| None)))?
        };
        Ok(obj)
    }
}
