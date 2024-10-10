use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{
            swipe_detect::SwipeSettings,
            text::paragraphs::{Paragraph, Paragraphs},
        },
        geometry::Direction,
        layout::obj::LayoutObj,
        ui_features_fw::UIFeaturesFirmware,
    },
};

use super::{
    component::{Frame, SwipeContent, SwipeUpScreen},
    theme, ModelMercuryFeatures,
};

#[cfg(feature="micropython")]
impl UIFeaturesFirmware for ModelMercuryFeatures {
    fn show_info(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        time_ms: u32,
    ) -> LayoutObj {
        let content = Paragraphs::new(Paragraph::new(&theme::TEXT_MAIN_GREY_LIGHT, description));
        LayoutObj::new(SwipeUpScreen::new(
            Frame::left_aligned(title, SwipeContent::new(content))
                .with_footer(TR::instructions__swipe_up.into(), None)
                .with_swipe(Direction::Up, SwipeSettings::default()),
        ))?
    }
}
