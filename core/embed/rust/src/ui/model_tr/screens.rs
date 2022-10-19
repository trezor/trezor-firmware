#[cfg(feature = "micropython")]
use crate::micropython::buffer::StrBuffer;
use crate::ui::{
    component::{
        text::paragraphs::{Paragraph, ParagraphVecShort, Paragraphs, VecExt},
        Component,
    },
    display::Icon,
    geometry::LinearPlacement,
    model_tr::{
        component::ResultScreen,
        constant,
        theme::{BLACK, ICON_FAIL, TEXT_BOLD, TEXT_NORMAL, WHITE},
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

        messages.add(Paragraph::new(&TEXT_BOLD, "FATAL ERROR!".into()).centered());
        messages.add(Paragraph::new(&TEXT_NORMAL, msg).centered());
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    } else {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_BOLD, "FATAL ERROR!".into()).centered());

        messages.add(Paragraph::new(&TEXT_NORMAL, file).centered());

        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    };

    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_BOLD, "PLEASE CONTACT".into()).centered());
    messages.add(Paragraph::new(&TEXT_BOLD, "TREZOR SUPPORT".into()).centered());

    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(WHITE, BLACK, Icon::new(ICON_FAIL), m_top, m_bottom, true);
    frame.place(constant::screen());
    frame.paint();
}

pub fn screen_error_shutdown(msg: Option<&str>, label: &str) {
    // SAFETY: these will get placed into `frame` which does not outlive this
    // function
    let msg = msg.map(|s| unsafe { get_str(s) });
    let label = unsafe { get_str(label) };

    let m_top = if let Some(msg) = msg {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_BOLD, label).centered());
        messages.add(Paragraph::new(&TEXT_NORMAL, msg).centered());
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    } else {
        let mut messages = ParagraphVecShort::new();

        messages.add(Paragraph::new(&TEXT_BOLD, label).centered());
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center())
    };

    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_BOLD, "PLEASE UNPLUG".into()).centered());
    messages.add(Paragraph::new(&TEXT_BOLD, "THE DEVICE".into()).centered());
    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ResultScreen::new(WHITE, BLACK, Icon::new(ICON_FAIL), m_top, m_bottom, true);
    frame.place(constant::screen());
    frame.paint();
}
