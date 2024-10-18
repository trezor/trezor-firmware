use crate::{
    error::Error,
    micropython::gc::Gc,
    strutil::TString,
    ui::{
        component::{image::BlendedImage, ComponentExt, Empty, Timeout},
        layout::obj::{LayoutMaybeTrace, LayoutObj, RootComponent},
        ui_features_fw::UIFeaturesFirmware,
    },
};

use super::{
    component::{Button, ButtonMsg, ButtonStyleSheet, CancelConfirmMsg, IconDialog},
    theme, ModelTTFeatures,
};

impl UIFeaturesFirmware for ModelTTFeatures {
    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        button: TString<'static>,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error> {
        assert!(
            !button.is_empty() || time_ms > 0,
            "either button or timeout must be set"
        );

        let icon = BlendedImage::new(
            theme::IMAGE_BG_CIRCLE,
            theme::IMAGE_FG_INFO,
            theme::INFO_COLOR,
            theme::FG,
            theme::BG,
        );
        let res = new_show_modal(
            title,
            TString::empty(),
            description,
            TString::empty(),
            false,
            time_ms,
            icon,
            theme::button_info(),
        )?;
        Ok(res)
    }
}

fn new_show_modal(
    title: TString<'static>,
    value: TString<'static>,
    description: TString<'static>,
    button: TString<'static>,
    allow_cancel: bool,
    time_ms: u32,
    icon: BlendedImage,
    button_style: ButtonStyleSheet,
) -> Result<Gc<LayoutObj>, Error> {
    let no_buttons = button.is_empty();
    let obj = if no_buttons && time_ms == 0 {
        // No buttons and no timer, used when we only want to draw the dialog once and
        // then throw away the layout object.
        LayoutObj::new(
            IconDialog::new(icon, title, Empty)
                .with_value(value)
                .with_description(description),
        )?
    } else if no_buttons && time_ms > 0 {
        // Timeout, no buttons.
        LayoutObj::new(
            IconDialog::new(
                icon,
                title,
                Timeout::new(time_ms).map(|_| Some(CancelConfirmMsg::Confirmed)),
            )
            .with_value(value)
            .with_description(description),
        )?
    } else if allow_cancel {
        // Two buttons.
        LayoutObj::new(
            IconDialog::new(
                icon,
                title,
                Button::cancel_confirm(
                    Button::with_icon(theme::ICON_CANCEL),
                    Button::with_text(button).styled(button_style),
                    false,
                ),
            )
            .with_value(value)
            .with_description(description),
        )?
    } else {
        // Single button.
        LayoutObj::new(
            IconDialog::new(
                icon,
                title,
                theme::button_bar(Button::with_text(button).styled(button_style).map(|msg| {
                    (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                })),
            )
            .with_value(value)
            .with_description(description),
        )?
    };

    Ok(obj)
}
