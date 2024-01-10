#[cfg(feature = "micropython")]
use crate::micropython::buffer::StrBuffer;

#[cfg(feature = "sd_card")]
use crate::ui::{layout::native::RustLayout, model_tt::theme};

#[cfg(all(feature = "sd_card", not(feature = "sd_card_hotswap")))]
use crate::ui::component::image::BlendedImage;
#[cfg(all(feature = "sd_card", not(feature = "sd_card_hotswap")))]
use crate::ui::{component::base::ComponentExt, model_tt::component::ButtonMsg};
use crate::ui::{
    component::Label,
    model::component::{
        bl_confirm::{Confirm, ConfirmMsg, ConfirmTitle},
        Button,
    },
};

#[cfg(all(feature = "sd_card", not(feature = "sd_card_hotswap")))]
use crate::ui::model::component::CancelConfirmMsg;
#[cfg(all(feature = "sd_card", not(feature = "sd_card_hotswap")))]
use crate::ui::model_tt::component::IconDialog;

#[cfg(all(feature = "sd_card", feature = "sd_card_hotswap"))]
pub fn insert_sd_card() -> bool {
    let title_str = StrBuffer::from("SD CARD REQUIRED");
    let title = Label::left_aligned(title_str, theme::TEXT_BOLD).vertically_centered();
    let msg = Label::left_aligned(
        StrBuffer::from("Please insert your SD card."),
        theme::TEXT_NORMAL,
    );

    let left = Button::with_text("CANCEL").styled(theme::button_default());
    let right = Button::with_text("RETRY").styled(theme::button_confirm());

    let mut layout = RustLayout::new(Confirm::new(
        theme::BG,
        left,
        right,
        ConfirmTitle::Text(title),
        msg,
    ));

    let res = layout.process();

    matches!(res, ConfirmMsg::Confirm)
}

#[cfg(all(feature = "sd_card", not(feature = "sd_card_hotswap")))]
pub fn insert_sd_card() -> bool {
    let icon = BlendedImage::new(
        theme::IMAGE_BG_CIRCLE,
        theme::IMAGE_FG_ERROR,
        theme::ERROR_COLOR,
        theme::FG,
        theme::BG,
    );

    let mut layout = RustLayout::new(
        IconDialog::new(
            icon,
            StrBuffer::from("SD CARD REQUIRED"),
            theme::button_bar(
                Button::with_text(StrBuffer::from("TRY AGAIN"))
                    .styled(theme::button_default())
                    .map(|msg| {
                        (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                    }),
            ),
        )
        .with_description(StrBuffer::from(
            "Please unplug the device and insert your SD card.",
        )),
    );

    layout.process();

    false
}

#[cfg(all(feature = "sd_card", feature = "sd_card_hotswap"))]
pub fn retry_wrong_card() -> bool {
    let title_str = StrBuffer::from("WRONG SD CARD");
    let title = Label::left_aligned(title_str, theme::TEXT_BOLD).vertically_centered();
    let msg = Label::left_aligned(
        StrBuffer::from("Please insert the correct SD card for this device."),
        theme::TEXT_NORMAL,
    );

    let left = Button::with_text("CANCEL").styled(theme::button_default());
    let right = Button::with_text("RETRY").styled(theme::button_confirm());

    let mut layout = RustLayout::new(Confirm::new(
        theme::BG,
        left,
        right,
        ConfirmTitle::Text(title),
        msg,
    ));

    let res = layout.process();

    matches!(res, ConfirmMsg::Confirm)
}

#[cfg(all(feature = "sd_card", not(feature = "sd_card_hotswap")))]
pub fn retry_wrong_card() -> bool {
    let icon = BlendedImage::new(
        theme::IMAGE_BG_CIRCLE,
        theme::IMAGE_FG_ERROR,
        theme::ERROR_COLOR,
        theme::FG,
        theme::BG,
    );

    let mut layout = RustLayout::new(
        IconDialog::new(
            icon,
            StrBuffer::from("WRONG SD CARD"),
            theme::button_bar(
                Button::with_text(StrBuffer::from("TRY AGAIN"))
                    .styled(theme::button_default())
                    .map(|msg| {
                        (matches!(msg, ButtonMsg::Clicked)).then(|| CancelConfirmMsg::Confirmed)
                    }),
            ),
        )
        .with_description(StrBuffer::from(
            "Please unplug the device and insert the correct SD card.",
        )),
    );

    layout.process();

    false
}

#[cfg(feature = "sd_card")]
pub fn retry_sd_card() -> bool {
    let title_str = StrBuffer::from("SD CARD PROBLEM");
    let title = Label::left_aligned(title_str, theme::TEXT_BOLD).vertically_centered();
    let msg = Label::left_aligned(
        StrBuffer::from("There was a problem accessing the SD card."),
        theme::TEXT_NORMAL,
    );

    let left = Button::with_text("ABORT").styled(theme::button_default());
    let right = Button::with_text("RETRY").styled(theme::button_confirm());

    let mut layout = RustLayout::new(Confirm::new(
        theme::BG,
        left,
        right,
        ConfirmTitle::Text(title),
        msg,
    ));

    let res = layout.process();

    matches!(res, ConfirmMsg::Confirm)
}
