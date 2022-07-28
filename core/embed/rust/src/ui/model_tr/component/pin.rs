use core::ops::Deref;

use crate::{
    trezorhal::random,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx},
        geometry::Rect,
    },
};

use super::{
    choice_item::BigCharacterChoiceItem,
    common::{display_dots_center_top, display_secret_center_top},
    ButtonDetails, ButtonLayout, ChoiceItems, ChoicePage, ChoicePageMsg, MultilineTextChoiceItem,
};
use heapless::{String, Vec};

pub enum PinEntryMsg {
    Confirmed,
    Cancelled,
}

const MAX_LENGTH: usize = 50;
const MAX_VISIBLE_DOTS: usize = 18;
const MAX_VISIBLE_DIGITS: usize = 18;

const CHOICE_LENGTH: usize = 14;
const EXIT_INDEX: usize = 0;
const DELETE_INDEX: usize = 1;
const SHOW_INDEX: usize = 2;
const PROMPT_INDEX: usize = 3;
const CHOICES: [&str; CHOICE_LENGTH] = [
    "EXIT",
    "DELETE",
    "SHOW PIN",
    "PLACEHOLDER FOR THE PROMPT",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
];

/// Component for entering a PIN.
pub struct PinEntry {
    choice_page: ChoicePage<CHOICE_LENGTH>,
    show_real_pin: bool,
    textbox: TextBox<MAX_LENGTH>,
}

impl PinEntry {
    pub fn new<T>(prompt: T) -> Self
    where
        T: Deref<Target = str>,
    {
        let choices = Self::get_page_items(prompt);

        Self {
            choice_page: ChoicePage::new(choices)
                .with_initial_page_counter(3)
                .with_carousel(),
            show_real_pin: false,
            textbox: TextBox::empty(),
        }
    }

    /// Constructing list of choice items for PIN entry.
    /// Digits are BIG, the rest is multiline.
    fn get_page_items<T>(prompt: T) -> Vec<ChoiceItems, CHOICE_LENGTH>
    where
        T: Deref<Target = str>,
    {
        let mut choices: Vec<ChoiceItems, CHOICE_LENGTH> = CHOICES
            .iter()
            .map(|choice| {
                // Depending on whether it is a digit (one character) or a text
                if choice.len() == 1 {
                    let item = BigCharacterChoiceItem::from_str(
                        *choice,
                        ButtonLayout::default_three_icons(),
                    );
                    ChoiceItems::BigCharacter(item)
                } else {
                    let item = MultilineTextChoiceItem::new(
                        String::from(*choice),
                        ButtonLayout::default_three_icons(),
                    )
                    .use_delimiter(' ');
                    ChoiceItems::MultilineText(item)
                }
            })
            .collect();

        // Action buttons have different text
        let confirm_btn = ButtonDetails::new("CONFIRM").with_arms();
        choices[EXIT_INDEX].set_middle_btn(Some(confirm_btn));
        choices[DELETE_INDEX].set_middle_btn(Some(confirm_btn));
        choices[SHOW_INDEX].set_middle_btn(Some(confirm_btn));
        choices[PROMPT_INDEX].set_middle_btn(Some(confirm_btn));
        choices[PROMPT_INDEX].set_text(String::from(prompt.as_ref()));

        choices
    }

    fn update_situation(&mut self) {
        if self.show_real_pin {
            self.reveal_current_pin();
            self.show_real_pin = false;
        } else {
            self.show_pin_length();
        }
    }

    fn show_pin_length(&self) {
        display_dots_center_top(self.textbox.len(), 0);
    }

    fn reveal_current_pin(&self) {
        display_secret_center_top(self.pin(), 0);
    }

    fn append_new_digit(&mut self, ctx: &mut EventCtx, page_counter: u8) {
        let digit = CHOICES[page_counter as usize];
        self.textbox.append_slice(ctx, digit);
    }

    fn delete_last_digit(&mut self, ctx: &mut EventCtx) {
        self.textbox.delete_last(ctx);
    }

    pub fn pin(&self) -> &str {
        self.textbox.content()
    }

    fn is_full(&self) -> bool {
        self.textbox.is_full()
    }

    fn is_empty(&self) -> bool {
        self.textbox.is_empty()
    }
}

impl Component for PinEntry {
    type Msg = PinEntryMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.choice_page.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.choice_page.event(ctx, event);
        if let Some(ChoicePageMsg::Choice(page_counter)) = msg {
            // Performing action under specific index or appending new digit
            match page_counter as usize {
                EXIT_INDEX => return Some(PinEntryMsg::Cancelled),
                DELETE_INDEX => {
                    self.delete_last_digit(ctx);
                    ctx.request_paint();
                }
                SHOW_INDEX => {
                    self.show_real_pin = true;
                    ctx.request_paint();
                }
                PROMPT_INDEX => return Some(PinEntryMsg::Confirmed),
                _ => {
                    if !self.is_full() {
                        self.append_new_digit(ctx, page_counter);
                        // Choosing any random digit to be shown next
                        let new_page_counter =
                            random::uniform_between(4, (CHOICE_LENGTH - 1) as u32);
                        self.choice_page
                            .set_page_counter(ctx, new_page_counter as u8);
                        ctx.request_paint();
                    }
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        self.choice_page.paint();
        self.update_situation();
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PinEntry {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("PinEntry");
        t.close();
    }
}
