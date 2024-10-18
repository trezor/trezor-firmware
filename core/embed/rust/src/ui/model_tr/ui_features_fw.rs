use crate::{
    error::Error,
    micropython::gc::Gc,
    strutil::TString,
    ui::{
        component::{
            text::paragraphs::{Paragraph, Paragraphs}, ComponentExt, Timeout
        },
        layout::obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
        ui_features_fw::UIFeaturesFirmware,
    },
};

use super::{component::Frame, theme, ModelTRFeatures};

impl UIFeaturesFirmware for ModelTRFeatures {
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
