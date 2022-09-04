use crate::{
    micropython::buffer::StrBuffer,
    trezorhal::random,
    ui::{
        component::{text::common::TextBox, Component, Event, EventCtx},
        geometry::Rect,
    },
};

use super::{
    choice_item::BigCharacterChoiceItem,
    common::{display_dots_center_top, display_secret_center_top},
    ButtonDetails, ButtonLayout, ChoiceFactory, ChoiceItem, ChoicePage, ChoicePageMsg,
    MultilineTextChoiceItem,
};
use heapless::String;

pub enum PinEntryMsg {
    Confirmed,
    Cancelled,
}

const MAX_PIN_LENGTH: usize = 50;
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

struct ChoiceFactoryPIN {
    prompt: StrBuffer,
}

impl ChoiceFactoryPIN {
    fn new(prompt: StrBuffer) -> Self {
        Self { prompt }
    }
}

impl ChoiceFactory for ChoiceFactoryPIN {
    fn get(&self, choice_index: u8) -> ChoiceItem {
        let choice = CHOICES[choice_index as usize];

        // Depending on whether it is a digit (one character) or a text.
        // Digits are BIG, the rest is multiline.
        let mut choice_item = if choice.len() == 1 {
            let item =
                BigCharacterChoiceItem::from_str(choice, ButtonLayout::default_three_icons());
            ChoiceItem::BigCharacter(item)
        } else {
            let item = MultilineTextChoiceItem::new(
                String::from(choice),
                ButtonLayout::default_three_icons(),
            )
            .use_delimiter(' ');
            ChoiceItem::MultilineText(item)
        };

        // Action buttons have different middle button text
        if [EXIT_INDEX, DELETE_INDEX, SHOW_INDEX, PROMPT_INDEX].contains(&(choice_index as usize)) {
            let confirm_btn = ButtonDetails::armed_text("CONFIRM");
            choice_item.set_middle_btn(Some(confirm_btn));
        }

        // Changing the prompt text for the wanted one
        if choice_index == PROMPT_INDEX as u8 {
            choice_item.set_text(String::from(self.prompt.as_ref()));
        }

        choice_item
    }

    fn count(&self) -> u8 {
        CHOICE_LENGTH as u8
    }
}

/// Component for entering a PIN.
pub struct PinEntry {
    choice_page: ChoicePage<ChoiceFactoryPIN>,
    show_real_pin: bool,
    textbox: TextBox<MAX_PIN_LENGTH>,
}

impl PinEntry {
    pub fn new(prompt: StrBuffer) -> Self {
        let choices = ChoiceFactoryPIN::new(prompt);

        Self {
            choice_page: ChoicePage::new(choices)
                .with_initial_page_counter(3)
                .with_carousel(),
            show_real_pin: false,
            textbox: TextBox::empty(),
        }
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
use super::{ButtonAction, ButtonPos};

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for PinEntry {
    fn get_btn_action(&self, pos: ButtonPos) -> String<25> {
        match pos {
            ButtonPos::Left => ButtonAction::PrevPage.string(),
            ButtonPos::Right => ButtonAction::NextPage.string(),
            ButtonPos::Middle => {
                let current_index = self.choice_page.page_index() as usize;
                match current_index {
                    EXIT_INDEX => ButtonAction::Cancel.string(),
                    DELETE_INDEX => ButtonAction::Action("Delete last digit").string(),
                    SHOW_INDEX => ButtonAction::Action("Show PIN").string(),
                    PROMPT_INDEX => ButtonAction::Confirm.string(),
                    _ => ButtonAction::select_item(CHOICES[current_index]),
                }
            }
        }
    }

    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("PinEntry");
        // NOTE: `show_real_pin` was not able to be transferred,
        // as it is true only for a very small amount of time
        t.kw_pair("textbox", self.textbox.content());
        self.report_btn_actions(t);
        t.field("choice_page", &self.choice_page);
        t.close();
    }
}
