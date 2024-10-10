use crate::{
    error::Error, micropython::obj::Obj, strutil::TString, ui::{
        component::{image::BlendedImage, ComponentExt, Empty, Timeout},
        layout::obj::LayoutObj,
        ui_features_fw::UIFeaturesFirmware,
    }
};

use super::{
    component::{Button, ButtonMsg, ButtonStyleSheet, CancelConfirmMsg, IconDialog},
    theme, ModelTTFeatures,
};

impl UIFeaturesFirmware for ModelTTFeatures {
    fn show_info(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        time_ms: u32,
    ) -> Result<Obj, Error> {
        let icon = BlendedImage::new(
            theme::IMAGE_BG_CIRCLE,
            theme::IMAGE_FG_INFO,
            theme::INFO_COLOR,
            theme::FG,
            theme::BG,
        );
        new_show_modal_copy(
            title,
            TString::empty(),
            description,
            button,
            allow_cancel,
            time_ms,
            icon,
            theme::button_info(),
        )
    }
}

fn new_show_modal_copy(
    title: TString<'static>,
    value: TString<'static>,
    description: TString<'static>,
    button: TString<'static>,
    allow_cancel: bool,
    time_ms: u32,
    icon: BlendedImage,
    button_style: ButtonStyleSheet,
) -> Result<Obj, Error> {
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
    Ok(obj.into())
}
