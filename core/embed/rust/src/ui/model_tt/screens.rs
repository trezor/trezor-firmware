#[cfg(feature = "micropython")]
use crate::micropython::buffer::StrBuffer;
use crate::ui::{
    component::{
        text::paragraphs::{Paragraph, ParagraphVecShort, Paragraphs, VecExt},
        Component,
    },
    display::Icon,
    geometry::LinearPlacement,
    model_tt::{
        component::ResultScreen,
        constant,
        theme::{
            FATAL_ERROR_COLOR, FATAL_ERROR_HIGHLIGHT_COLOR, ICON_WARNING40, TEXT_ERROR_BOLD,
            TEXT_ERROR_HIGHLIGHT, TEXT_ERROR_NORMAL, WHITE,
        },
    },
};

#[cfg(not(feature = "micropython"))]
// SAFETY: Actually safe but see below
unsafe fn get_str(text: &str) -> &str {
    text
}
#[cfg(feature = "micropython")]
// SAFETY: The caller is responsible for ensuring that the StrBuffer does not
// escape the lifetime of the original &str.
unsafe fn get_str(text: &str) -> StrBuffer {
    unsafe { StrBuffer::from_ptr_and_len(text.as_ptr(), text.len()) }
}

pub fn screen_fatal_error(msg: Option<&str>, file: &str) {
    // SAFETY: these will get placed into `frame` which does not outlive this
    // function
    let msg = msg.map(|s| unsafe { get_str(s) });
    let file = unsafe { get_str(file) };

    let m_top = if let Some(msg) = msg {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "FATAL ERROR!".into()).centered());
        messages.add(Paragraph::new(&TEXT_ERROR_NORMAL, msg).centered());

        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    } else {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, "FATAL ERROR!".into()).centered());
        messages.add(Paragraph::new(&TEXT_ERROR_NORMAL, file).centered());

        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    };
    let mut messages = ParagraphVecShort::new();

    messages.add(
        Paragraph::new(
            &TEXT_ERROR_HIGHLIGHT,
            "PLEASE CONTACT\nTREZOR SUPPORT".into(),
        )
        .centered(),
    );
    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(
        WHITE,
        FATAL_ERROR_COLOR,
        FATAL_ERROR_HIGHLIGHT_COLOR,
        Icon::new(ICON_WARNING40),
        m_top,
        m_bottom,
        true,
    );
    frame.place(constant::screen());
    frame.paint();
}

pub fn screen_error_shutdown(label: &str, msg: Option<&str>) {
    // SAFETY: these will get placed into `frame` which does not outlive this
    // function
    let msg = msg.map(|s| unsafe { get_str(s) });
    let label = unsafe { get_str(label) };

    let m_top = if let Some(msg) = msg {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, label).centered());
        messages.add(Paragraph::new(&TEXT_ERROR_NORMAL, msg).centered());

        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    } else {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_ERROR_BOLD, label).centered());
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    };
    let mut messages = ParagraphVecShort::new();

    messages
        .add(Paragraph::new(&TEXT_ERROR_HIGHLIGHT, "PLEASE UNPLUG\nTHE DEVICE".into()).centered());
    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(
        WHITE,
        FATAL_ERROR_COLOR,
        FATAL_ERROR_HIGHLIGHT_COLOR,
        Icon::new(ICON_WARNING40),
        m_top,
        m_bottom,
        true,
    );
    frame.place(constant::screen());
    frame.paint();
}
