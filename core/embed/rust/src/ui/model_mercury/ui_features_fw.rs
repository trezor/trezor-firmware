use crate::{
    error::Error,
    micropython::gc::Gc,
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, Paragraphs},
        },
        geometry::Direction,
        layout::obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
        ui_features_fw::UIFeaturesFirmware,
    },
};

use super::{
    component::{Frame, SwipeContent, SwipeUpScreen},
    theme, ModelMercuryFeatures,
};

impl UIFeaturesFirmware for ModelMercuryFeatures {
    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        _button: TString<'static>,
        _time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        let content = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
        let obj = LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(title, SwipeContent::new(content))
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?;
        Ok(obj)
    }
}
