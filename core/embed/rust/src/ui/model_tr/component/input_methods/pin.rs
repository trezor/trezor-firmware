use crate::{
    strutil::StringType,
    trezorhal::random,
    ui::{
        component::{text::common::TextBox, Child, Component, ComponentExt, Event, EventCtx},
        display::Icon,
        geometry::Rect,
    },
};

use super::super::{
    theme, ButtonDetails, ButtonLayout, CancelConfirmMsg, ChangingTextLine, ChoiceFactory,
    ChoiceItem, ChoicePage,
};
use heapless::String;

#[derive(Clone, Copy)]
enum PinAction {
    Delete,
    Show,
    Enter,
    Digit(char),
}

const MAX_PIN_LENGTH: usize = 50;
const EMPTY_PIN_STR: &str = "_";

const CHOICE_LENGTH: usize = 13;
const NUMBER_START_INDEX: usize = 3;
const CHOICES: [(&str, PinAction, Option<Icon>); CHOICE_LENGTH] = [
    ("DELETE", PinAction::Delete, Some(theme::ICON_DELETE)),
    ("SHOW", PinAction::Show, Some(theme::ICON_EYE)),
    ("ENTER", PinAction::Enter, Some(theme::ICON_TICK)),
    ("0", PinAction::Digit('0'), None),
    ("1", PinAction::Digit('1'), None),
    ("2", PinAction::Digit('2'), None),
    ("3", PinAction::Digit('3'), None),
    ("4", PinAction::Digit('4'), None),
    ("5", PinAction::Digit('5'), None),
    ("6", PinAction::Digit('6'), None),
    ("7", PinAction::Digit('7'), None),
    ("8", PinAction::Digit('8'), None),
    ("9", PinAction::Digit('9'), None),
];

fn get_random_digit_position() -> usize {
    random::uniform_between(NUMBER_START_INDEX as u32, (CHOICE_LENGTH - 1) as u32) as usize
}

struct ChoiceFactoryPIN;

impl<T: StringType + Clone> ChoiceFactory<T> for ChoiceFactoryPIN {
    type Action = PinAction;
    type Item = ChoiceItem<T>;

    fn get(&self, choice_index: usize) -> (Self::Item, Self::Action) {
        let (choice_str, action, icon) = CHOICES[choice_index];

        let mut choice_item = ChoiceItem::new(choice_str, ButtonLayout::default_three_icons());

        // Action buttons have different middle button text
        if !matches!(action, PinAction::Digit(_)) {
            let confirm_btn = ButtonDetails::armed_text("CONFIRM".into());
            choice_item.set_middle_btn(Some(confirm_btn));
        }

        // Adding icons for appropriate items
        if let Some(icon) = icon {
            choice_item = choice_item.with_icon(icon);
        }

        (choice_item, action)
    }

    fn count(&self) -> usize {
        CHOICE_LENGTH
    }
}

/// Component for entering a PIN.
pub struct PinEntry<T: StringType + Clone> {
    choice_page: ChoicePage<ChoiceFactoryPIN, T, PinAction>,
    pin_line: Child<ChangingTextLine<String<MAX_PIN_LENGTH>>>,
    subprompt: T,
    show_real_pin: bool,
    show_last_digit: bool,
    textbox: TextBox<MAX_PIN_LENGTH>,
}

impl<T> PinEntry<T>
where
    T: StringType + Clone,
{
    pub fn new(subprompt: T) -> Self {
        let pin_line_content = if !subprompt.as_ref().is_empty() {
            String::from(subprompt.as_ref())
        } else {
            String::from(EMPTY_PIN_STR)
        };

        Self {
            // Starting at a random digit.
            choice_page: ChoicePage::new(ChoiceFactoryPIN)
                .with_initial_page_counter(get_random_digit_position())
                .with_carousel(true),
            pin_line: Child::new(
                ChangingTextLine::center_bold(pin_line_content).without_ellipsis(),
            ),
            subprompt,
            show_real_pin: false,
            show_last_digit: false,
            textbox: TextBox::empty(),
        }
    }

    /// Performs overall update of the screen.
    fn update(&mut self, ctx: &mut EventCtx) {
        self.update_pin_line(ctx);
        ctx.request_paint();
    }

    /// Show updated content in the changing line.
    /// Many possibilities, according to the PIN state.
    fn update_pin_line(&mut self, ctx: &mut EventCtx) {
        let pin_line_text = if self.is_empty() && !self.subprompt.as_ref().is_empty() {
            String::from(self.subprompt.as_ref())
        } else if self.is_empty() {
            String::from(EMPTY_PIN_STR)
        } else if self.show_real_pin {
            String::from(self.pin())
        } else {
            // Showing asterisks and possibly the last digit.
            let mut dots: String<MAX_PIN_LENGTH> = String::new();
            for _ in 0..self.textbox.len() - 1 {
                unwrap!(dots.push('*'));
            }
            let last_char = if self.show_last_digit {
                unwrap!(self.textbox.content().chars().last())
            } else {
                '*'
            };
            unwrap!(dots.push(last_char));
            dots
        };

        self.pin_line.mutate(ctx, |ctx, pin_line| {
            pin_line.update_text(pin_line_text);
            pin_line.request_complete_repaint(ctx);
        });
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

impl<T> Component for PinEntry<T>
where
    T: StringType + Clone,
{
    type Msg = CancelConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let pin_height = self.pin_line.inner().needed_height();
        let (pin_area, choice_area) = bounds.split_top(pin_height);
        self.pin_line.place(pin_area);
        self.choice_page.place(choice_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Any event when showing real PIN should hide it
        // Same with showing last digit
        if self.show_real_pin {
            self.show_real_pin = false;
            self.update(ctx)
        }
        if self.show_last_digit {
            self.show_last_digit = false;
            self.update(ctx)
        }

        match self.choice_page.event(ctx, event) {
            Some(PinAction::Delete) => {
                self.textbox.delete_last(ctx);
                self.update(ctx);
                None
            }
            Some(PinAction::Show) => {
                self.show_real_pin = true;
                self.update(ctx);
                None
            }
            Some(PinAction::Enter) => Some(CancelConfirmMsg::Confirmed),
            Some(PinAction::Digit(ch)) if !self.is_full() => {
                self.textbox.append(ctx, ch);
                // Choosing random digit to be shown next
                self.choice_page
                    .set_page_counter(ctx, get_random_digit_position());
                self.show_last_digit = true;
                self.update(ctx);
                None
            }
            _ => None,
        }
    }

    fn paint(&mut self) {
        self.pin_line.paint();
        self.choice_page.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for PinEntry<T>
where
    T: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("PinKeyboard");
        t.string("subprompt", self.subprompt.as_ref());
        t.string("pin", self.textbox.content());
        t.child("choice_page", &self.choice_page);
    }
}
