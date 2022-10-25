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

#[no_mangle]
extern "C" fn screen_fatal_error(msg: *const cty::c_char, file: *const cty::c_char) -> u32 {
    let m_top = if msg.is_null() {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "FATAL ERROR!").centered());
        // .add(theme::TEXT_WIPE_NORMAL, unwrap!(unsafe { from_c_str(expr) }))
        //     .centered()
        messages.add(
            Paragraph::new(&TEXT_ERROR_NORMAL, unwrap!(unsafe { from_c_str(file) })).centered(),
        );

        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    } else {
        let msg = unwrap!(unsafe { from_c_str(msg) });
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "FATAL ERROR!").centered());
        messages.add(Paragraph::new(&TEXT_ERROR_NORMAL, msg).centered());

        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    };
    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "PLEASE CONTACT").centered());
    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "TREZOR SUPPORT").centered());
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

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, label).centered());
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    } else {
        let mut messages = ParagraphVecShort::new();
        let msg = unwrap!(unsafe { from_c_str(msg) });

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, label).centered());
        messages.add(Paragraph::new(&TEXT_ERROR_NORMAL, msg).centered());

        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    };
    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "PLEASE UNPLUG").centered());
    messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "THE DEVICE").centered());
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
