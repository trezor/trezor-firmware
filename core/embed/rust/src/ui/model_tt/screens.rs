#[cfg(feature = "micropython")]
use crate::micropython::buffer::StrBuffer;
use crate::ui::{
    component::{
        text::paragraphs::{Paragraph, ParagraphVecShort, Paragraphs, VecExt},
        Component,
    },
    geometry::LinearPlacement,
    model_tt::{
        component::ResultScreen,
        constant,
        theme::{FATAL_ERROR_COLOR, ICON_WARN_SMALL, TEXT_ERROR_BOLD, TEXT_ERROR_NORMAL, WHITE},
    },
    util::from_c_str,
};

#[cfg(not(feature = "micropython"))]
fn get_str(text: &str) -> &str {
    text
}
#[cfg(feature = "micropython")]
fn get_str(text: &'static str) -> StrBuffer {
    text.into()
}

#[no_mangle]
extern "C" fn screen_fatal_error(msg: *const cty::c_char, file: *const cty::c_char) -> u32 {
    let m_top = if msg.is_null() {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, get_str("FATAL ERROR!")).centered());
        // .add(theme::TEXT_WIPE_NORMAL, unwrap!(unsafe { from_c_str(expr) }))
        //     .centered()
        messages.add(
            Paragraph::new(
                &TEXT_ERROR_NORMAL,
                get_str(unwrap!(unsafe { from_c_str(file) })),
            )
            .centered(),
        );

        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    } else {
        let msg = unwrap!(unsafe { from_c_str(msg) });
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, get_str("FATAL ERROR!")).centered());
        messages.add(Paragraph::new(&TEXT_ERROR_NORMAL, get_str(msg)).centered());

        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    };
    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, get_str("PLEASE CONTACT")).centered());
    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, get_str("TREZOR SUPPORT")).centered());
    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(
        WHITE,
        FATAL_ERROR_COLOR,
        ICON_WARN_SMALL,
        m_top,
        m_bottom,
        true,
    );
    frame.place(constant::screen());
    frame.paint();
    0
}

#[no_mangle]
extern "C" fn screen_error_shutdown(label: *const cty::c_char, msg: *const cty::c_char) -> u32 {
    let label = unwrap!(unsafe { from_c_str(label) });

    let m_top = if msg.is_null() {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, get_str(label)).centered());
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    } else {
        let mut messages = ParagraphVecShort::new();
        let msg = unwrap!(unsafe { from_c_str(msg) });

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, get_str(label)).centered());
        messages.add(Paragraph::new(&TEXT_ERROR_NORMAL, get_str(msg)).centered());

        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    };
    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, get_str("PLEASE UNPLUG")).centered());
    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, get_str("THE DEVICE")).centered());
    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(
        WHITE,
        FATAL_ERROR_COLOR,
        ICON_WARN_SMALL,
        m_top,
        m_bottom,
        true,
    );
    frame.place(constant::screen());
    frame.paint();
    0
}
