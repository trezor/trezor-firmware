use crate::{
    strutil::ShortString,
    ui::{component::EventCtx, util::ResultExt},
};

/// Reified editing operations of `TextBox`.
///
/// Note: This does not contain all supported editing operations, only the ones
/// we currently use.
pub enum TextEdit {
    ReplaceLast(char),
    Append(char),
}

/// Wraps a character buffer of maximum length `L` and provides text editing
/// operations over it. Text ops usually take a `EventCtx` to request a paint
/// pass in case of any state modification.
pub struct TextBox {
    text: ShortString,
}

impl TextBox {
    /// Create a new `TextBox` with content `text`.
    pub fn new(text: &str, max_len: usize) -> Self {
        let text = unwrap!(ShortString::try_from(text));
        debug_assert!(text.capacity() >= max_len);
        Self { text }
    }

    /// Create an empty `TextBox`.
    pub fn empty(max_len: usize) -> Self {
        Self::new("", max_len)
    }

    pub fn content(&self) -> &str {
        &self.text
    }

    pub fn len(&self) -> usize {
        self.text.len()
    }

    pub fn is_empty(&self) -> bool {
        self.text.is_empty()
    }

    /// Delete the last character of content, if any.
    pub fn delete_last(&mut self, ctx: &mut EventCtx) {
        let changed = self.text.pop().is_some();
        if changed {
            ctx.request_paint();
        }
    }

    /// Replaces the last character of the content with `ch`. If the content is
    /// empty, `ch` is appended.
    pub fn replace_last(&mut self, ctx: &mut EventCtx, ch: char) {
        let previous = self.text.pop();
        self.text
            .push(ch)
            .assert_if_debugging_ui("TextBox has zero capacity");
        let changed = previous != Some(ch);
        if changed {
            ctx.request_paint();
        }
    }

    /// Append `ch` at the end of the content.
    pub fn append(&mut self, ctx: &mut EventCtx, ch: char) {
        self.text.push(ch).assert_if_debugging_ui("TextBox is full");
        ctx.request_paint();
    }

    /// Append `slice` at the end of the content.
    pub fn append_slice(&mut self, ctx: &mut EventCtx, slice: &str) {
        self.text
            .push_str(slice)
            .assert_if_debugging_ui("TextBox is full");
        ctx.request_paint();
    }

    /// Replace the textbox content with `text`.
    pub fn replace(&mut self, ctx: &mut EventCtx, text: &str) {
        if self.text != text {
            self.text.clear();
            self.text
                .push_str(text)
                .assert_if_debugging_ui("TextBox is full");
            ctx.request_paint();
        }
    }

    /// Clear the textbox content.
    pub fn clear(&mut self, ctx: &mut EventCtx) {
        self.replace(ctx, "");
    }

    /// Apply a editing operation to the text buffer.
    pub fn apply(&mut self, ctx: &mut EventCtx, edit: TextEdit) {
        match edit {
            TextEdit::ReplaceLast(char) => self.replace_last(ctx, char),
            TextEdit::Append(char) => self.append(ctx, char),
        }
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for TextBox {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("TextBox");
        t.string("text", self.text.as_str().into());
    }
}
