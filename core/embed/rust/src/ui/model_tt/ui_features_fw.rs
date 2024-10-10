use crate::{
    error::Error,
    strutil::TString,
    ui::{
        component::{image::BlendedImage, ComponentExt},
        layout::obj::{LayoutMaybeTrace, RootComponent},
        ui_features_fw::UIFeaturesFirmware,
    },
};

use super::{
    component::{Button, ButtonMsg, CancelConfirmMsg, IconDialog},
    theme, ModelTTFeatures,
};

impl UIFeaturesFirmware for ModelTTFeatures {
    fn show_info(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error> {
        let icon = BlendedImage::new(
            theme::IMAGE_BG_CIRCLE,
            theme::IMAGE_FG_INFO,
            theme::INFO_COLOR,
            theme::FG,
            theme::BG,
        );
        let res = RootComponent::new(
            IconDialog::new(
                icon,
                title,
                theme::button_bar(Button::with_text(button).styled(theme::button_info()).map(
                    |msg| (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed),
                )),
            )
            .with_description(description),
        );
        Ok(res)
    }
}
