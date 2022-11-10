use crate::{
    micropython::buffer::StrBuffer,
    trezorhal::random,
    ui::{
        component::{text::common::TextBox, Child, Component, ComponentExt, Event, EventCtx},
        display::Icon,
        geometry::Rect,
        model_tr::theme,
    },
};

use super::{
    ButtonDetails, ButtonLayout, ChangingTextLine, ChoiceFactory, ChoiceItem, ChoicePage,
    ChoicePageMsg,
};
use heapless::String;

pub enum PinEntryMsg {
    Confirmed,
    Cancelled,
}

const MAX_PIN_LENGTH: usize = 50;
const MAX_VISIBLE_DOTS: usize = 18;
const MAX_VISIBLE_DIGITS: usize = 18;

const CHOICE_LENGTH: usize = 13;
const DELETE_INDEX: usize = 0;
const SHOW_INDEX: usize = 1;
const PROMPT_INDEX: usize = 2;
const CHOICES: [&str; CHOICE_LENGTH] = [
    "DELETE",
    "SHOW",
    "ENTER PIN",
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
    type Item = ChoiceItem;

    fn get(&self, choice_index: u8) -> ChoiceItem {
        let choice_str = CHOICES[choice_index as usize];

        let mut choice_item = ChoiceItem::new(choice_str, ButtonLayout::default_three_icons());

        // Action buttons have different middle button text
        if [DELETE_INDEX, SHOW_INDEX, PROMPT_INDEX].contains(&(choice_index as usize)) {
            let confirm_btn = ButtonDetails::armed_text("CONFIRM");
            choice_item.set_middle_btn(Some(confirm_btn));
        }

        // Adding icons for appropriate items
        if choice_index == DELETE_INDEX as u8 {
            choice_item = choice_item.with_icon(Icon::new(theme::ICON_DELETE));
        } else if choice_index == SHOW_INDEX as u8 {
            choice_item = choice_item.with_icon(Icon::new(theme::ICON_EYE));
        } else if choice_index == PROMPT_INDEX as u8 {
            choice_item = choice_item.with_icon(Icon::new(theme::ICON_TICK));
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
    pin_dots: Child<ChangingTextLine<String<MAX_PIN_LENGTH>>>,
    show_real_pin: bool,
    textbox: TextBox<MAX_PIN_LENGTH>,
}

impl PinEntry {
    pub fn new(prompt: StrBuffer) -> Self {
        let choices = ChoiceFactoryPIN::new(prompt);

        Self {
            // Starting at the digit 0
            choice_page: ChoicePage::new(choices)
                .with_initial_page_counter(PROMPT_INDEX as u8 + 1)
                .with_carousel(true),
            pin_dots: Child::new(ChangingTextLine::center_mono(String::new())),
            show_real_pin: false,
            textbox: TextBox::empty(),
        }
    }

    fn append_new_digit(&mut self, ctx: &mut EventCtx, page_counter: u8) {
        let digit = CHOICES[page_counter as usize];
        self.textbox.append_slice(ctx, digit);
    }

    fn delete_last_digit(&mut self, ctx: &mut EventCtx) {
        self.textbox.delete_last(ctx);
    }

    fn update_pin_dots(&mut self, ctx: &mut EventCtx) {
        // TODO: this is the same action as for the passphrase entry,
        // might do a common component that will handle this part,
        // (something like `SecretTextLine`)
        // also with things like shifting the dots when too many etc.
        // TODO: when the PIN is longer than fits the screen, we might show ellipsis
        if self.show_real_pin {
            let pin = String::from(self.pin());
            self.pin_dots.inner_mut().update_text(pin);
        } else {
            let mut dots: String<MAX_PIN_LENGTH> = String::new();
            for _ in 0..self.textbox.len() {
                unwrap!(dots.push_str("*"));
            }
            self.pin_dots.inner_mut().update_text(dots);
        }
        self.pin_dots.request_complete_repaint(ctx);
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
        let pin_area_height = self.pin_dots.inner().needed_height();
        let (pin_area, choice_area) = bounds.split_top(pin_area_height);
        self.pin_dots.place(pin_area);
        self.choice_page.place(choice_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Any event when showing real PIN should hide it
        if self.show_real_pin {
            self.show_real_pin = false;
            self.update_pin_dots(ctx);
        }

        let msg = self.choice_page.event(ctx, event);
        if let Some(ChoicePageMsg::Choice(page_counter)) = msg {
            // Performing action under specific index or appending new digit
            match page_counter as usize {
                DELETE_INDEX => {
                    self.delete_last_digit(ctx);
                    self.update_pin_dots(ctx);
                    ctx.request_paint();
                }
                SHOW_INDEX => {
                    self.show_real_pin = true;
                    self.update_pin_dots(ctx);
                    ctx.request_paint();
                }
                PROMPT_INDEX => return Some(PinEntryMsg::Confirmed),
                _ => {
                    if !self.is_full() {
                        self.append_new_digit(ctx, page_counter);
                        self.update_pin_dots(ctx);
                        // Choosing any random digit to be shown next
                        let new_page_counter = random::uniform_between(
                            PROMPT_INDEX as u32 + 1,
                            (CHOICE_LENGTH - 1) as u32,
                        );
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
        self.pin_dots.paint();
        self.choice_page.paint();
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
