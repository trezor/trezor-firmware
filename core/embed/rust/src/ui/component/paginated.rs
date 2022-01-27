use crate::ui::component::{
    text::layout::{LayoutFit, TextNoOp},
    FormattedText,
};

/// Common message type for pagination components.
pub enum PageMsg<T, U> {
    /// Pass-through from paged component.
    Content(T),

    /// Messages from page controls outside the paged component, like
    /// "OK" and "Cancel" buttons.
    Controls(U),
}

pub trait Paginate {
    fn page_count(&mut self) -> usize;
    fn change_page(&mut self, active_page: usize);
}

impl<F, T> Paginate for FormattedText<F, T>
where
    F: AsRef<[u8]>,
    T: AsRef<[u8]>,
{
    fn page_count(&mut self) -> usize {
        let mut page_count = 1; // There's always at least one page.
        let mut char_offset = 0;

        loop {
            let fit = self.layout_content(&mut TextNoOp);
            match fit {
                LayoutFit::Fitting { .. } => {
                    break; // TODO: We should consider if there's more content
                           // to render.
                }
                LayoutFit::OutOfBounds {
                    processed_chars, ..
                } => {
                    page_count += 1;
                    char_offset += processed_chars;
                    self.set_char_offset(char_offset);
                }
            }
        }

        // Reset the char offset back to the beginning.
        self.set_char_offset(0);

        page_count
    }

    fn change_page(&mut self, to_page: usize) {
        let mut active_page = 0;
        let mut char_offset = 0;

        // Make sure we're starting from the beginning.
        self.set_char_offset(char_offset);

        while active_page < to_page {
            let fit = self.layout_content(&mut TextNoOp);
            match fit {
                LayoutFit::Fitting { .. } => {
                    break; // TODO: We should consider if there's more content
                           // to render.
                }
                LayoutFit::OutOfBounds {
                    processed_chars, ..
                } => {
                    active_page += 1;
                    char_offset += processed_chars;
                    self.set_char_offset(char_offset);
                }
            }
        }
    }
}
