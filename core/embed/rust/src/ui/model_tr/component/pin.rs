use core::ops::Deref;

use crate::{
    trezorhal::random,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx},
        geometry::{Point, Rect},
    },
};

use super::{
    common::{display_bold_center, ButtonDetails, ButtonLayout, MultilineStringChoiceItem},
    ChoicePage, ChoicePageMsg,
};
use heapless::{String, Vec};

pub enum PinEntryMsg {
    Confirmed,
    Cancelled,
}

const PIN_ROW: i32 = 40;

const MAX_LENGTH: usize = 50;
const MAX_VISIBLE_DOTS: usize = 18;
const MAX_VISIBLE_DIGITS: usize = 18;

const CHOICE_LENGTH: usize = 14;
const EXIT_INDEX: usize = 0;
const DELETE_INDEX: usize = 1;
const SHOW_INDEX: usize = 2;
const PROMPT_INDEX: usize = 3;
const DIGITS: [&str; CHOICE_LENGTH] = [
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
    choice_page: ChoicePage<MultilineStringChoiceItem, CHOICE_LENGTH>,
    show_real_pin: bool,
    textbox: TextBox<MAX_LENGTH>,
}

impl PinEntry {
    pub fn new<T>(prompt: T) -> Self
    where
        T: Deref<Target = str>,
    {
        let choices = Self::get_word_choice_page_items(prompt);

        Self {
            choice_page: ChoicePage::new(choices)
                .with_initial_page_counter(3)
                .with_carousel(),
            show_real_pin: false,
            textbox: TextBox::empty(),
        }
    }

    /// Constructing list of choice items for PIN entry.
    fn get_word_choice_page_items<T>(prompt: T) -> Vec<MultilineStringChoiceItem, CHOICE_LENGTH>
    where
        T: Deref<Target = str>,
    {
        let mut choices: Vec<MultilineStringChoiceItem, CHOICE_LENGTH> = DIGITS
            .iter()
            .map(|digit| {
                MultilineStringChoiceItem::new(String::from(*digit), ButtonLayout::default_three())
                    .use_delimiter(' ')
            })
            .collect();

        // Action buttons have different text
        let confirm_btn = ButtonDetails::new("CONFIRM");
        choices[EXIT_INDEX].btn_layout.btn_middle = Some(confirm_btn);
        choices[DELETE_INDEX].btn_layout.btn_middle = Some(confirm_btn);
        choices[SHOW_INDEX].btn_layout.btn_middle = Some(confirm_btn);
        choices[PROMPT_INDEX].btn_layout.btn_middle = Some(confirm_btn);
        choices[PROMPT_INDEX].text = String::from(prompt.as_ref());

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
        // Only showing the maximum visible length
        let digits = self.textbox.len();
        let dots_visible = digits.min(MAX_VISIBLE_DOTS);

        // String::repeat() is not available for heapless::String
        let mut dots: String<50> = String::new();
        for _ in 0..dots_visible {
            dots.push_str("*").unwrap();
        }

        // Giving some notion of change even for longer-than-visible PINs
        // - slightly shifting the dots to the left and right after each new digit
        let x_baseline = if digits > MAX_VISIBLE_DOTS && digits % 2 == 0 {
            61
        } else {
            64
        };
        display_bold_center(Point::new(x_baseline, PIN_ROW), &dots);
    }

    fn reveal_current_pin(&self) {
        let digits = self.textbox.len();

        if digits <= MAX_VISIBLE_DOTS {
            display_bold_center(Point::new(64, PIN_ROW), self.pin());
        } else {
            // Show the last part of PIN with preceding ellipsis to show something is hidden
            let ellipsis = "...";
            let offset: usize = digits.saturating_sub(MAX_VISIBLE_DIGITS) + ellipsis.len();
            let mut to_show: String<MAX_VISIBLE_DIGITS> = String::from(ellipsis);
            to_show.push_str(&self.pin()[offset..]).unwrap();
            display_bold_center(Point::new(64, PIN_ROW), &to_show);
        }
    }

    fn append_new_digit(&mut self, ctx: &mut EventCtx, page_counter: u8) {
        let digit = DIGITS[page_counter as usize];
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
