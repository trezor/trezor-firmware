#[cfg(feature = "micropython")]
use crate::micropython::buffer::StrBuffer;
use crate::ui::{
    component::{
        text::paragraphs::{Paragraph, ParagraphVecShort, Paragraphs, VecExt},
        Component,
    },
    geometry::LinearPlacement,
    model_tt::{
        component::ErrorScreen,
        constant,
        theme::{TEXT_ERROR_HIGHLIGHT, TEXT_ERROR_NORMAL},
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

pub fn screen_fatal_error(title: &str, msg: &str, footer: &str) {
    // SAFETY: these will get placed into `frame` which does not outlive this
    // function
    let title = unsafe { get_str(title) };
    let msg = unsafe { get_str(msg) };
    let footer = unsafe { get_str(footer) };

    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_ERROR_NORMAL, msg).centered());

    let m_top =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut messages = ParagraphVecShort::new();

    messages.add(Paragraph::new(&TEXT_ERROR_HIGHLIGHT, footer).centered());

    let m_bottom =
        Paragraphs::new(messages).with_placement(LinearPlacement::vertical().align_at_center());

    let mut frame = ErrorScreen::new(title, m_top, m_bottom);
    frame.place(constant::screen());
    frame.paint();
}
